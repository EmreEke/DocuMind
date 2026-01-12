import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session
from models import Document, DocumentChunk
import shutil
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# .env dosyasından API anahtarını aldığından emin ol
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def process_and_store_pdf(file, db: Session):
    # 1. Dosyayı geçici olarak kaydet (LangChain dosya yolu ister)
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. PDF'i Yükle
        loader = PyPDFLoader(temp_filename)
        pages = loader.load()
        
        # 3. Metni Parçala (Chunking) - KRİTİK KARAR
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # Her parça 1000 karakter
            chunk_overlap=200   # Parçalar birbirinin içine 200 karakter girsin (bağlam kopmasın diye)
        )
        chunks = text_splitter.split_documents(pages)

        # 4. Veritabanına Doküman Kaydını Aç
        new_doc = Document(
            filename=file.filename,
            total_pages=len(pages),
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

def get_answer_from_docs(question: str, db: Session):
    # 1. Embedding Modelini Hazırla
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
    
    # 2. Soruyu Vektöre Çevir
    question_vector = embeddings.embed_query(question)
    
    # 3. Veritabanında En Benzer 3 Parçayı Bul (Postgres pgvector gücü!)
    # L2 distance operatörü (<->) kullanarak en yakın komşuları buluyoruz.
    closest_chunks = db.query(DocumentChunk).order_by(
        DocumentChunk.embedding.l2_distance(question_vector)
    ).limit(3).all()
    
    if not closest_chunks:
        return {"answer": "Üzgünüm, dokümanlarda bununla ilgili bilgi bulamadım.", "sources": []}
    
    # 4. Bağlamı (Context) Birleştir
    context_text = "\n\n".join([chunk.chunk_text for chunk in closest_chunks])
    
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
    
    return {
        "answer": response.content,
        "sources": [chunk.document_id for chunk in closest_chunks] # Hangi dokümandan geldiği
    }