# UI Standards (Contract)

Bu doküman, `frontend/` arayüzünün **tasarım sistemi + davranış sözleşmesi**dir. Yeni eklenecek her ekran/bileşen bu kurallara uymalıdır.

## 1) i18n (TR/EN)
- **Varsayılan dil**: `tr` (fallback: `en`)
- **Kural**: UI metinleri *hardcoded* yazılmaz. Tüm metinler `t('namespace:key')` ile gelir.
- **Locale formatları**:
  - Tarih/saat/sayı formatı aktif locale’a göre yapılır.
  - API’den gelen kullanıcı içeriği (tweet metni, handle, kanal adı) çevrilmez.
- **HTML dili**: aktif locale değişince `document.documentElement.lang` güncellenir (`tr`/`en`).

## 2) Tema (dark/light/system)
- **Zorunlu modlar**: `dark | light | system`
- **Token kuralı**:
  - Komponentler doğrudan renk hex’i kullanmaz; `var(--token)` kullanır.
  - Tema renkleri `html[data-theme="dark"]` ve `html[data-theme="light"]` altında tanımlanır.
- **System modu**:
  - Kullanıcı `system` seçerse OS `prefers-color-scheme` izlenir ve `data-theme` otomatik set edilir.
- **Persist**: tema tercihi `localStorage`’da saklanır.

## 3) Motion (şık ama “AI demo” değil)
Amaç: premium his, düşük gürültü.

### Zorunlular
- **Tek easing**: `--ease-out`
- **Süreler**:
  - `--transition-fast`: 120–160ms
  - `--transition-normal`: 200–260ms
  - `--transition-slow`: 320–420ms
- **Performans**: animasyonlar `transform`/`opacity` ağırlıklı olmalı.
- **Reduced motion**: `prefers-reduced-motion: reduce` durumunda animasyonlar kapatılır veya minimal fade’e düşer.

### Yasaklar (AI mockup hissi)
- Neon glow pulse, sürekli gradient sweep, particle/parıltı
- 3D tilt/rotate gösterişi
- Loop animasyonlar (yükleme dışında)
- 600ms+ ağır geçişler

### Nerelerde micro-interaction var?
- Nav icon hover/active: kısa bg + color transition
- Kanal sekmeleri: active underline/bg + içerik `fade+slide (2–4px)`
- Tweet kartı: hover’da border + 1–2px lift; press state `scale(0.99)`
- Yorum açılır panel: caret rotate; içerik `fade+slide`
- Skeleton → içerik: kısa fade

## 4) Component sözlüğü (tek kaynak)
Bu bileşenler “temel bloklar”dır; yeni UI bunları kullanarak büyütülür.

- `Avatar`: harf avatar + opsiyonel logo, daima dairesel.
- `Badge`: kanal/etiket rozetleri; `--accent-soft` vb. tokenlarla.
- `Tabs`: kanal sekmeleri gibi yatay seçimler (overflow destekli).
- `SegmentedControl`: tema/dil/model seçimi için.
- `Metric`: etkileşim/istatistik satırı (ikon + sayı).
- `EmptyState`: onboarding + boş ekranlar (CTA opsiyonlu).
- `Drawer/Expandable`: yorum listesi gibi açılır alanlar.

## 5) Dashboard UX kuralları
- Seçili grupta **tek tweet kartı** gösterilir.
- Kart üstünde **kanal sekmeleri** (logo/harf avatar + handle) görünür biçimde yer alır.
- Medya alanı: şimdilik sakin placeholder (aspect-ratio kutusu).

## 6) Yorumlar UX kuralları
- Yorumlar **tek listede** birleştirilir.
- Her yorum: avatar (baş harf), ad/handle, tarih, metin, metrikler.
- Kaynak kanal etiketi gösterilir (hangi kanal tweet’inden geldiği kaybolmasın).
- Filtreler:
  - Sıralama: en yeni / en çok beğenilen
  - Analiz varsa: duygu filtresi (tümü / pozitif / negatif / nötr) seçili modele göre

## 7) Analiz paneli kuralları
- `Duygu Analizi Sonuçları` altında model seçimi (segmented).
- Seçili model, tüm özet/graph/kıyas render’ını belirler.
- Kanal kıyas dili sade: rozet/metric; gösterişli “🏆” tarzı vurgu minimum.

## 8) Performans sözleşmesi
- Büyük listelerde gereksiz re-render yok (memoization).
- Ağır iş: `useMemo`/`useCallback` ile stabilize edilir.
- Çok büyük grup listesi için opsiyonel virtualization stratejisi hazır tutulur.

