from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from ai_service import process_and_store_document, get_answer_from_docs
from models import Document
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(title="DocuMind API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    doc_id: Optional[int] = None  # Opsiyonel: Belirli bir doküman ID'si

@app.get("/")
def read_root():
    return {"message": "DocuMind API Çalışıyor! 🚀"}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Veritabanı bağlantısı başarılı! 🟢"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- YENİ EKLENEN KISIM ---
@app.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Dosya uzantısını kontrol et
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı bulunamadı.")
    
    file_extension = file.filename.lower().split('.')[-1]
    if file_extension not in ['pdf', 'txt']:
        raise HTTPException(status_code=400, detail="Sadece PDF ve TXT dosyaları kabul edilir.")
    
    try:
        # AI Servisine gönder
        result = process_and_store_document(file, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/documents")
async def get_documents(db: Session = Depends(get_db)):
    """Tüm dokümanları listele"""
    try:
        documents = db.query(Document).order_by(Document.upload_date.desc()).all()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
                    "summary": doc.summary,
                    "total_pages": doc.total_pages
                }
                for doc in documents
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask_question(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        response = get_answer_from_docs(request.question, db, doc_id=request.doc_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))