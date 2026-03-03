# Twitter Haber Karşılaştırma & Duygu Analizi

Bu proje, birden fazla X/Twitter haber kanalından tweet çekip ortak haberleri eşleştirir ve ilgili tweet yanıtları üzerinde Türkçe duygu analizi yapar.

## İçindekiler
- [Genel Bakış](#genel-bakış)
- [Özellikler](#özellikler)
- [Proje Yapısı](#proje-yapısı)
- [Teknolojiler](#teknolojiler)
- [Kurulum](#kurulum)
- [Yapılandırma (.env)](#yapılandırma-env)
- [Çalıştırma](#çalıştırma)
- [Nasıl Çalışır?](#nasıl-çalışır)
- [Test](#test)
- [Sorun Giderme](#sorun-giderme)
- [Sık Kullanılan Komutlar](#sık-kullanılan-komutlar)
- [Push Öncesi Kontrol Listesi](#push-öncesi-kontrol-listesi)

## Genel Bakış
Uygulama akışı 3 ana adımdan oluşur:
1. Girilen haber kanallarının son tweetleri çekilir.
2. Tweetler Gemini API ile konu bazında eşleştirilir (gerekirse anahtar kelime fallback).
3. Eşleşen tweetlerin yorumları toplanır ve Türkçe BERT modeli ile pozitif/negatif sınıflandırılır.

Arayüz Streamlit ile hazırlanmıştır ve sonuçları etkileşimli olarak gösterir.

## Özellikler
- Birden fazla kanal desteği (en az 2 kanal).
- URL veya kullanıcı adı üzerinden tweet çekme.
- Ortak haber eşleştirme (LLM + fallback eşleştirme).
- Yorum toplama (syndication/CDN yöntemleri).
- Türkçe duygu analizi (`savasy/bert-base-turkish-sentiment-cased`).
- Pie chart ve detay listesi ile sonuç görselleştirme.

## Proje Yapısı
```text
Twitter/
├─ frontend/
│  └─ app.py                    # Streamlit arayüzü
├─ backend/
│  ├─ scraper/
│  │  ├─ tweets.py              # Tweet çekme
│  │  └─ replies.py             # Yorum çekme
│  └─ analyzer/
│     ├─ matcher.py             # Haber eşleştirme (Gemini + fallback)
│     └─ sentiment.py           # Türkçe BERT duygu analizi
├─ data/                        # Örnek/çıktı JSON dosyaları
├─ config.py                    # Ortam ve sabitler
├─ test_pipeline.py             # Uçtan uca pipeline testi
├─ requirements.txt
└─ README.md
```

## Teknolojiler
- **Arayüz:** Streamlit
- **HTTP & Parsing:** requests, BeautifulSoup
- **LLM Eşleştirme:** Google Gemini API
- **NLP:** transformers, torch
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
Proje kök dizininde `.env` dosyası oluşturun:

```env
GEMINI_API_KEY=your_api_key_here
```

Gemini anahtarını Google AI Studio üzerinden alabilirsiniz: https://aistudio.google.com/apikey

## Çalıştırma
Streamlit uygulamasını başlatın:

```bash
streamlit run frontend/app.py
```

Başarılı çalıştığında terminalde genellikle şu adrese benzer bir link görürsünüz:
- `http://localhost:8501`

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
- Model çıktısı bozuk/boş ise keyword tabanlı fallback devreye girer.

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

### Model ilk açılışta yavaş
- `transformers` modeli ilk kullanımda indirildiği için ilk analiz uzun sürebilir.

## Sık Kullanılan Komutlar
```bash
# Bağımlılık kur
pip install -r requirements.txt

# Uygulamayı başlat
streamlit run frontend/app.py

# Pipeline testini çalıştır
python test_pipeline.py
```

## Push Öncesi Kontrol Listesi
- `.env` dosyası repoya dahil edilmemeli.
- API key’leri kod içine hard-code edilmemeli.
- Uygulama lokalde açılıp temel akış test edilmeli.
- Gerekirse `requirements.txt` güncelliği kontrol edilmeli.

---
Geliştirme odaklı not: Bu proje dış API’lere bağlı olduğu için zaman zaman geçici erişim/rate-limit kaynaklı dalgalanmalar görülebilir.
