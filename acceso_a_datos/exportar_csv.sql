\cd Python/entrada

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;

\copy (SELECT id_cliente, ref_odoo, tipo, ciudad, activo, fecha_alta FROM cliente ORDER BY id_cliente) TO 'clientes.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

\copy (SELECT id_modelo, ref_odoo, nombre, categoria, precio_base, personalizable, activo FROM modelo ORDER BY id_modelo) TO 'modelos.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

\copy (SELECT id_pedido, ref_odoo, tipo, estado, fecha_pedido, fecha_entrega_prevista, fecha_confirmacion, fecha_cancelacion, total, id_cliente FROM pedido ORDER BY id_pedido) TO 'pedidos.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

\copy (SELECT l.id_linea, l.id_pedido, l.id_variante, v.id_modelo, v.color, l.talla, l.cantidad, l.precio_unitario, l.logo_club, (l.personalizacion IS NOT NULL OR l.texto_bordado IS NOT NULL) AS personalizada FROM linea_pedido l JOIN variante v ON v.id_variante = l.id_variante ORDER BY l.id_linea) TO 'lineas_pedido.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

\copy (SELECT s.id_variante, v.id_modelo, v.color, s.talla, s.cantidad, s.stock_minimo, s.ultima_actualizacion FROM stock s JOIN variante v ON v.id_variante = s.id_variante ORDER BY s.id_variante, s.talla) TO 'stock.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

\copy (SELECT 'pedidos_totales' AS indicador, (SELECT COUNT(*) FROM pedido)::numeric AS valor_sql UNION ALL SELECT 'lineas_totales', (SELECT COUNT(*) FROM linea_pedido) UNION ALL SELECT 'pedidos_confirmados', (SELECT COUNT(*) FROM pedido WHERE estado = 'CONFIRMADO') UNION ALL SELECT 'pares_vendidos', (SELECT COALESCE(SUM(l.cantidad), 0) FROM linea_pedido l JOIN pedido p ON p.id_pedido = l.id_pedido WHERE p.estado = 'CONFIRMADO') UNION ALL SELECT 'ingresos_validos', (SELECT COALESCE(SUM(l.cantidad * l.precio_unitario), 0) FROM linea_pedido l JOIN pedido p ON p.id_pedido = l.id_pedido WHERE p.estado = 'CONFIRMADO') UNION ALL SELECT 'ingresos_2026-10', (SELECT COALESCE(SUM(l.cantidad * l.precio_unitario), 0) FROM linea_pedido l JOIN pedido p ON p.id_pedido = l.id_pedido WHERE p.estado = 'CONFIRMADO' AND p.fecha_pedido >= '2026-10-01' AND p.fecha_pedido < '2026-11-01') UNION ALL SELECT 'pares_talla_42', (SELECT COALESCE(SUM(l.cantidad), 0) FROM linea_pedido l JOIN pedido p ON p.id_pedido = l.id_pedido WHERE p.estado = 'CONFIRMADO' AND l.talla = 42)) TO 'referencia_sql.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

COMMIT;