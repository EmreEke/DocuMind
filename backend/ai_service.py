import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session
from models import Document, DocumentChunk
import shutil
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# .env dosyasından API anahtarını aldığından emin ol
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def process_and_store_document(file, db: Session):
    """
    PDF veya TXT dosyasını işleyip veritabanına kaydeder.
    """
    # 1. Dosyayı geçici olarak kaydet (LangChain dosya yolu ister)
    temp_filename = f"temp_{file.filename}"
    
    # Dosya tipine göre yazma modunu belirle
    file_extension = file.filename.lower().split('.')[-1]
    is_text_file = file_extension == 'txt'
    
    if is_text_file:
        # TXT dosyası için text modunda yaz
        with open(temp_filename, "w", encoding="utf-8") as buffer:
            content = file.file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            buffer.write(content)
    else:
        # PDF dosyası için binary modunda yaz
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    try:
        # 2. Dosya tipine göre loader seç
        if is_text_file:
            loader = TextLoader(temp_filename, encoding="utf-8")
        else:
            loader = PyPDFLoader(temp_filename)
        
        documents = loader.load()
        
        # 3. Metni Parçala (Chunking) - KRİTİK KARAR
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # Her parça 1000 karakter
            chunk_overlap=200   # Parçalar birbirinin içine 200 karakter girsin (bağlam kopmasın diye)
        )
        chunks = text_splitter.split_documents(documents)

        # 4. Veritabanına Doküman Kaydını Aç
        # TXT dosyaları için total_pages yerine chunk sayısını kullanabiliriz veya 0 bırakabiliriz
        total_pages = len(documents) if not is_text_file else 0
        
        new_doc = Document(
            filename=file.filename,
            total_pages=total_pages,
            summary="Özet henüz oluşturulmadı..." # Bunu sonra yapacağız
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # 5. Embedding (Vektör) Oluştur ve Kaydet
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
        
        print(f"Toplam {len(chunks)} parça işleniyor...")
        
        for i, chunk in enumerate(chunks):
            # Metni vektöre çevir
            vector = embeddings.embed_query(chunk.page_content)
            
            # Parçayı kaydet
            db_chunk = DocumentChunk(
                document_id=new_doc.id,
                chunk_text=chunk.page_content,
                chunk_index=i,
                embedding=vector
            )
            db.add(db_chunk)
        
        db.commit()
        return {"status": "success", "doc_id": new_doc.id, "chunks_count": len(chunks)}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        # Geçici dosyayı sil
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# Geriye dönük uyumluluk için eski fonksiyon adını da tutuyoruz
def process_and_store_pdf(file, db: Session):
    """Geriye dönük uyumluluk için - process_and_store_document'i çağırır"""
    return process_and_store_document(file, db)

def get_answer_from_docs(question: str, db: Session, doc_id: int = None):
    # 1. Soru tipini belirle - özet isteniyor mu?
    question_lower = question.lower()
    is_summary_request = any(keyword in question_lower for keyword in [
        'özet', 'özetle', 'özetini', 'özeti', 'genel', 'tüm', 'hepsi', 
        'hakkında', 'içeriği', 'içerik', 'summary', 'summarize'
    ])
    
    # 2. Embedding Modelini Hazırla
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
    
    if is_summary_request:
        # ÖZET İSTENİYORSA: Tüm chunk'ları al (veya çok daha fazla)
        # Token limiti nedeniyle maksimum 50 chunk alıyoruz, eğer daha fazlası varsa
        query = db.query(DocumentChunk)
        
        # Eğer belirli bir doküman seçildiyse, sadece o dokümanın chunk'larını al
        if doc_id is not None:
            query = query.filter(DocumentChunk.document_id == doc_id)
        
        all_chunks = query.order_by(DocumentChunk.chunk_index).limit(50).all()
        
        if not all_chunks:
            return {"answer": "Üzgünüm, dokümanlarda bilgi bulamadım.", "sources": []}
        
        # Tüm chunk'ları birleştir
        context_text = "\n\n".join([chunk.chunk_text for chunk in all_chunks])
        
        # Özet için özel prompt
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        
        system_prompt = """Sen yardımcı bir asistansın. Aşağıda verilen dokümanın TAMAMINI kapsayan, kapsamlı ve detaylı bir özet hazırla.
        Özet şunları içermelidir:
        - Dokümanın ana konuları ve temaları
        - Önemli detaylar ve örnekler
        - Farklı bölümlerde bahsedilen konular
        - Tüm önemli bilgileri kapsamalı
        
        Sadece verilen bağlamdaki bilgileri kullan, uydurma.
        
        Doküman İçeriği:
        {context}
        """
        
        user_message = f"Lütfen yukarıdaki dokümanın kapsamlı bir özetini hazırla."
        
    else:
        # NORMAL SORU: En benzer chunk'ları bul
        # 2. Soruyu Vektöre Çevir
        question_vector = embeddings.embed_query(question)
        
        # 3. Veritabanında En Benzer 3 Parçayı Bul (Postgres pgvector gücü!)
        # L2 distance operatörü (<->) kullanarak en yakın komşuları buluyoruz.
        query = db.query(DocumentChunk)
        
        # Eğer belirli bir doküman seçildiyse, sadece o dokümanın chunk'larını filtrele
        if doc_id is not None:
            query = query.filter(DocumentChunk.document_id == doc_id)
        
        closest_chunks = query.order_by(
            DocumentChunk.embedding.l2_distance(question_vector)
        ).limit(3).all()
        
        if not closest_chunks:
            return {"answer": "Üzgünüm, dokümanlarda bununla ilgili bilgi bulamadım.", "sources": []}
        
        # 4. Bağlamı (Context) Birleştir
        context_text = "\n\n".join([chunk.chunk_text for chunk in closest_chunks])
        all_chunks = closest_chunks
        
        # 5. Gemini'ye Prompt Hazırla (RAG Prompt)
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        
        system_prompt = """Sen yardımcı bir asistansın. Aşağıdaki bağlamı (context) kullanarak kullanıcının sorusunu cevapla.
        Eğer cevap bağlamda yoksa 'Bilmiyorum' de, uydurma.
        
        Bağlam:
        {context}
        """
        
        user_message = f"Soru: {question}"
    
    messages = [
        SystemMessage(content=system_prompt.format(context=context_text)),
        HumanMessage(content=user_message)
    ]
    
    # 6. Cevabı Üret
    response = llm.invoke(messages)
    
    # Kaynakları benzersiz hale getir
    unique_sources = list(set([chunk.document_id for chunk in all_chunks]))
    
    return {
        "answer": response.content,
        "sources": unique_sources # Hangi dokümandan geldiği
    }