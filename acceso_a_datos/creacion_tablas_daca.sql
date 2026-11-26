-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 0.9.4
-- PostgreSQL version: 13.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: sneaker_factory | type: DATABASE --
-- DROP DATABASE IF EXISTS sneaker_factory;
-- ddl-end --

DROP TABLE IF EXISTS log_eventos, linea_pedido, pedido, stock, variante, modelo, cliente, usuario, rol_permiso, permiso, rol CASCADE;


-- object: public.permiso | type: TABLE --
-- DROP TABLE IF EXISTS public.permiso CASCADE;
CREATE TABLE public.permiso (
	id_permiso serial NOT NULL,
	codigo varchar(40) NOT NULL,
	descripcion varchar(200),
	CONSTRAINT permiso_pk PRIMARY KEY (id_permiso),
	CONSTRAINT uq_permiso_codigo UNIQUE (codigo)
);
-- ddl-end --

-- object: public.rol_permiso | type: TABLE --
-- DROP TABLE IF EXISTS public.rol_permiso CASCADE;
CREATE TABLE public.rol_permiso (
	id_rol integer NOT NULL,
	id_permiso integer NOT NULL,
	CONSTRAINT rol_permiso_pk PRIMARY KEY (id_rol,id_permiso)
);
-- ddl-end --

-- object: public.rol | type: TABLE --
-- DROP TABLE IF EXISTS public.rol CASCADE;
CREATE TABLE public.rol (
	id_rol serial NOT NULL,
	nombre varchar(30) NOT NULL,
	descripcion varchar(200),
	CONSTRAINT rol_pk PRIMARY KEY (id_rol),
	CONSTRAINT uq_rol_nombre UNIQUE (nombre)
);
-- ddl-end --

-- object: public.usuario | type: TABLE --
-- DROP TABLE IF EXISTS public.usuario CASCADE;
CREATE TABLE public.usuario (
	id_usuario serial NOT NULL,
	username varchar(40) NOT NULL,
	password_hash varchar(100) NOT NULL,
	nombre_completo varchar(100) NOT NULL,
	activo boolean NOT NULL DEFAULT true,
	fecha_creacion timestamp NOT NULL DEFAULT now(),
	ultimo_acceso timestamp,
	id_rol integer NOT NULL,
	CONSTRAINT usuario_pk PRIMARY KEY (id_usuario),
	CONSTRAINT uq_usuario_username UNIQUE (username)
);
-- ddl-end --

-- object: public.log_eventos | type: TABLE --
-- DROP TABLE IF EXISTS public.log_eventos CASCADE;
CREATE TABLE public.log_eventos (
	id_log bigserial NOT NULL,
	fecha timestamp NOT NULL DEFAULT clock_timestamp(),
	tabla varchar(30) NOT NULL,
	operacion varchar(10) NOT NULL,
	registro_id integer NOT NULL,
	accion varchar(50),
	resumen jsonb,
	id_usuario integer,
	CONSTRAINT log_eventos_pk PRIMARY KEY (id_log),
	CONSTRAINT ck_log_eventos_operacion CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE'))
);
-- ddl-end --

-- object: public.cliente | type: TABLE --
-- DROP TABLE IF EXISTS public.cliente CASCADE;
CREATE TABLE public.cliente (
	id_cliente serial NOT NULL,
	ref_odoo varchar(20) NOT NULL,
	nombre varchar(100) NOT NULL,
	tipo varchar(20) NOT NULL,
	cif varchar(15),
	email varchar(120),
	telefono varchar(20),
	direccion varchar(150),
	ciudad varchar(60),
	activo boolean NOT NULL DEFAULT true,
	fecha_alta date NOT NULL DEFAULT CURRENT_DATE,
	CONSTRAINT cliente_pk PRIMARY KEY (id_cliente),
	CONSTRAINT uq_cliente_ref_odoo UNIQUE (ref_odoo),
	CONSTRAINT uq_cliente_cif UNIQUE (cif),
	CONSTRAINT uq_cliente_email UNIQUE (email),
	CONSTRAINT ck_cliente_tipo CHECK (tipo IN ('CLUB', 'EQUIPO', 'EMPRESA', 'PARTICULAR'))
);
-- ddl-end --

-- object: public.pedido | type: TABLE --
-- DROP TABLE IF EXISTS public.pedido CASCADE;
CREATE TABLE public.pedido (
	id_pedido serial NOT NULL,
	ref_odoo varchar(20) NOT NULL,
	tipo varchar(10) NOT NULL,
	estado varchar(12) NOT NULL DEFAULT 'BORRADOR',
	fecha_pedido timestamp NOT NULL DEFAULT now(),
	fecha_entrega_prevista date,
	fecha_confirmacion timestamp,
	fecha_cancelacion timestamp,
	total numeric(12,2) NOT NULL DEFAULT 0,
	observaciones varchar(300),
	id_cliente integer NOT NULL,
	id_usuario integer,
	CONSTRAINT pedido_pk PRIMARY KEY (id_pedido),
	CONSTRAINT uq_pedido_ref_odoo UNIQUE (ref_odoo),
	CONSTRAINT ck_pedido_tipo CHECK (tipo IN ('ESTANDAR', 'CUSTOM')),
	CONSTRAINT ck_pedido_estado CHECK (estado IN ('BORRADOR', 'CONFIRMADO', 'CANCELADO')),
	CONSTRAINT ck_pedido_total CHECK (total >= 0),
	CONSTRAINT ck_pedido_entrega CHECK (fecha_entrega_prevista IS NULL OR fecha_entrega_prevista >= fecha_pedido::date)
);
-- ddl-end --

-- object: public.linea_pedido | type: TABLE --
-- DROP TABLE IF EXISTS public.linea_pedido CASCADE;
CREATE TABLE public.linea_pedido (
	id_linea serial NOT NULL,
	talla numeric(3,1) NOT NULL,
	cantidad integer NOT NULL,
	precio_unitario numeric(10,2) NOT NULL,
	personalizacion varchar(200),
	texto_bordado varchar(40),
	logo_club boolean NOT NULL DEFAULT false,
	id_pedido integer NOT NULL,
	id_variante integer NOT NULL,
	CONSTRAINT uq_linea_pedido UNIQUE (id_pedido, id_variante, talla),
	CONSTRAINT linea_pedido_pk PRIMARY KEY (id_linea),
	CONSTRAINT ck_linea_pedido_cantidad CHECK (cantidad > 0),
	CONSTRAINT ck_linea_pedido_precio CHECK (precio_unitario >= 0)
);
-- ddl-end --

-- object: public.modelo | type: TABLE --
-- DROP TABLE IF EXISTS public.modelo CASCADE;
CREATE TABLE public.modelo (
	id_modelo serial NOT NULL,
	ref_odoo varchar(20) NOT NULL,
	nombre varchar(60) NOT NULL,
	categoria varchar(20) NOT NULL,
	descripcion varchar(300),
	precio_base numeric(10,2) NOT NULL,
	personalizable boolean NOT NULL DEFAULT true,
	imagen varchar(100),
	destacado boolean NOT NULL DEFAULT false,
	activo boolean NOT NULL DEFAULT true,
	CONSTRAINT modelo_pk PRIMARY KEY (id_modelo),
	CONSTRAINT uq_modelo_ref_odoo UNIQUE (ref_odoo),
	CONSTRAINT uq_modelo_nombre UNIQUE (nombre),
	CONSTRAINT ck_modelo_categoria CHECK (categoria IN ('correr', 'botas', 'futbol', 'baloncesto')),
	CONSTRAINT ck_modelo_precio CHECK (precio_base > 0)
);
-- ddl-end --

-- object: public.variante | type: TABLE --
-- DROP TABLE IF EXISTS public.variante CASCADE;
CREATE TABLE public.variante (
	id_variante serial NOT NULL,
	sku varchar(30) NOT NULL,
	color varchar(40) NOT NULL,
	precio_extra numeric(10,2) NOT NULL DEFAULT 0,
	activo boolean NOT NULL DEFAULT true,
	id_modelo integer NOT NULL,
	CONSTRAINT variante_pk PRIMARY KEY (id_variante),
	CONSTRAINT uq_variante_sku UNIQUE (sku),
	CONSTRAINT uq_variante_modelo_color UNIQUE (id_modelo,color),
	CONSTRAINT ck_variante_precio_extra CHECK (precio_extra >= 0)
);
-- ddl-end --

-- object: public.stock | type: TABLE --
-- DROP TABLE IF EXISTS public.stock CASCADE;
CREATE TABLE public.stock (
	id_variante integer NOT NULL,
	talla numeric(3,1) NOT NULL,
	cantidad integer NOT NULL DEFAULT 0,
	stock_minimo integer NOT NULL DEFAULT 5,
	ultima_actualizacion timestamp NOT NULL DEFAULT now(),
	CONSTRAINT stock_pk PRIMARY KEY (id_variante,talla),
	CONSTRAINT ck_stock_talla CHECK (talla BETWEEN 30 AND 48),
	CONSTRAINT ck_stock_cantidad CHECK (cantidad >= 0),
	CONSTRAINT ck_stock_minimo CHECK (stock_minimo >= 0)
);
-- ddl-end --

-- object: fk_rol_permiso_id_rol_rol | type: CONSTRAINT --
-- ALTER TABLE public.rol_permiso DROP CONSTRAINT IF EXISTS fk_rol_permiso_id_rol_rol CASCADE;
ALTER TABLE public.rol_permiso ADD CONSTRAINT fk_rol_permiso_id_rol_rol FOREIGN KEY (id_rol)
REFERENCES public.rol (id_rol) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_rol_permiso_id_permiso_permiso | type: CONSTRAINT --
-- ALTER TABLE public.rol_permiso DROP CONSTRAINT IF EXISTS fk_rol_permiso_id_permiso_permiso CASCADE;
ALTER TABLE public.rol_permiso ADD CONSTRAINT fk_rol_permiso_id_permiso_permiso FOREIGN KEY (id_permiso)
REFERENCES public.permiso (id_permiso) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_usuario_id_rol_rol | type: CONSTRAINT --
-- ALTER TABLE public.usuario DROP CONSTRAINT IF EXISTS fk_usuario_id_rol_rol CASCADE;
ALTER TABLE public.usuario ADD CONSTRAINT fk_usuario_id_rol_rol FOREIGN KEY (id_rol)
REFERENCES public.rol (id_rol) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_log_eventos_id_usuario_usuario | type: CONSTRAINT --
-- ALTER TABLE public.log_eventos DROP CONSTRAINT IF EXISTS fk_log_eventos_id_usuario_usuario CASCADE;
ALTER TABLE public.log_eventos ADD CONSTRAINT fk_log_eventos_id_usuario_usuario FOREIGN KEY (id_usuario)
REFERENCES public.usuario (id_usuario) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_pedido_id_cliente_cliente | type: CONSTRAINT --
-- ALTER TABLE public.pedido DROP CONSTRAINT IF EXISTS fk_pedido_id_cliente_cliente CASCADE;
ALTER TABLE public.pedido ADD CONSTRAINT fk_pedido_id_cliente_cliente FOREIGN KEY (id_cliente)
REFERENCES public.cliente (id_cliente) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_pedido_id_usuario_usuario | type: CONSTRAINT --
-- ALTER TABLE public.pedido DROP CONSTRAINT IF EXISTS fk_pedido_id_usuario_usuario CASCADE;
ALTER TABLE public.pedido ADD CONSTRAINT fk_pedido_id_usuario_usuario FOREIGN KEY (id_usuario)
REFERENCES public.usuario (id_usuario) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_linea_pedido_id_pedido_pedido | type: CONSTRAINT --
-- ALTER TABLE public.linea_pedido DROP CONSTRAINT IF EXISTS fk_linea_pedido_id_pedido_pedido CASCADE;
ALTER TABLE public.linea_pedido ADD CONSTRAINT fk_linea_pedido_id_pedido_pedido FOREIGN KEY (id_pedido)
REFERENCES public.pedido (id_pedido) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_linea_pedido_stock | type: CONSTRAINT --
-- ALTER TABLE public.linea_pedido DROP CONSTRAINT IF EXISTS fk_linea_pedido_stock CASCADE;
ALTER TABLE public.linea_pedido ADD CONSTRAINT fk_linea_pedido_stock FOREIGN KEY (id_variante,talla)
REFERENCES public.stock (id_variante,talla) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_variante_id_modelo_modelo | type: CONSTRAINT --
-- ALTER TABLE public.variante DROP CONSTRAINT IF EXISTS fk_variante_id_modelo_modelo CASCADE;
ALTER TABLE public.variante ADD CONSTRAINT fk_variante_id_modelo_modelo FOREIGN KEY (id_modelo)
REFERENCES public.modelo (id_modelo) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --

-- object: fk_stock_id_variante_variante | type: CONSTRAINT --
-- ALTER TABLE public.stock DROP CONSTRAINT IF EXISTS fk_stock_id_variante_variante CASCADE;
ALTER TABLE public.stock ADD CONSTRAINT fk_stock_id_variante_variante FOREIGN KEY (id_variante)
REFERENCES public.variante (id_variante) MATCH SIMPLE
ON DELETE RESTRICT ON UPDATE NO ACTION;
-- ddl-end --


