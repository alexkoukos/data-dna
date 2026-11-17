FROM node:22-alpine
WORKDIR /app
COPY server.mjs index.html ./
EXPOSE 3100
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -qO- http://127.0.0.1:3100/healthz >/dev/null || exit 1
USER node
CMD ["node", "server.mjs"]
