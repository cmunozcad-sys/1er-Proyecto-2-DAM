FROM node:24-alpine

WORKDIR /app

COPY package.json server.js db.js ./
RUN npm install

CMD ["node", "server.js"]
