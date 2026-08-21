FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/api
# 可通过 build arg 指定 npm 镜像源（国内网络建议用 npmmirror）
ARG NPM_REGISTRY=https://registry.npmjs.org
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json* ./
RUN npm install --registry=${NPM_REGISTRY}

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
