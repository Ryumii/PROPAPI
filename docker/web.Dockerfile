FROM node:20-alpine

WORKDIR /app

COPY web/package.json web/package-lock.json* ./
RUN npm ci || npm install

COPY web/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
