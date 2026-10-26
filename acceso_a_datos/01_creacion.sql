DROP TABLE IF EXISTS log_eventos, linea_pedido, pedido, stock, variante, modelo, cliente, usuario, rol_permiso, permiso, rol CASCADE;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(200)
);

CREATE TABLE permiso (
    id_permiso SERIAL PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    descripcion VARCHAR(200)
);

CREATE TABLE rol_permiso (
    id_rol INTEGER NOT NULL REFERENCES rol(id_rol),
    id_permiso INTEGER NOT NULL REFERENCES permiso(id_permiso),
    PRIMARY KEY (id_rol, id_permiso)
);

CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    username VARCHAR(40) NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT now(),
    ultimo_acceso TIMESTAMP,
    id_rol INTEGER NOT NULL REFERENCES rol(id_rol)
);

CREATE TABLE cliente (
    id_cliente SERIAL PRIMARY KEY,
    ref_odoo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('CLUB', 'EQUIPO', 'EMPRESA', 'PARTICULAR')),
    cif VARCHAR(15) UNIQUE,
    email VARCHAR(120) UNIQUE,
    telefono VARCHAR(20),
    direccion VARCHAR(150),
    ciudad VARCHAR(60),
    activo BOOLEAN NOT NULL DEFAULT true,
    fecha_alta DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE modelo (
    id_modelo SERIAL PRIMARY KEY,
    ref_odoo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL UNIQUE,
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('correr', 'botas', 'futbol', 'baloncesto')),
    descripcion VARCHAR(300),
    precio_base NUMERIC(10,2) NOT NULL CHECK (precio_base > 0),
    personalizable BOOLEAN NOT NULL DEFAULT true,
    imagen VARCHAR(100),
    destacado BOOLEAN NOT NULL DEFAULT false,
    activo BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE variante (
    id_variante SERIAL PRIMARY KEY,
    sku VARCHAR(30) NOT NULL UNIQUE,
    color VARCHAR(40) NOT NULL,
    precio_extra NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (precio_extra >= 0),
    activo BOOLEAN NOT NULL DEFAULT true,
    id_modelo INTEGER NOT NULL REFERENCES modelo(id_modelo),
    UNIQUE (id_modelo, color)
);

CREATE TABLE stock (
    id_variante INTEGER NOT NULL REFERENCES variante(id_variante),
    talla NUMERIC(3,1) NOT NULL CHECK (talla BETWEEN 30 AND 48),
    cantidad INTEGER NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 5 CHECK (stock_minimo >= 0),
    ultima_actualizacion TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (id_variante, talla)
);

CREATE TABLE pedido (
    id_pedido SERIAL PRIMARY KEY,
    ref_odoo VARCHAR(20) NOT NULL UNIQUE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('ESTANDAR', 'CUSTOM')),
    estado VARCHAR(12) NOT NULL DEFAULT 'BORRADOR' CHECK (estado IN ('BORRADOR', 'CONFIRMADO', 'CANCELADO')),
    fecha_pedido TIMESTAMP NOT NULL DEFAULT now(),
    fecha_entrega_prevista DATE,
    fecha_confirmacion TIMESTAMP,
    fecha_cancelacion TIMESTAMP,
    total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    observaciones VARCHAR(300),
    id_cliente INTEGER NOT NULL REFERENCES cliente(id_cliente),
    id_usuario INTEGER REFERENCES usuario(id_usuario),
    CHECK (fecha_entrega_prevista IS NULL OR fecha_entrega_prevista >= fecha_pedido::date)
);

CREATE TABLE linea_pedido (
    id_linea SERIAL PRIMARY KEY,
    talla NUMERIC(3,1) NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),
    personalizacion VARCHAR(200),
    texto_bordado VARCHAR(40),
    logo_club BOOLEAN NOT NULL DEFAULT false,
    id_pedido INTEGER NOT NULL REFERENCES pedido(id_pedido),
    id_variante INTEGER NOT NULL,
    FOREIGN KEY (id_variante, talla) REFERENCES stock(id_variante, talla)
);

CREATE TABLE log_eventos (
    id_log BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMP NOT NULL DEFAULT clock_timestamp(),
    tabla VARCHAR(30) NOT NULL,
    operacion VARCHAR(10) NOT NULL CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE')),
    registro_id INTEGER NOT NULL,
    accion VARCHAR(50),
    resumen JSONB,
    id_usuario INTEGER REFERENCES usuario(id_usuario)
);

CREATE INDEX idx_pedido_cliente ON pedido(id_cliente);
CREATE INDEX idx_pedido_estado ON pedido(estado);
CREATE INDEX idx_pedido_fecha ON pedido(fecha_pedido);
CREATE INDEX idx_linea_pedido ON linea_pedido(id_pedido);
CREATE INDEX idx_linea_stock ON linea_pedido(id_variante, talla);
CREATE INDEX idx_log_fecha ON log_eventos(fecha);
