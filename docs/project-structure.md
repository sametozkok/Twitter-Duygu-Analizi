# Project Structure Guide

Bu dosya, projeyi yeni bir ekip üyesinin hızlıca anlayabilmesi için hazırlanmıştır.

## 1) Top-level

```text
Twitter/
├─ backend/
├─ frontend/
├─ data/
├─ docs/
├─ config.py
├─ requirements.txt
├─ test_pipeline.py
└─ README.md
```

- `backend/`: Uygulamanin is kurallari, scraping, eslestirme ve API.
- `frontend/`: React + Vite arayuz.
- `data/`: Ornek/veri ciktilari (json dosyalari).
- `docs/`: Mimari ve proje aciklama dokumanlari.
- `config.py`: Ortam degiskenleri ve sabit ayarlar.
- `requirements.txt`: Python bagimliliklari.
- `test_pipeline.py`: Uctan uca test scripti.

## 2) Backend Layout

```text
backend/
├─ api/
│  ├─ main.py
│  ├─ routes/
│  │  ├─ health.py
│  │  └─ analyze.py
│  ├─ schemas/
│  │  └─ analysis.py
│  └─ services/
│     └─ pipeline.py
├─ analyzer/
│  ├─ matcher.py
│  ├─ emotion.py
│  ├─ sentiment.py
│  └─ sentiment_compare.py
├─ preprocess/
│  └─ text_cleaner.py
├─ scraper/
│  ├─ tweets.py
│  └─ replies.py
└─ storage/
   └─ json_store.py
```

### backend/api
- `main.py`: FastAPI uygulama giris noktasi, CORS, router kayitlari.
- `routes/health.py`: Saglik kontrol endpoint'i (`/health`).
- `routes/analyze.py`: Ana endpointler (`/api/match`, `/api/replies`, `/api/analysis`, `/api/sentiment/compare`).
- `schemas/analysis.py`: Request/response modelleri (Pydantic).
- `services/pipeline.py`: Is akisini orkestre eder (scraper + analyzer cagrilari).

### backend/analyzer
- `matcher.py`: Tweetleri konu bazli eslestirir (Gemini + fallback).
- `emotion.py`: Yorumlardan duygu siniflandirma ciktilari.
- `sentiment.py`: Sentiment yardimci katmani/model islemleri.
- `sentiment_compare.py`: Birden fazla algoritmayi ayni veri uzerinde karsilastirir (`bert`, `hybrid`).

### backend/preprocess
- `text_cleaner.py`: Yorum metnini temizleyip analize hazir hale getirir.

### backend/storage
- `json_store.py`: Analiz ve yorum ciktilarini `data/analysis_runs/` altina JSON olarak kaydeder.

### backend/scraper
- `tweets.py`: Kanallardan tweet cekme islemleri.
- `replies.py`: Tweet yorumlarini cekme, kullanici ve metrik parse etme.

## 3) Frontend Layout

```text
frontend/
├─ src/
│  ├─ App.tsx
│  ├─ main.tsx
│  ├─ styles.css
│  ├─ types.ts
│  ├─ components/
│  └─ lib/
│     └─ api.ts
├─ package.json
├─ vite.config.ts
└─ tsconfig.json
```

- `src/App.tsx`: Ana ekran akis ve state yonetimi.
- `src/components/`: UI bilesenleri (Sidebar, Topbar, StatCard vb.).
- `src/lib/api.ts`: Backend API cagrilari.
- `src/types.ts`: Frontend tipleri.
- `src/styles.css`: Sayfa stili.

## 4) Data and Docs

- `data/`: Cikti/ara veri json dosyalari.
- `docs/architecture.md`: Mimari kararlar ve akis.
- `docs/project-structure.md`: Bu dosya.

## 5) Environment Variables

Proje kokunde `.env` dosyasi kullanilir.

Temel degiskenler:
- `GEMINI_API_KEY`
- `TWITTER_BEARER_TOKEN`
- `TWITTER_AUTH_TOKEN`
- `TWITTER_CT0`

Not: `GEMINI_API_KEY` frontend'de gosterilmez, backend tarafinda kullanilir.

## 6) Local Run Commands

API:
```bash
uvicorn backend.api.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## 7) Cleanup Policy

Paylasmadan once su klasorler repoda olmamali:
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`

Bu klasorler yerel ve yeniden uretilebilir oldugu icin temiz tutulur.
