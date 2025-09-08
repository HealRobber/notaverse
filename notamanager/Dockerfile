FROM node:24 AS build
WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.29
COPY --from=build /app/build /usr/share/nginx/html/notamanager

RUN rm /etc/nginx/conf.d/default.conf