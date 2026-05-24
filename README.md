# Twitter Haber Karşılaştırma & Duygu Analizi

Bu proje, birden fazla X/Twitter haber kanalından tweet çekip ortak haberleri eşleştirir ve ilgili tweet yanıtları üzerinde Türkçe duygu analizi yapar.

Yeni geliştirme hattı `frontend/` klasöründeki React uygulaması ve `backend/api/` klasöründeki FastAPI katmanı üzerinden ilerliyor.

## İçindekiler
- [Genel Bakış](#genel-bakış)
- [Özellikler](#özellikler)
- [Proje Yapısı](#proje-yapısı)
- [Teknolojiler](#teknolojiler)
- [Kurulum](#kurulum)
- [Yapılandırma (.env)](#yapılandırma-env)
- [Çalıştırma](#çalıştırma)
- [Canlıya Alma (Self-hosted, Docker)](#canlıya-alma-self-hosted-docker)
- [Canlıya Alma (Render + Vercel)](#canlıya-alma-render--vercel)
- [Nasıl Çalışır?](#nasıl-çalışır)
- [Test](#test)
- [Proje Haritası](#proje-haritası)
- [Duygu Analizi Yol Haritası](#duygu-analizi-yol-haritası)
- [Sorun Giderme](#sorun-giderme)
- [Sık Kullanılan Komutlar](#sık-kullanılan-komutlar)
- [Push Öncesi Kontrol Listesi](#push-öncesi-kontrol-listesi)

## Genel Bakış
Uygulama akışı 3 ana adımdan oluşur:
1. Girilen haber kanallarının son tweetleri çekilir.
2. Tweetler Gemini API ile konu bazında eşleştirilir (gerekirse anahtar kelime fallback).
3. Eşleşen tweetlerin yorumları toplanır ve Türkçe BERT ya da Twitter XLM-RoBERTa modelleri ile duygu analizine (pozitif/nötr/negatif) tabi tutulur.

Yeni arayüz React ile hazırlanıyor.

## Özellikler
- Birden fazla kanal desteği (en az 2 kanal).
- URL veya kullanıcı adı üzerinden tweet çekme.
- Ortak haber eşleştirme (LLM + fallback eşleştirme).
- Yorum toplama (syndication/CDN yöntemleri).
- Türkçe duygu analizi:
  - BERT Modeli (`savasy/bert-base-turkish-sentiment-cased`)
  - RoBERTa Modeli (`cardiffnlp/twitter-xlm-roberta-base-sentiment`)
- Modern React arayüz, temiz panel yapısı, karşılaştırmalı grafikler ve bileşen tabanlı ekranlar.

## Proje Yapısı
```text
Twitter/
├─ backend/
│  ├─ api/                      # FastAPI giriş noktası ve servis katmanı
│  ├─ analyzer/                 # Duygu, emotion ve eşleştirme motoru
│  └─ scraper/                  # Tweet ve yorum çekme
├─ frontend/                    # React + Vite arayüz
├─ data/                        # Örnek/çıktı JSON dosyaları
├─ config.py                    # Ortam ve sabitler
├─ test_pipeline.py             # Uçtan uca pipeline testi
├─ requirements.txt
└─ README.md
```

## Teknolojiler
- **Arayüz:** React + Vite
- **HTTP & Parsing:** requests, BeautifulSoup
- **LLM Eşleştirme:** Google Gemini API
- **NLP:** transformers, torch, sentencepiece, tiktoken
- **Görselleştirme:** plotly
- **Ortam Değişkenleri:** python-dotenv

## Kurulum

### 1) Projeyi aç
```bash
cd Twitter
```

### 2) (Önerilen) Sanal ortam oluştur ve aktif et
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Conda kullanıyorsanız mevcut ortamınızı da kullanabilirsiniz.

### 3) Bağımlılıkları kur
```bash
pip install -r requirements.txt
```

## Yapılandırma (.env)
Proje kök dizininde `.env` dosyası oluşturun (isterseniz `.env.example` dosyasını kopyalayabilirsiniz):

```env
GEMINI_API_KEY=your_gemini_api_key_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
SENTIMENT_ALLOW_MODEL_DOWNLOAD=1 # 1 ise Hugging Face modelleri sunucuda yoksa otomatik indirilir
```

Gemini anahtarını Google AI Studio üzerinden alabilirsiniz: https://aistudio.google.com/apikey
Twitter bearer token değerini kod içerisine **yazmayın**, sadece `.env` üzerinden yönetin.
Gemini API key alanı frontend'de gösterilmez; eşleştirme yalnızca backend tarafındaki `.env` değişkeni ile çalışır.

## Çalıştırma
Yeni mimaride iki süreç bulunur:

```bash
# API
uvicorn backend.api.main:app --reload --port 8000

# React frontend
cd frontend
npm install
npm run dev
```

API varsayılan olarak `http://localhost:8000`, frontend ise `http://localhost:5173` üzerinde çalışır.

## Canlıya Alma (Self-hosted, Docker)

Sunucunuzda Nginx + Cloudflare zaten varsa, arkadaki backend ve frontend Docker ile yönetilebilir. Detaylı adım adım Türkçe rehber: **[`docs/deploy.md`](docs/deploy.md)**

Hızlı özet:

```bash
ssh kullanici@sunucu
cd ~/Twitter-Duygu-Analizi
nano .env                  # API key'leri ve VITE_API_BASE_URL'i kontrol et
chmod +x scripts/deploy.sh
./scripts/deploy.sh        # Tek komut: pull + build + up + healthcheck
```

İlgili dosyalar:
- `Dockerfile` — backend (Python + FastAPI)
- `frontend/Dockerfile` — frontend (Node build → Nginx serve)
- `docker-compose.yml` — iki servisi orkestre eder
- `scripts/deploy.sh` — sunucuda tek komutla deploy
- `docs/deploy.md` — SSH adımları, sorun giderme, rollback

## Canlıya Alma (Render + Vercel)

Bu repo mevcut haliyle su sekilde deploy edilmeye hazir:

### 1) Backend (Render)
- Render'da repo baglayin.
- Kök dizindeki `render.yaml` dosyasi otomatik okunur.
- Build komutu: `pip install -r requirements.txt`
- Start komutu: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
- Ortam degiskenleri:
	- `GEMINI_API_KEY`
	- `TWITTER_BEARER_TOKEN`
	- `CORS_ORIGINS` = frontend adresiniz (ornek: `https://your-app.vercel.app`)

### 2) Frontend (Vercel)
- Vercel'de ayni repoyu import edin.
- Root Directory olarak `frontend` secin.
- Build komutu: `npm run build`
- Output directory: `dist`
- Environment Variable:
	- `VITE_API_BASE_URL` = Render backend adresiniz (ornek: `https://your-backend.onrender.com`)
- `frontend/vercel.json` SPA rewrite ayari icerir.

### 3) Son kontrol
- Frontend acildiktan sonra API saglik endpointi dogrulayin:
	- `<RENDER_URL>/health` -> `{"status":"ok"}`

## Nasıl Çalışır?

### 1) Kanal girişleri
- En az 2 kanal girilir.
- İlk 3 kanal için input alanı vardır.
- Ek kanallar satır satır eklenebilir.

### 2) Tweet çekme
- Her kanal için son tweetler çekilir.
- Hatalı/erişilemeyen kanallar uyarı olarak gösterilir.

### 3) Haber eşleştirme
- Tweetler Gemini API’ye gönderilir.
- Ortak konuya ait tweet grupları döner.
- Model çıktısı bozuk/boş ise kural tabanlı fallback devreye girer.

### 4) Yorumlar + duygu analizi
- Eşleşen tweetler için yorumlar toplanır.
- Yorumlar pozitif/negatif olarak sınıflanır.
- Toplam, oran ve detaylar arayüzde raporlanır.

## Test
Uçtan uca pipeline testi için:

```bash
python test_pipeline.py
```

Bu test:
- Örnek kanallardan tweet çeker,
- Gemini ile eşleştirmeyi dener,
- Konsola özet basar.

## Proje Haritası
Projenin klasör bazlı detaylı açıklamasını burada bulabilirsiniz:

- `docs/project-structure.md`

## Duygu Analizi Yol Haritası
Yorumlardan duygu analizi için adım adım uygulama planı burada:

- `docs/sentiment-roadmap.md`

## Sorun Giderme

### `Gemini API hatası` alıyorum
- API key’in doğru olduğundan emin olun.
- Kota/rate limit dolmuş olabilir; yeni key deneyin.

### `En az 2 kanaldan tweet çekilemedi`
- Kanal URL’lerini kontrol edin (`https://x.com/kullanici`).
- Geçici ağ/API sorunları için tekrar deneyin.

### Yorumlar boş geliyor
- Bazı tweetlerde yorumlara public erişim kısıtlı olabilir.
- Bu durumda uygulama analiz adımını bilgi mesajı ile geçer.

### Model ilk açılışta yavaş veya zaman aşımı veriyor
- `transformers` modelleri (BERT ve RoBERTa) ilk kullanımda internetten indirildiği için ilk analiz uzun sürebilir (~1-2 dakika). Sonraki istekler tamamen önbellek üzerinden çalıştığından anında yanıtlanır.
- Sunucunun ilk istekte zaman aşımına uğramaması için sunucu ayağa kalkarken modellerin önceden çekilmesini sağlayacak `SENTIMENT_ALLOW_MODEL_DOWNLOAD=1` parametresinin `.env`'de tanımlı olduğundan emin olun.

### Tiktoken veya Sentencepiece Kaynaklı Hatalar
- Bazı Linux/Windows sunucularda XLM-RoBERTa modeli yüklenirken BPE parser uyuşmazlığı yaşanabilir. Kodumuzda otomatik `AutoTokenizer` yerine doğrudan `XLMRobertaTokenizer` zorlanarak bu hata aşılmıştır. Bağımlılıkların eksiksiz kurulması için `pip install -r requirements.txt` komutunu çalıştırdığınızdan emin olun.

## Sık Kullanılan Komutlar
```bash
# Python bağımlılık kur
pip install -r requirements.txt

# API'yi başlat
uvicorn backend.api.main:app --reload --port 8000

# Yeni frontend'i başlat
cd frontend
npm run dev

# Pipeline testini çalıştır
python test_pipeline.py

# (Yeni) Yorum duygu algoritmalarini karsilastirma endpoint'i
# POST /api/sentiment/compare
```

## Push Öncesi Kontrol Listesi
- `.env` dosyası repoya dahil edilmemeli.
- API key’leri kod içine hard-code edilmemeli.
- Uygulama lokalde açılıp temel akış test edilmeli.
- Gerekirse `requirements.txt` güncelliği kontrol edilmeli.

---
Geliştirme odaklı not: Bu proje dış API’lere bağlı olduğu için zaman zaman geçici erişim/rate-limit kaynaklı dalgalanmalar görülebilir.
