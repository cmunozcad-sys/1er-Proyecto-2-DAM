# Imagen ligera de Node 24
FROM node:24-alpine

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar el código e instalar las dependencias
COPY package.json server.js db.js odoo.js sincronizador.js probar_odoo.js ./
RUN npm install

# Arrancar la API
CMD ["node", "server.js"]
