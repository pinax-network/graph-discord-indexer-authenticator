# Build image
FROM node:22.9.0-alpine3.20 AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN mv .env.placeholders .env
RUN ls -la
RUN npm run build

# Nginx image
FROM nginx:1.27.1-alpine3.20

COPY --from=build /app/dist /usr/share/nginx/html

COPY env.sh /docker-entrypoint.d/env.sh
RUN chmod +x /docker-entrypoint.d/env.sh
