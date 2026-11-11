FROM node:24-alpine

WORKDIR /app

COPY package.json server.js db.js odoo.js sincronizador.js probar_odoo.js ./
RUN npm install

CMD ["node", "server.js"]
