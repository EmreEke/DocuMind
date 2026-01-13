# 🧠 DocuMind - AI-Powered Document Search & RAG System

DocuMind, kullanıcıların PDF ve TXT dokümanlarını yükleyebildiği, dokümanlar üzerinde hibrit arama (vektörel + anahtar kelime) yapabildiği ve yapay zeka destekli sorular sorabildiği modern bir RAG (Retrieval-Augmented Generation) sistemidir.

Bu proje, **BİL440 YZ Destekli Yazılım Geliştirme** dersi final ödevi kapsamında geliştirilmiştir.

## ✨ Özellikler

### 📄 Doküman Yönetimi
- **Çoklu Format Desteği**: PDF ve TXT dosyaları yükleme
- **Otomatik İşleme**: Dokümanlar otomatik olarak parçalara (chunks) ayrılır ve vektörleştirilir
- **Doküman Listesi**: Yüklenen tüm dokümanları görüntüleme
- **Doküman Seçme**: Belirli bir dokümana odaklanarak soru-cevap yapma
- **Doküman Silme**: Artık kullanılmayan dokümanları silme

### 🔍 Hibrit Arama Sistemi
- **Vektörel Arama**: pgvector kullanarak anlamsal (semantic) arama
- **Anahtar Kelime Araması**: PostgreSQL LIKE operatörü ile metin bazlı arama
- **Akıllı Birleştirme**: İki arama yöntemi birleştirilerek en iyi sonuçlar elde edilir

### 💬 AI Destekli Soru-Cevap
- **Akıllı Cevap Üretimi**: Google Gemini 2.5 Flash ile doküman içeriğine dayalı cevaplar
- **Kapsamlı Özetleme**: Tüm dokümanı kapsayan detaylı özetler
- **Kaynak Referansları**: Cevapların hangi dosyalardan geldiği gösterilir
- **Bağlam Korunması**: Büyük chunk'lar ve overlap ile bağlam kaybı minimize edilir

### 🎨 Modern Kullanıcı Arayüzü
- **Glassmorphism Tasarım**: Modern blur ve şeffaflık efektleri
- **Gradient Arka Planlar**: Profesyonel görünüm
- **Smooth Animasyonlar**: Kullanıcı deneyimini artıran geçişler
- **Responsive Tasarım**: Tüm ekran boyutlarında çalışır

## 🛠️ Teknoloji Yığını

### Frontend
- **React 19.2** - Modern UI framework
- **Vite** - Hızlı build tool
- **Axios** - HTTP client
- **React Icons** - İkon kütüphanesi
- **CSS3** - Modern styling (Glassmorphism, Gradients, Animations)

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM
- **LangChain** - AI/LLM entegrasyonu
- **Google Gemini 2.5 Flash** - LLM modeli
- **Google Generative AI Embeddings** - Vektörleştirme

### Veritabanı
- **PostgreSQL 16** - İlişkisel veritabanı
- **pgvector** - Vektör arama eklentisi
- **Docker** - Konteynerleştirme

## 📋 Gereksinimler

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Google Gemini API Key

## 🚀 Kurulum

### 1. Projeyi Klonlayın

```bash
git clone <repository-url>
cd DocuMind
```

### 2. Veritabanını Başlatın

```bash
docker-compose up -d
```

Bu komut PostgreSQL + pgvector veritabanını başlatır. Veritabanı `localhost:5435` portunda çalışacaktır.

### 3. Backend Kurulumu

```bash
cd backend

# Virtual environment oluştur
python -m venv venv

# Virtual environment'ı aktifleştir
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyası oluştur
# .env dosyasına şunları ekleyin:
# DATABASE_URL=postgresql://postgres:documind_password@localhost:5435/documind_db
# GOOGLE_API_KEY=your_google_api_key_here
```

`.env` dosyası örneği:
```env
DATABASE_URL=postgresql://postgres:documind_password@localhost:5435/documind_db
GOOGLE_API_KEY=your_google_api_key_here
```

### 4. Veritabanı Tablolarını Oluşturun

```bash
# Python shell'de:
python
>>> from database import engine, Base
>>> from models import Document, DocumentChunk
>>> Base.metadata.create_all(bind=engine)
>>> exit()
```

### 5. Backend'i Başlatın

```bash
uvicorn main:app --reload --port 8000
```

Backend `http://localhost:8000` adresinde çalışacaktır.

### 6. Frontend Kurulumu

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Development server'ı başlat
npm run dev
```

Frontend `http://localhost:5173` adresinde çalışacaktır.

## 📖 Kullanım

### Doküman Yükleme

1. Sol sidebar'daki "Doküman Yükle" bölümünden PDF veya TXT dosyası seçin
2. "Yükle & Analiz Et" butonuna tıklayın
3. Sistem dosyayı otomatik olarak işleyip parçalara ayırır ve vektörleştirir

### Soru Sorma

1. Chat alanındaki input kutusuna sorunuzu yazın
2. Enter'a basın veya gönder butonuna tıklayın
3. Sistem dokümanlarda arama yapar ve AI destekli cevap üretir

### Doküman Seçme

1. "Dokümanlar" bölümünden bir doküman seçin
2. Seçili doküman üzerinde soru-cevap yapılır
3. "Tüm Dokümanlar" seçeneği ile tüm dokümanlarda arama yapabilirsiniz

### Özet İsteme

Soru alanına şu ifadelerden birini yazın:
- "Bu dokümanın özeti nedir?"
- "Dokümanı özetle"
- "Tüm içeriği hakkında bilgi ver"

Sistem tüm dokümanı kapsayan kapsamlı bir özet üretir.

### Doküman Silme

1. "Dokümanlar" bölümündeki listede silmek istediğiniz dokümanın yanındaki çöp kutusu ikonuna tıklayın
2. Onaylayın
3. Doküman ve tüm chunk'ları silinir

## 🔌 API Endpoints

### `GET /`
API sağlık kontrolü

### `GET /test-db`
Veritabanı bağlantı testi

### `POST /upload`
Doküman yükleme
```json
{
  "status": "success",
  "doc_id": 1,
  "chunks_count": 45
}
```

### `GET /documents`
Tüm dokümanları listeleme
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "example.pdf",
      "upload_date": "2024-01-01T00:00:00",
      "summary": "...",
      "total_pages": 10
    }
  ]
}
```

### `POST /ask`
Soru sorma
```json
{
  "question": "En yakın komşu algoritması nedir?",
  "doc_id": 1  // Opsiyonel
}
```

Response:
```json
{
  "answer": "...",
  "sources": [1],
  "source_filenames": ["ML_07.pdf"]
}
```

### `DELETE /documents/{doc_id}`
Doküman silme

## 🏗️ Proje Yapısı

```
DocuMind/
├── backend/
│   ├── main.py              # FastAPI uygulaması
│   ├── ai_service.py        # AI ve RAG işlemleri
│   ├── database.py          # Veritabanı bağlantısı
│   ├── models.py            # SQLAlchemy modelleri
│   ├── requirements.txt      # Python bağımlılıkları
│   └── .env                 # Ortam değişkenleri (oluşturulmalı)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Ana React komponenti
│   │   ├── App.css          # Stil dosyası
│   │   ├── api.js           # API çağrıları
│   │   └── main.jsx         # React entry point
│   ├── package.json         # Node.js bağımlılıkları
│   └── vite.config.js       # Vite yapılandırması
├── docker-compose.yml       # Docker yapılandırması
└── README.md                # Bu dosya
```

## 🔧 Yapılandırma

### Veritabanı Ayarları

`docker-compose.yml` dosyasında:
- Port: `5435`
- Kullanıcı: `postgres`
- Şifre: `documind_password`
- Veritabanı: `documind_db`

### Backend Ayarları

`.env` dosyasında:
- `DATABASE_URL`: PostgreSQL bağlantı string'i
- `GOOGLE_API_KEY`: Google Gemini API anahtarı

### Frontend Ayarları

`frontend/src/api.js` dosyasında:
- `API_BASE_URL`: Backend API adresi (varsayılan: `http://127.0.0.1:8000`)

## 🎯 Özellikler ve Gereksinimler

### Karşılanan Gereksinimler

✅ **FR-1: Doküman Yönetimi** - PDF ve TXT desteği  
✅ **FR-2: Hibrit Arama** - Vektörel + Anahtar kelime araması  
✅ **FR-3: AI Q&A** - Doküman tabanlı soru-cevap  
✅ **FR-4: Özetleme** - Otomatik ve isteğe bağlı özetler  
✅ **AIR-1: Vektörleştirme** - Gemini Embeddings ile vektörleştirme  

### Gelecek Geliştirmeler

- [ ] Detaylı özet endpoint'i
- [ ] Hallucination trap mekanizması
- [ ] Kullanıcı kimlik doğrulama
- [ ] Çoklu dil desteği
- [ ] Doküman versiyonlama

## 🐛 Sorun Giderme

### Veritabanı Bağlantı Hatası

```bash
# Docker container'ın çalıştığını kontrol edin
docker ps

# Container'ı yeniden başlatın
docker-compose restart
```

### Backend Başlatma Hatası

- `.env` dosyasının doğru yapılandırıldığından emin olun
- Virtual environment'ın aktif olduğunu kontrol edin
- Port 8000'in kullanılabilir olduğunu kontrol edin

### Frontend Başlatma Hatası

```bash
# node_modules'ı temizleyip yeniden yükleyin
rm -rf node_modules
npm install
```

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.

## 👥 Katkıda Bulunanlar

- Proje geliştiricisi

## 📧 İletişim

Sorularınız için issue açabilirsiniz.

---

**Not**: Bu proje BİL440 dersi kapsamında geliştirilmiştir ve eğitim amaçlıdır.
