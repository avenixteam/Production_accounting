# 1-bosqich: frontend'ni build qilish
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_URL=/api
RUN npm run build

# 2-bosqich: Caddy statik fayllarni beradi va /api ni backend'ga yo'naltiradi
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
