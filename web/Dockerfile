# Build context is the repository root (see docker-compose.yml): the extension and its shared
# rules are built in the same image, so the dashboard can serve /extension.zip.
FROM node:22-alpine AS ext
WORKDIR /app/extension
COPY extension/package.json extension/package-lock.json ./
RUN npm ci --ignore-scripts
COPY extension ./
COPY shared ../shared
RUN npx wxt prepare && npx wxt zip \
 && cp .output/*-chrome.zip /extension.zip

FROM node:22-alpine AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
RUN npm run build

# Pinned to the nginx stable line so a rebuild does not silently change versions.
FROM nginx:1.30-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=ext /extension.zip /usr/share/nginx/html/extension.zip
COPY samples /usr/share/nginx/html/samples
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -qO- http://127.0.0.1:3000/ >/dev/null || exit 1
