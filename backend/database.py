import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 1. .env dosyasını yükle
load_dotenv()

# 2. Veritabanı adresini al
DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Bağlantı motorunu oluştur
# (Docker kullandığımız için check_same_thread gerekmez, o SQLite içindir)
engine = create_engine(DATABASE_URL)

# 4. Oturum (Session) fabrikası
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Modeller için temel sınıf
Base = declarative_base()

# --- EKSİK OLAN KISIM MUHTEMELEN BURASIYDI ---
# 6. Dependency: Her istekte DB açıp kapatan fonksiyon
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()