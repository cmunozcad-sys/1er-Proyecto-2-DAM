-- PARTE 1. BÚSQUEDAS
-- Consulta 1. Pedidos de un cliente
SELECT p.ref_odoo, p.tipo, p.estado, p.fecha_pedido, p.total
FROM pedido p
JOIN cliente c ON c.id_cliente = p.id_cliente
WHERE c.nombre = 'Club Atletismo Halcones'
ORDER BY p.fecha_pedido;

-- Consulta 2. Pedidos según su estado
SELECT p.ref_odoo, c.nombre AS cliente, p.tipo, p.fecha_confirmacion, p.total
FROM pedido p
JOIN cliente c ON c.id_cliente = p.id_cliente
WHERE p.estado = 'CONFIRMADO'
ORDER BY p.fecha_confirmacion;

-- Consulta 3. Pedidos de un periodo
SELECT p.ref_odoo, c.nombre AS cliente, p.estado, p.fecha_pedido, p.total
FROM pedido p
JOIN cliente c ON c.id_cliente = p.id_cliente
WHERE p.fecha_pedido >= '2026-10-01'
  AND p.fecha_pedido <  '2026-11-01'
ORDER BY p.fecha_pedido;

-- Consulta 4. Pedidos que incluyen un modelo
SELECT DISTINCT p.ref_odoo, c.nombre AS cliente, p.estado
FROM pedido p
JOIN cliente c       ON c.id_cliente  = p.id_cliente
JOIN linea_pedido l  ON l.id_pedido   = p.id_pedido
JOIN variante v      ON v.id_variante = l.id_variante
JOIN modelo m        ON m.id_modelo   = v.id_modelo
WHERE m.nombre = 'Cometa'
ORDER BY p.ref_odoo;


-- PARTE 2. CONSULTAS CON VARIAS TABLAS
-- Consulta 5. Detalle completo de un pedido
SELECT p.ref_odoo, c.nombre AS cliente, m.nombre AS modelo, v.color,
       l.talla, l.cantidad, l.precio_unitario,
       l.cantidad * l.precio_unitario AS subtotal
FROM pedido p
JOIN cliente c       ON c.id_cliente  = p.id_cliente
JOIN linea_pedido l  ON l.id_pedido   = p.id_pedido
JOIN variante v      ON v.id_variante = l.id_variante
JOIN modelo m        ON m.id_modelo   = v.id_modelo
WHERE p.ref_odoo = 'CUS-0001'
ORDER BY l.talla;

-- Consulta 6. Ficha de fabricación de los pedidos Custom
SELECT p.ref_odoo AS referencia, c.nombre AS cliente, m.nombre AS modelo,
       v.color, l.personalizacion, l.texto_bordado, l.logo_club,
       l.talla, l.cantidad
FROM pedido p
JOIN cliente c       ON c.id_cliente  = p.id_cliente
JOIN linea_pedido l  ON l.id_pedido   = p.id_pedido
JOIN variante v      ON v.id_variante = l.id_variante
JOIN modelo m        ON m.id_modelo   = v.id_modelo
WHERE p.tipo = 'CUSTOM'
  AND p.estado = 'CONFIRMADO'
ORDER BY p.ref_odoo, l.talla;


-- PARTE 3. AGRUPACIONES
-- Consulta 7. Unidades pedidas por talla
SELECT l.talla, SUM(l.cantidad) AS pares
FROM linea_pedido l
JOIN pedido p ON p.id_pedido = l.id_pedido
WHERE p.estado <> 'CANCELADO'
GROUP BY l.talla
ORDER BY l.talla;

-- Consulta 8. Pares y ventas por modelo
SELECT m.nombre AS modelo,
       SUM(l.cantidad) AS pares,
       SUM(l.cantidad * l.precio_unitario) AS ventas
FROM linea_pedido l
JOIN pedido p   ON p.id_pedido   = l.id_pedido
JOIN variante v ON v.id_variante = l.id_variante
JOIN modelo m   ON m.id_modelo   = v.id_modelo
WHERE p.estado <> 'CANCELADO'
GROUP BY m.nombre
ORDER BY pares DESC;

-- Consulta 9. Pedidos e importe por cliente
SELECT c.nombre AS cliente,
       COUNT(p.id_pedido) AS num_pedidos,
       SUM(p.total) AS importe_total
FROM cliente c
JOIN pedido p ON p.id_cliente = c.id_cliente
WHERE p.estado <> 'CANCELADO'
GROUP BY c.nombre
ORDER BY importe_total DESC;


-- PARTE 4. HAVING Y SUBCONSULTAS
-- Consulta 10. Clientes con más de un pedido
SELECT c.nombre AS cliente, COUNT(p.id_pedido) AS num_pedidos
FROM cliente c
JOIN pedido p ON p.id_cliente = c.id_cliente
WHERE p.estado <> 'CANCELADO'
GROUP BY c.nombre
HAVING COUNT(p.id_pedido) > 1
ORDER BY num_pedidos DESC;

-- Consulta 11. Pedidos con un importe superior a la media
SELECT p.ref_odoo, c.nombre AS cliente, p.total
FROM pedido p
JOIN cliente c ON c.id_cliente = p.id_cliente
WHERE p.estado <> 'CANCELADO'
  AND p.total > (SELECT AVG(total) FROM pedido WHERE estado <> 'CANCELADO')
ORDER BY p.total DESC;

-- Consulta 12. Stock bajo
SELECT m.nombre AS modelo, s.talla, s.cantidad, s.stock_minimo
FROM stock s
JOIN variante v ON v.id_variante = s.id_variante
JOIN modelo m   ON m.id_modelo   = v.id_modelo
WHERE s.cantidad < s.stock_minimo
ORDER BY s.cantidad, m.nombre, s.talla;


-- PARTE 5. INDICADORES
-- Consulta 13. Panel de indicadores (ventas = solo pedidos confirmados)
SELECT
    (SELECT COUNT(*) FROM pedido) AS total_pedidos,
    (SELECT COALESCE(SUM(l.cantidad), 0)
     FROM linea_pedido l
     JOIN pedido p ON p.id_pedido = l.id_pedido
     WHERE p.estado <> 'CANCELADO') AS pares_solicitados,
    (SELECT COALESCE(SUM(total), 0)
     FROM pedido
     WHERE estado = 'CONFIRMADO') AS importe_ventas;

-- Consulta 14. Pedidos por estado
SELECT estado, COUNT(*) AS num_pedidos, SUM(total) AS importe
FROM pedido
GROUP BY estado
ORDER BY estado;

-- Consulta 15. Stock por debajo de un umbral (en la API el 10 será un parámetro)
SELECT m.nombre AS modelo, s.talla, s.cantidad
FROM stock s
JOIN variante v ON v.id_variante = s.id_variante
JOIN modelo m   ON m.id_modelo   = v.id_modelo
WHERE s.cantidad < 10
ORDER BY s.cantidad, m.nombre, s.talla;


-- PARTE 6. TRANSACCIONES
-- Ejemplo A. COMMIT: los cambios se guardan (ejecutar una sola vez)
BEGIN;

INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0003'), 5, 43, 1, 74.99);

COMMIT;

SELECT p.ref_odoo, SUM(l.cantidad) AS pares, p.total
FROM pedido p JOIN linea_pedido l ON l.id_pedido = p.id_pedido
WHERE p.ref_odoo = 'PED-0003'
GROUP BY p.ref_odoo, p.total;

-- Ejemplo B. ROLLBACK: los cambios se deshacen
BEGIN;

UPDATE pedido
SET estado = 'CANCELADO', fecha_cancelacion = now()
WHERE ref_odoo = 'CUS-0001';

SELECT ref_odoo, estado FROM pedido WHERE ref_odoo = 'CUS-0001';

ROLLBACK;

SELECT ref_odoo, estado FROM pedido WHERE ref_odoo = 'CUS-0001';

-- Ejemplo C. Un error dentro de la transacción
BEGIN;

UPDATE pedido SET observaciones = 'Revisado' WHERE ref_odoo = 'PED-0006';

INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
VALUES ((SELECT id_pedido FROM pedido WHERE ref_odoo = 'PED-0006'), 18, 44, -5, 84.99);

ROLLBACK;

SELECT ref_odoo, observaciones FROM pedido WHERE ref_odoo = 'PED-0006';
