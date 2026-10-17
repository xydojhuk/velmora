FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/index.html frontend/vite.config.js frontend/server.js ./
COPY VERSION /VERSION
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/scripts ./scripts

RUN npm run build

FROM node:22-alpine

ENV NODE_ENV=production

RUN addgroup -S -g 10001 velmora && adduser -S -D -H -u 10001 -G velmora velmora

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund && npm cache clean --force

COPY --from=build /app/dist ./dist
COPY frontend/server.js ./server.js

USER 10001:10001

EXPOSE 5173

CMD ["node", "server.js"]
