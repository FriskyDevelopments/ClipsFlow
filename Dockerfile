# Build stage — compile TypeScript to dist/
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# Runtime stage — production deps only
FROM node:20-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist

# Persist the JSON store on a mounted volume in production.
ENV CLIPS_DATA_DIR=/app/data
RUN mkdir -p /app/data && chown -R node:node /app/data
VOLUME ["/app/data"]

USER node
EXPOSE 3000
CMD ["node", "dist/index.js"]
