import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
        # Daha büyük chunk size = daha fazla bağlam, daha iyi anlama
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,    # Her parça 1500 karakter (artırıldı)
            chunk_overlap=300   # Parçalar birbirinin içine 300 karakter girsin (bağlam kopmasın diye)
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
            return {"answer": "Üzgünüm, dokümanlarda bilgi bulamadım.", "sources": [], "source_filenames": []}
        
        # Tüm chunk'ları birleştir
        context_text = "\n\n".join([chunk.chunk_text for chunk in all_chunks])
        
        # Özet için de dosya adlarını al
        unique_doc_ids = list(set([chunk.document_id for chunk in all_chunks]))
        source_documents = db.query(Document).filter(Document.id.in_(unique_doc_ids)).all()
        source_filenames = [doc.filename for doc in source_documents]
        
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
        
        # Özet için response'u burada üret ve döndür
        messages = [
            SystemMessage(content=system_prompt.format(context=context_text)),
            HumanMessage(content=user_message)
        ]
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        response = llm.invoke(messages)
        
        return {
            "answer": response.content,
            "sources": unique_doc_ids,
            "source_filenames": source_filenames
        }
        
    else:
        # NORMAL SORU: Hibrit arama (Vektörel + Anahtar Kelime)
        # 1. Sorudan anahtar kelimeleri çıkar (basit tokenizasyon)
        question_words = [word.lower().strip('.,!?;:()[]{}"\'') 
                         for word in question.split() 
                         if len(word) > 2]  # 2 karakterden uzun kelimeler
        
        # 2. Vektörel Arama: En benzer chunk'ları bul
        question_vector = embeddings.embed_query(question)
        
        query = db.query(DocumentChunk)
        if doc_id is not None:
            query = query.filter(DocumentChunk.document_id == doc_id)
        
        # Vektörel arama ile en yakın 10 chunk al
        vector_chunks = query.order_by(
            DocumentChunk.embedding.l2_distance(question_vector)
        ).limit(10).all()
        
        # 3. Anahtar Kelime Arama: Sorudaki kelimeleri içeren chunk'ları bul (OR mantığı)
        keyword_chunks = []
        if question_words:
            keyword_query = db.query(DocumentChunk)
            if doc_id is not None:
                keyword_query = keyword_query.filter(DocumentChunk.document_id == doc_id)
            
            # İlk 5 anahtar kelimeyi kullan ve OR mantığıyla birleştir
            # En az bir kelime eşleşirse chunk'ı al
            keyword_filters = [
                DocumentChunk.chunk_text.ilike(f'%{word}%')
                for word in question_words[:5]
            ]
            
            if keyword_filters:
                keyword_query = keyword_query.filter(or_(*keyword_filters))
                keyword_chunks = keyword_query.limit(10).all()
        
        # 4. Chunk'ları birleştir ve benzersiz hale getir
        all_found_chunks = {}
        for chunk in vector_chunks + keyword_chunks:
            if chunk.id not in all_found_chunks:
                all_found_chunks[chunk.id] = chunk
        
        closest_chunks = list(all_found_chunks.values())
        
        # Eğer hiç chunk bulunamadıysa
        if not closest_chunks:
            return {"answer": "Üzgünüm, dokümanlarda bununla ilgili bilgi bulamadım.", "sources": []}
        
        # 5. Chunk'ları benzerlik skoruna göre sırala ve en iyi 8'ini al
        # (Vektörel arama sonuçları genelde daha iyi olduğu için önce onları alıyoruz)
        if len(closest_chunks) > 8:
            # Vektörel arama sonuçlarını önceliklendir
            vector_chunk_ids = {chunk.id for chunk in vector_chunks}
            prioritized = [chunk for chunk in closest_chunks if chunk.id in vector_chunk_ids]
            others = [chunk for chunk in closest_chunks if chunk.id not in vector_chunk_ids]
            closest_chunks = (prioritized + others)[:8]
        
        # 6. Bağlamı (Context) Birleştir
        context_text = "\n\n".join([chunk.chunk_text for chunk in closest_chunks])
        all_chunks = closest_chunks
        
        # 7. Gemini'ye Prompt Hazırla (İyileştirilmiş RAG Prompt)
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        
        system_prompt = """Sen yardımcı bir AI asistansın. Aşağıdaki doküman parçalarını (context) kullanarak kullanıcının sorusunu detaylı ve kapsamlı bir şekilde cevapla.

ÖNEMLİ KURALLAR:
1. Verilen bağlamdaki bilgileri kullanarak soruyu cevapla
2. Eğer sorudaki anahtar kelimeler veya konular bağlamda geçiyorsa, o konuyu detaylıca açıkla
3. Bağlamda ilgili bilgiler varsa, bunları birleştirerek kapsamlı bir cevap ver
4. Sadece bağlamda kesinlikle hiçbir ilgili bilgi yoksa "Bu konu hakkında dokümanlarda yeterli bilgi bulunamadı" de
5. Bağlamda geçen terimler, kavramlar ve açıklamaları kullan

Bağlam (Doküman Parçaları):
{context}
"""
        
        user_message = f"Kullanıcı sorusu: {question}\n\nLütfen yukarıdaki bağlamı kullanarak bu soruyu detaylı ve kapsamlı bir şekilde cevapla. Eğer bağlamda ilgili bilgiler varsa, bunları birleştirerek açıkla."
    
    messages = [
        SystemMessage(content=system_prompt.format(context=context_text)),
        HumanMessage(content=user_message)
    ]
    
    # 6. Cevabı Üret
    response = llm.invoke(messages)
    
    # Kaynakları benzersiz hale getir ve dosya adlarını al
    unique_doc_ids = list(set([chunk.document_id for chunk in all_chunks]))
    
    # Dosya adlarını veritabanından al
    source_documents = db.query(Document).filter(Document.id.in_(unique_doc_ids)).all()
    source_filenames = [doc.filename for doc in source_documents]
    
    return {
        "answer": response.content,
        "sources": unique_doc_ids,  # Geriye dönük uyumluluk için ID'ler de döndürülüyor
        "source_filenames": source_filenames  # Dosya adları
    }