-- Pruebas de la base de datos
-- Lo voy ejecutando por bloques en el pgAdmin, no todo de golpe,
-- porque hay cosas que tienen que fallar a propósito.


-- 1. Lo básico: insertar, modificar y borrar

-- Meto un cliente de prueba
INSERT INTO cliente (ref_odoo, nombre, tipo, email, ciudad)
VALUES ('CLI-007', 'Club Natación Prueba', 'CLUB', 'prueba@ejemplo.com', 'Madrid');

-- Le pongo un teléfono
UPDATE cliente SET telefono = '600000007' WHERE ref_odoo = 'CLI-007';

-- Y lo borro otra vez para no dejar basura
DELETE FROM cliente WHERE ref_odoo = 'CLI-007';

-- Tiene que salir vacío
SELECT * FROM cliente WHERE ref_odoo = 'CLI-007';


-- 2. Cosas que NO deberían dejarme hacer
-- Todos estos INSERT/DELETE tienen que dar error. Si alguno entra,
-- es que me falta alguna restricción.

-- Cantidad negativa en una línea de pedido
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0003'), 5, 42, -3, 74.99);

-- Pedido para un cliente que no existe (el 999 no está)
INSERT INTO pedido (ref_odoo, tipo, id_cliente)
VALUES ('PED-9999', 'ESTANDAR', 999);

-- Borrar un cliente que ya tiene pedidos, no debería poder
DELETE FROM cliente WHERE ref_odoo = 'CLI-001';

-- Talla 30 para un modelo que no la tiene
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0003'), 5, 30, 1, 74.99);

-- 'ENVIADO' no es uno de los estados que he definido
INSERT INTO pedido (ref_odoo, tipo, estado, id_cliente)
VALUES ('PED-9998', 'ESTANDAR', 'ENVIADO', 1);

-- Otro usuario llamado admin, el username es único
INSERT INTO usuario (username, password_hash, nombre_completo, id_rol)
VALUES ('admin', crypt('otra', gen_salt('bf')), 'Admin duplicado', 1);

-- Compruebo que no se ha colado nada (tienen que salir los mismos que antes)
SELECT COUNT(*) AS pedidos FROM pedido;
SELECT COUNT(*) AS usuarios FROM usuario;


-- 3. Prueba A: un pedido Custom de principio a fin
-- 40 pares de la Cometa para un club, con bordado y logo

-- Apunto cómo está el stock antes de empezar
SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

-- Creo el pedido con todas sus líneas (una por talla)
BEGIN;
SELECT set_config('app.id_usuario', '2', true);  -- para que la auditoría sepa quién lo hace

INSERT INTO pedido (ref_odoo, tipo, id_cliente, id_usuario, observaciones)
VALUES ('CUS-0005', 'CUSTOM', 1, 2, 'Prueba A: 40 pares para el club');

-- talla, cantidad -> 4+6+8+8+6+4+4 = 40
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario, personalizacion, texto_bordado, logo_club)
SELECT p.id_pedido, 1, t.talla, t.cantidad, 69.99, 'Colores del club: rojo y blanco', 'HALCONES', true
FROM pedido p, (VALUES (38, 4), (39, 6), (40, 8), (41, 8), (42, 6), (43, 4), (44, 4)) AS t(talla, cantidad)
WHERE p.ref_odoo = 'CUS-0005';

COMMIT;

-- El total lo calcula el trigger, debería ser 40 * 69.99 = 2799.60
SELECT ref_odoo, estado, total FROM pedido WHERE ref_odoo = 'CUS-0005';

-- Ahora lo confirmo
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CONFIRMADO' WHERE ref_odoo = 'CUS-0005';
COMMIT;

-- El stock tiene que haber bajado justo lo que pedí en cada talla
SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

-- Y en el log tiene que aparecer todo lo que he hecho
SELECT id_log, fecha, tabla, operacion, registro_id, accion, id_usuario
FROM log_eventos
ORDER BY id_log;


-- 4. Prueba B: confirmar un pedido cuando no hay stock

-- Pedido normal en borrador, 5 pares de la variante 19 en la 42
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
INSERT INTO pedido (ref_odoo, tipo, id_cliente, id_usuario)
VALUES ('PED-0007', 'ESTANDAR', 4, 2);
INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0007'), 19, 42, 5, 109.99);
COMMIT;

-- Intento confirmarlo: tiene que saltar el error de stock insuficiente
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CONFIRMADO' WHERE ref_odoo = 'PED-0007';
ROLLBACK;

-- Tiene que seguir en BORRADOR, sin fecha de confirmación, y el stock igual
SELECT ref_odoo, estado, fecha_confirmacion FROM pedido WHERE ref_odoo = 'PED-0007';
SELECT talla, cantidad FROM stock WHERE id_variante = 19 AND talla = 42;


-- 5. Prueba C: cancelar el pedido que confirmé en la prueba A

BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET estado = 'CANCELADO' WHERE ref_odoo = 'CUS-0005';
COMMIT;

-- Ahora tiene que tener las dos fechas puestas
SELECT ref_odoo, estado, fecha_confirmacion, fecha_cancelacion FROM pedido WHERE ref_odoo = 'CUS-0005';

-- El stock tiene que volver a estar como al principio de la prueba A
SELECT talla, cantidad FROM stock WHERE id_variante = 1 ORDER BY talla;

-- Los cambios de estado en el log
SELECT id_log, fecha, accion, id_usuario
FROM log_eventos
WHERE accion LIKE 'CAMBIO ESTADO%'
ORDER BY id_log;


-- 6. Prueba D: hacer un cambio y deshacerlo con ROLLBACK

-- Cuántas filas hay en el log ahora mismo
SELECT COUNT(*) AS entradas_log FROM log_eventos;

BEGIN;
SELECT set_config('app.id_usuario', '1', true);
UPDATE pedido SET observaciones = 'Cambio que se va a deshacer' WHERE ref_odoo = 'PED-0006';
-- dentro de la transacción sí se ve una entrada más
SELECT COUNT(*) AS entradas_dentro FROM log_eventos;
ROLLBACK;

-- Después del ROLLBACK tiene que volver al número de antes
-- y las observaciones no tienen que haber cambiado
SELECT COUNT(*) AS entradas_log FROM log_eventos;
SELECT ref_odoo, observaciones FROM pedido WHERE ref_odoo = 'PED-0006';


-- 7. Lo que no se ha confirmado no lo ven las demás conexiones
-- Para esta hacen falta dos pestañas de consulta abiertas a la vez.

-- En la pestaña 1 hago el cambio pero sin COMMIT todavía
BEGIN;
SELECT set_config('app.id_usuario', '2', true);
UPDATE pedido SET observaciones = 'Revisado por el comercial' WHERE ref_odoo = 'PED-0006';

-- En la pestaña 2 miro el log, todavía no tiene que salir la entrada nueva:
--   SELECT id_log, accion, registro_id FROM log_eventos ORDER BY id_log DESC LIMIT 1;

-- Vuelvo a la pestaña 1 y hago el COMMIT
COMMIT;

-- En la pestaña 2 lo vuelvo a lanzar y ahora sí tiene que aparecer:
--   SELECT id_log, accion, registro_id FROM log_eventos ORDER BY id_log DESC LIMIT 1;


-- 8. Un par de cosas más que tienen que bloquear los triggers

-- Tocar las líneas de un pedido que ya está confirmado (error)
UPDATE linea_pedido SET cantidad = 1
WHERE id_pedido = (SELECT id_pedido FROM pedido WHERE ref_odoo = 'CUS-0004');

-- Pasar a borrador un pedido cancelado, no tiene sentido (error)
UPDATE pedido SET estado = 'BORRADOR' WHERE ref_odoo = 'CUS-0005';
