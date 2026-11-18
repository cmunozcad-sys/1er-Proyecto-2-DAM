// Conexión con PostgreSQL. Los datos de acceso salen del .env

const { Pool } = require("pg");

const pool = new Pool({
    host: process.env.DB_HOST,
    port: Number(process.env.DB_PORT),
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD
});

// Se usa en server.js y en sincronizador.js
module.exports = pool;
