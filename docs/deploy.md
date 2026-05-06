# Deploy Rehberi (Docker + Nginx Proxy Manager)

Bu rehber, Twitter Duygu Analizi projesini self-hosted bir sunucuda **Docker + docker-compose** ile yayına almanın adım adım anlatımıdır. Mevcut **Nginx Proxy Manager (NPM)** ve Cloudflare yapısı korunur — sadece arka tarafta PM2 yerine Docker container'ları çalışır.

> Hedef domain: `https://twitter.mericozkaya.me`
> Sunucu local IP: `192.168.1.13`

---

## 0. Mimari özet

```
İnternet
   │
Cloudflare (DNS + TLS)
   │
   ▼
Nginx Proxy Manager (npm.mericozkaya.me)
   │  twitter.mericozkaya.me proxy host
   │
   ├── /         ───► http://192.168.1.13:3001  (frontend container)
   └── /api/     ───► http://192.168.1.13:8001  (backend container)  [yeni eklenecek]
```

### Port haritası

| Port | Kim kullanıyor | Bu projede |
|------|----------------|-----------|
| 80, 81 | NPM | Dokunulmaz |
| 3000 | pipelineflow | Dokunulmaz |
| **3001** | Twitter frontend | **Korundu** (NPM zaten buraya bakıyor) |
| 5216 | myspeed | Dokunulmaz |
| **8000** | api-pipelineflow | **Dokunulmaz** |
| **8001** | (boş) | **Twitter backend için kullanılacak** |
| 9000 | portainer | Dokunulmaz |

> **Frontend için 3001 portu mevcut NPM kaydı olduğu gibi kalır.** Backend için yeni `/api/` location ekleyeceğiz, ek subdomain veya port forwarding yok.

---

## 1. İLK KURULUM (sadece bir kere yapılır)

### 1.1 Sunucuya bağlan

```bash
ssh kullanici_adin@192.168.1.13   # veya kullandığınız adres
```

### 1.2 Docker yüklü mü kontrol et

```bash
docker --version
docker compose version
```

Yoksa kur:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 1.3 Veriyi yedekle

```bash
cd ~/Twitter-Duygu-Analizi
tar -czf ~/data-backup-$(date +%Y%m%d).tar.gz data/
ls -lh ~/data-backup-*.tar.gz
```

### 1.4 PM2 process'lerini durdur ve sil

Docker'a geçtiğimiz için 3001 ve eski backend portunu serbest bırakmamız gerek:

```bash
pm2 list                              # mevcut process'leri gör
pm2 stop twitter-backend twitter-frontend
pm2 delete twitter-backend twitter-frontend
pm2 save
pm2 list                              # listeden tamamen düştüklerini doğrula
```

> Diğer projeleri (pipelineflow, myspeed, vb.) PM2'de yönetiyorsanız onlara dokunmuyoruz, sadece `twitter-*` olanları kaldırıyoruz.

### 1.5 .env dosyasını güncelle

```bash
nano .env
```

Aşağıdaki satırlar olmalı:

```env
# Mevcut anahtarlar
GEMINI_API_KEY=...
TWITTER_BEARER_TOKEN=...
TWITTER_AUTH_TOKEN=...
TWITTER_CT0=...
GROQ_API_KEY=...                  # opsiyonel
LLM_PROVIDER=groq                 # opsiyonel

# Backend CORS — frontend'in domain'i
CORS_ORIGINS=https://twitter.mericozkaya.me

# Frontend build-time: API hangi URL'ye gidecek?
# Aynı subdomain altında /api yolu kullanacağız
VITE_API_BASE_URL=https://twitter.mericozkaya.me
```

> **Önemli:** `VITE_API_BASE_URL` build-time bir değişkendir. Değişirse frontend'i `--build frontend` ile yeniden build etmek gerekir.

### 1.6 Nginx Proxy Manager'da `/api` location'ı ekle

NPM web arayüzüne (`https://npm.mericozkaya.me` veya local IP) girin.

1. **Hosts → Proxy Hosts** menüsüne git.
2. `twitter.mericozkaya.me` satırının sağındaki **3 nokta menüsüne** tıkla → **Edit**.
3. Açılan modalde:
   - **Details** sekmesi: Forward Hostname/IP `192.168.1.13`, Forward Port `3001` (DEĞİŞMESİN — frontend için).
   - **Custom locations** sekmesine geç.
   - **+ Add Location** butonuna bas.
   - Aşağıdaki gibi doldur:

   | Alan | Değer |
   |---|---|
   | **Define location** | `/api` |
   | **Scheme** | `http` |
   | **Forward Hostname/IP** | `192.168.1.13` |
   | **Forward Port** | `8001` |

   Sağdaki "gear" (dişli) ikonuna tıklayıp aşağıdaki advanced config'i ekle (önemli — uzun süreli istekler için):

   ```nginx
   client_max_body_size 10m;
   proxy_read_timeout 300s;
   proxy_connect_timeout 60s;
   proxy_send_timeout 300s;
   ```

4. **Save**'e bas.

> **Test:** Bu adımdan sonra (Docker daha çalışmasa bile) NPM artık `twitter.mericozkaya.me/api/*` isteklerini `192.168.1.13:8001`'e yönlendirir. Backend ayağa kalktığında çalışacak.

### 1.7 Deploy scriptini çalıştırılabilir yap

```bash
chmod +x scripts/deploy.sh
```

### 1.8 İlk deploy

```bash
./scripts/deploy.sh
```

> **İlk build 10-15 dakika sürer** (PyTorch ~750 MB indirilir). Sonraki build'ler cache sayesinde çok hızlı.

### 1.9 Doğrula

```bash
docker compose ps
# twitter-backend ve twitter-frontend "Up" görünmeli, backend "(healthy)"

# Backend
curl -s http://127.0.0.1:8001/health
# {"status":"ok"}

# Frontend
curl -sI http://127.0.0.1:3001/
# HTTP/1.1 200 OK
```

Sonra tarayıcıda:
1. `https://twitter.mericozkaya.me` → arayüz açılmalı
2. DevTools → Network sekmesi açıkken bir analiz başlat → `https://twitter.mericozkaya.me/api/...` istekleri 200 dönmeli.

---

## 2. RUTİN DEPLOY (her güncelleme)

```bash
ssh kullanici_adin@192.168.1.13
cd ~/Twitter-Duygu-Analizi
./scripts/deploy.sh
```

Tek komut. Script:
1. `git fetch` + `git reset --hard origin/main`
2. `docker compose up -d --build`
3. Eski imajları temizler
4. Backend ve frontend için health check yapar

---

## 3. .ENV GÜNCELLEME

```bash
ssh kullanici_adin@192.168.1.13
cd ~/Twitter-Duygu-Analizi
nano .env
```

| Değişen değişken | Yapılacak |
|---|---|
| Backend env (Twitter, Gemini, vs.) | `docker compose up -d backend` |
| `VITE_API_BASE_URL` (frontend) | `docker compose up -d --build frontend` |

---

## 4. SORUN GİDERME

### 4.1 Loglar

```bash
docker compose logs -f --tail 100              # iki servisin de canlı logu
docker compose logs -f backend                 # sadece backend
docker compose logs -f frontend                # sadece frontend
```

Ctrl+C ile çık.

### 4.2 Tek servisi yeniden başlat

```bash
docker compose restart backend
docker compose restart frontend
```

### 4.3 Tamamen sıfırdan ayağa kaldır

```bash
docker compose down
docker compose up -d --build
```

### 4.4 Container'ın içine gir (debug)

```bash
docker compose exec backend bash
docker compose exec frontend sh
```

### 4.5 "Port already in use" hatası

3001 veya 8001 portunda başka bir şey çalışıyor:

```bash
sudo lsof -i :3001
sudo lsof -i :8001
# Genelde eski PM2 process'i: pm2 list / pm2 stop X / pm2 delete X
```

### 4.6 Domain üzerinden /api/ 502 Bad Gateway dönüyor

NPM Twitter backend'e ulaşamıyor demektir.

- `docker compose ps` → backend "Up (healthy)" mi?
- Sunucudan: `curl http://127.0.0.1:8001/health` → cevap geliyor mu?
- NPM'de Custom Location doğru: `/api` → `http://192.168.1.13:8001`
- Sunucuda firewall/iptables 8001'i sunucu içinden engellemiyor mu?

### 4.7 Frontend açılıyor ama analiz başlatınca CORS hatası

`.env`'de `CORS_ORIGINS=https://twitter.mericozkaya.me` ekli mi? Sonrasında `docker compose up -d backend` ile backend'i yeniden başlat.

### 4.8 Disk dolduğunda imaj temizliği

```bash
docker system df            # ne kadar yer kaplıyor
docker image prune -f       # dangling imajlar
docker system prune -a      # DİKKAT: kullanılmayan tüm imajlar silinir
```

### 4.9 Build hatası

```bash
docker compose build --no-cache    # cache'i bypass et
```

---

## 5. ROLLBACK (geri alma)

```bash
cd ~/Twitter-Duygu-Analizi
git log --oneline -10
git checkout <bilinen-iyi-commit-hash>
./scripts/deploy.sh
# Sorun çözüldüğünde:
git checkout main
```

---

## 6. VERİ KAYBETMEMEK İÇİN

`./data/` klasörü `docker-compose.yml`'de **volume** olarak mount edildi.

✅ `docker compose down` → veri kalıcı  
✅ `docker compose up -d --build` → veri kalıcı  
❌ `rm -rf data/` → veri **gider**

Otomatik yedek (cron — her gün 03:00'da):

```bash
crontab -e
# Ekle:
# 0 3 * * * cd /home/USERNAME/Twitter-Duygu-Analizi && tar -czf ~/backups/data-$(date +\%Y\%m\%d).tar.gz data/
```

---

## 7. KOMUT KARTI (hızlı erişim)

```bash
# Deploy
./scripts/deploy.sh

# Durum
docker compose ps

# Loglar
docker compose logs -f --tail 50

# Yeniden başlat (kod değişmeden)
docker compose restart

# Sadece env değişti, build gerekmez
docker compose up -d

# Build'i zorla (Dockerfile değiştiyse)
docker compose up -d --build

# Durdur
docker compose down

# Container shell
docker compose exec backend bash

# Disk kullanımı
docker system df

# Yedek al
tar -czf ~/data-$(date +%Y%m%d).tar.gz data/
```

---

## 8. HANGİ DOSYAYA NE ZAMAN DOKUNULUR?

| Senaryo | Dokunulan dosya | Komut |
|---|---|---|
| API key değişti | `.env` (sunucuda) | `docker compose up -d backend` |
| Frontend domain veya `/api` yolu değişti | `.env` (`VITE_API_BASE_URL`) | `docker compose up -d --build frontend` |
| Yeni Python paketi | `requirements.txt` (commit + push) | `./scripts/deploy.sh` |
| Yeni npm paketi | `frontend/package.json` (commit + push) | `./scripts/deploy.sh` |
| Port değişikliği | `docker-compose.yml` | `docker compose up -d` |
| NPM config (proxy host / location) | NPM web arayüzü | NPM "Save" otomatik reload yapar |

---

## 9. NPM'DE NE YAPTIK ÖZETİ (kontrol için)

`twitter.mericozkaya.me` proxy host'unun ayarları **deploy sonunda** şöyle olmalı:

**Details sekmesi:**
- Domain: `twitter.mericozkaya.me`
- Forward Hostname/IP: `192.168.1.13`
- Forward Port: `3001`
- Cache Assets: kapalı (Vite zaten cache header'ları veriyor)
- Block Common Exploits: açık (varsayılan)
- Websockets Support: açık (her ihtimale karşı)

**SSL sekmesi:**
- Let's Encrypt (mevcut hali)
- Force SSL: açık
- HTTP/2: açık

**Custom locations sekmesi (YENİ):**
- Location: `/api` → `http://192.168.1.13:8001`
- Advanced config:
  ```nginx
  client_max_body_size 10m;
  proxy_read_timeout 300s;
  proxy_connect_timeout 60s;
  proxy_send_timeout 300s;
  ```

Diğer hiçbir proxy host'a (api-pipelineflow, myspeed, npm, pipelineflow, portainer, system) **dokunulmadı**.
