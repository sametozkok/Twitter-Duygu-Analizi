# Sentiment Analysis Roadmap (Step-by-step)

Bu dokuman, ikinci asama olan yorumlardan duygu analizi gelistirme planinin uygulama sirasini verir.

## Phase 1 - Data and Backend Foundation (Tamamlandi - Ilk Iskelet)

- [x] JSON tabanli kalici kayit yardimcilari eklendi.
- [x] Yorum on-isleme (text cleaning) katmani eklendi.
- [x] Coklu algoritma karsilastirma modulu eklendi.
- [x] Yeni API endpoint: `POST /api/sentiment/compare`.
- [x] Cekilen yorumlar snapshot olarak `data/analysis_runs/` altina yaziliyor.

## Phase 2 - Algorithm Evaluation (Siradaki adim)

Hedef: 2-3 algoritmayi ayni veri uzerinde karsilastirip karar vermek.

- [ ] Degerlendirme metriği belirle (accuracy yerine su asamada tutarlilik ve hata analizi).
- [ ] 30-50 yorumluk mini etiketli kontrol seti olustur.
- [ ] `bert` ve `hybrid` ciktilarini ayni set icin kaydet.
- [ ] Hatali siniflanan ornekleri etiketle.
- [ ] Ana algoritma kararini ver (`hybrid` aday).

## Phase 3 - Frontend Integration (Siradaki adim)

- [ ] Duygu analizi calistir butonu ekle.
- [ ] Kanal bazli duygu dagilimi (pozitif/negatif/notr) goster.
- [ ] Grup bazli ozet kartlari ekle.
- [ ] Karsilastirma modunda algoritmalar arasi sonuc farki tablosu ekle.

## Phase 4 - UX and Reliability

- [ ] Analiz loading/progress durumlari.
- [ ] Bos veri/eksik veri durum mesajlari.
- [ ] JSON kayit dosyasi linki veya son run bilgisi gosterimi.
- [ ] Basit retry mekanizmasi.

## Phase 5 - Free Deployment

- [ ] Frontend: Vercel
- [ ] Backend: Render
- [ ] Environment variable setup
- [ ] CORS allow list ayari
- [ ] Post-deploy smoke test

## API Notes

### 1) Yorum cekme
`POST /api/replies`

Bu cagridan sonra yorumlar backend tarafinda temizlenerek memory response'a girer ve snapshot dosyasina kaydedilir.

### 2) Sentiment compare
`POST /api/sentiment/compare`

Girdi: `matched_groups` + `algorithms`
Varsayilan algoritmalar: `bert`, `hybrid`

Cikti:
- grup bazli kanal sonuclari
- algoritma bazli summary
- `best_algorithm`
- kaydedilen JSON dosya yolu (save aciksa)
