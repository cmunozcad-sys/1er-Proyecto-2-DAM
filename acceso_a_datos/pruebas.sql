-- 1. INSERT, UPDATE y DELETE sobre datos de prueba

-- 1.1 INSERT: un cliente nuevo
INSERT INTO cliente (ref_odoo, nombre, tipo, email, ciudad)
VALUES ('CLI-007', 'Club Natación Prueba', 'CLUB', 'prueba@ejemplo.com', 'Madrid');

-- 1.2 UPDATE: cambiar su teléfono
UPDATE cliente SET telefono = '600000007' WHERE ref_odoo = 'CLI-007';

-- 1.3 DELETE: borrarlo
DELETE FROM cliente WHERE ref_odoo = 'CLI-007';

SELECT * FROM cliente WHERE ref_odoo = 'CLI-007';

-- 2. RESTRICCIONES QUE EVITAN DATOS INCOHERENTES

-- 2.1 Cantidad negativa en una línea
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0003'), 5, 42, -3, 74.99);

-- 2.2 Pedido de un cliente que no existe
INSERT INTO pedido (ref_odoo, tipo, id_cliente)
VALUES ('PED-9999', 'ESTANDAR', 999);

-- 2.3 Borrar un cliente que tiene pedidos
DELETE FROM cliente WHERE ref_odoo = 'CLI-001';

-- 2.4 Pedir una talla que no existe para ese modelo
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0003'), 5, 30, 1, 74.99);

-- 2.5 Un estado de pedido inventado
INSERT INTO pedido (ref_odoo, tipo, estado, id_cliente)
VALUES ('PED-9998', 'ESTANDAR', 'ENVIADO', 1);

-- 2.6 Dos usuarios con el mismo nombre
INSERT INTO usuario (username, password_hash, nombre_completo, id_rol)
VALUES ('admin', crypt('otra', gen_salt('bf')), 'Admin duplicado', 1);

SELECT COUNT(*) AS pedidos FROM pedido;
SELECT COUNT(*) AS usuarios FROM usuario;

-- 3. PRUEBA A: pedido Custom completo

-- 3.1 Ver el stock de la Cometa ANTES
SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

-- 3.2 Crear el pedido y sus líneas
BEGIN;
SELECT set_config('app.id_usuario', '2', true);

INSERT INTO pedido (ref_odoo, tipo, id_cliente, id_usuario, observaciones)
VALUES ('CUS-0005', 'CUSTOM', 1, 2, 'Prueba A: 40 pares para el club');

INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario, personalizacion, texto_bordado, logo_club)
SELECT p.id_pedido, 1, t.talla, t.cantidad, 69.99, 'Colores del club: rojo y blanco', 'HALCONES', true
FROM pedido p,
     (VALUES (38, 4), (39, 6), (40, 8), (41, 8), (42, 6), (43, 4), (44, 4)) AS t(talla, cantidad)
WHERE p.ref_odoo = 'CUS-0005';

COMMIT;

-- 3.3 Ver el total
SELECT ref_odoo, estado, total FROM pedido WHERE ref_odoo = 'CUS-0005';

-- 3.4 Confirmar el pedido
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CONFIRMADO' WHERE ref_odoo = 'CUS-0005';
COMMIT;

-- 3.5 Ver el stock de la Cometa DESPUÉS
SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

-- 3.6 Ver la auditoría
SELECT id_log, fecha, tabla, operacion, registro_id, accion, id_usuario
FROM log_eventos
ORDER BY id_log;

-- 4. PRUEBA B: confirmar un pedido sin stock suficiente

-- 4.1 Crear el pedido en borrador
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
INSERT INTO pedido (ref_odoo, tipo, id_cliente, id_usuario)
VALUES ('PED-0007', 'ESTANDAR', 4, 2);
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0007'), 19, 42, 5, 109.99);
COMMIT;

-- 4.2 Intentar confirmarlo
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CONFIRMADO' WHERE ref_odoo = 'PED-0007';
ROLLBACK;

-- 4.3 Comprobar el pedido y el stock
SELECT ref_odoo, estado, fecha_confirmacion FROM pedido WHERE ref_odoo = 'PED-0007';
SELECT talla, cantidad FROM stock WHERE id_variante = 19 AND talla = 42;

-- 5. PRUEBA C: cancelar un pedido confirmado

BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CANCELADO' WHERE ref_odoo = 'CUS-0005';
COMMIT;

SELECT ref_odoo, estado, fecha_confirmacion, fecha_cancelacion FROM pedido WHERE ref_odoo = 'CUS-0005';

SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

SELECT id_log, fecha, accion, id_usuario
FROM log_eventos
WHERE accion LIKE 'CAMBIO ESTADO%'
ORDER BY id_log;

-- 6. PRUEBA D: ROLLBACK deliberado

-- 6.1 Contar las entradas de auditoría antes
SELECT COUNT(*) AS entradas_log FROM log_eventos;

-- 6.2 Cambiar algo y deshacerlo
BEGIN;
SELECT set_config('app.id_usuario', '1', true);
UPDATE pedido SET observaciones = 'Cambio que se va a deshacer' WHERE ref_odoo = 'PED-0006';
SELECT COUNT(*) AS entradas_dentro FROM log_eventos;
ROLLBACK;

-- 6.3 Contar las entradas después del ROLLBACK
SELECT COUNT(*) AS entradas_log FROM log_eventos;
SELECT ref_odoo, observaciones FROM pedido WHERE ref_odoo = 'PED-0006';

-- 7. LA AUDITORÍA SOLO SE VE EN OTRAS CONEXIONES TRAS EL COMMIT

-- PESTAÑA 1: cambio sin COMMIT
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET observaciones = 'Revisado por el comercial' WHERE ref_odoo = 'PED-0006';

-- PESTAÑA 2: consultar el log
--   SELECT id_log, accion, registro_id FROM log_eventos ORDER BY id_log DESC LIMIT 1;

-- PESTAÑA 1: COMMIT
COMMIT;

-- PESTAÑA 2: volver a consultar el log
--   SELECT id_log, accion, registro_id FROM log_eventos ORDER BY id_log DESC LIMIT 1;

-- 8. OTRAS PROTECCIONES DE LOS TRIGGERS

-- 8.1 Modificar una línea de un pedido ya confirmado
UPDATE linea_pedido SET cantidad = 1
WHERE id_pedido = (SELECT id_pedido FROM pedido WHERE ref_odoo = 'CUS-0004');

-- 8.2 Volver a poner en borrador un pedido cancelado
UPDATE pedido SET estado = 'BORRADOR' WHERE ref_odoo = 'CUS-0005';
