# === Build aşaması ===
FROM node:20-alpine AS builder

WORKDIR /app

# Paket manifestlerini önce kopyala (cache için)
COPY package*.json ./
RUN npm ci

# Kaynak kodu kopyala
COPY . .

# Vite build-time env (compose'dan args ile gelir, runtime'da değiştirilemez)
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# === Serve aşaması ===
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
