# Twitter Duygu Analizi

Bu proje, X (Twitter) üzerindeki bir tweet'e gelen yorumları çekip Türkçe duygu analizi yapar.

## Özellikler
- Tweet yorumlarını GraphQL API ile çekme (cookie tabanlı oturum)
- Türkçe BERT ile duygu sınıflandırması
- Sonuçları JSON olarak kaydetme
- Duygu dağılımını grafik olarak gösterme

## Proje Yapısı
- `TwitCeken1.ipynb`: Tüm akışın bulunduğu notebook
- `data/yorumlar.json`: Çekilen yorumlar
- `data/yorumlar_duygu_analizi_bert.json`: Yorum bazlı BERT sonuçları
- `data/duygu_ozet_bert.json`: Toplu duygu özeti

## Kurulum
```bash
pip install -r requirements.txt
```

## Kullanım (Notebook)
1. `TwitCeken1.ipynb` dosyasını aç.
2. Hücreleri sırayla çalıştır:
   - Tweet listeleme
   - X giriş (manuel)
   - Yorum çekme
   - Duygu analizi (BERT)
3. Çıktılar `data/` klasörüne yazılır.

## Kullanılan Model
- `savasy/bert-base-turkish-sentiment-cased`

## Notlar
- X/Twitter içerik çekimi platform kurallarına tabidir.
- Hesap çerezlerini ve kişisel bilgileri paylaşmayın.
- Bu çalışma eğitim/analiz amaçlıdır.
