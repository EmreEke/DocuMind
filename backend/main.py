from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from ai_service import process_and_store_pdf, get_answer_from_docs
from pydantic import BaseModel

app = FastAPI(title="DocuMind API", version="1.0")

class QueryRequest(BaseModel):
    question: str

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
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")
    
    try:
        # AI Servisine gönder
        result = process_and_store_pdf(file, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/ask")
async def ask_question(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        response = get_answer_from_docs(request.question, db)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))