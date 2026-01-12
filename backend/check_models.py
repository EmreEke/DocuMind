import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Ortam değişkenlerini yükle (.env dosyasını bul)
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("HATA: GOOGLE_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")
else:
    # 2. SDK'yı konfigüre et
    genai.configure(api_key=api_key)

    print("--- Kullanılabilir Gemini Modelleri ---")
    try:
        # 3. Modelleri listele
        for m in genai.list_models():
            # Sadece içerik üretebilen (generateContent) modelleri filtrele
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model Adı: {m.name}")
                print(f"Açıklama: {m.description}")
                print("-" * 30)
    except Exception as e:
        print(f"Bir hata oluştu: {str(e)}")