#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Sunucuda tek komutla deploy:  ./scripts/deploy.sh
# ----------------------------------------------------------------------
set -euo pipefail

# Renkler
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Proje root'una geç (script nereden çağrılırsa çağrılsın)
cd "$(dirname "$0")/.."

step() { echo -e "\n${BLUE}==> $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; }

# ---------- 1. Önkoşul kontrolleri ----------
step "1/6  Önkoşullar kontrol ediliyor"
command -v docker >/dev/null 2>&1 || { err "docker bulunamadı. Kurulum: curl -fsSL https://get.docker.com | sh"; exit 1; }
docker compose version >/dev/null 2>&1 || { err "docker compose plugin yok"; exit 1; }
ok "Docker hazır"

if [ ! -f .env ]; then
    err ".env dosyası yok. Sunucuda once 'nano .env' ile oluşturun."
    exit 1
fi
ok ".env mevcut"

# ---------- 2. Git pull ----------
step "2/6  Git'ten son sürüm çekiliyor"
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})
if [ "$LOCAL" = "$REMOTE" ]; then
    warn "Yeni commit yok ama yine de build yapacağız (env veya Dockerfile değişmiş olabilir)"
else
    git reset --hard "@{u}"
    ok "Kod güncellendi: $(git log -1 --oneline)"
fi

# ---------- 3. Build & up ----------
step "3/6  Docker imajları build ediliyor (ilk seferde 10-15 dk sürebilir)"
docker compose up -d --build

# ---------- 4. Eski imajları temizle ----------
step "4/6  Eski / dangling imajlar temizleniyor"
docker image prune -f >/dev/null
ok "Temizlik tamam"

# ---------- 5. Sağlık kontrolü ----------
step "5/6  Servisler ayağa kalkıyor (15s bekleme)"
sleep 15
docker compose ps

echo ""
# Backend host'ta 8001, container içinde 8000
if curl -fs http://127.0.0.1:8001/health >/dev/null; then
    ok "Backend sağlık endpoint'i 200 döndü (port 8001)"
else
    err "Backend cevap vermedi! Logları kontrol et: docker compose logs backend"
    exit 1
fi

# Frontend host'ta 3001 (NPM bu porta proxy yapıyor)
if curl -fsI "http://127.0.0.1:3001/" >/dev/null; then
    ok "Frontend cevap veriyor (port 3001)"
else
    warn "Frontend port 3001 cevap vermedi — eski PM2 process'i durduruldu mu?"
fi

# ---------- 6. Bitti ----------
step "6/6  Deploy tamamlandı"
echo -e "${GREEN}Logları izlemek için:${NC}  docker compose logs -f --tail 50"
echo -e "${GREEN}Durum için:${NC}           docker compose ps"
echo -e "${GREEN}Yeniden başlat:${NC}      docker compose restart"
