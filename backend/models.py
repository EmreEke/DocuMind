from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    summary = Column(Text, nullable=True)
    total_pages = Column(Integer, default=0)

    # İlişki: Bir dokümanın birçok parçası (chunk) olur
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    # DİKKAT: Gemini Embeddings 768 boyutludur.
    embedding = Column(Vector(768))

    document = relationship("Document", back_populates="chunks")