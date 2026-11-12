\cd ProgramacionDeServiciosyProcesos/datos

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;

\copy (SELECT p.ref_odoo AS referencia, c.nombre AS cliente, m.nombre AS modelo, v.color, l.personalizacion, l.texto_bordado, l.logo_club, l.talla, l.cantidad FROM pedido p JOIN cliente c ON c.id_cliente = p.id_cliente JOIN linea_pedido l ON l.id_pedido = p.id_pedido JOIN variante v ON v.id_variante = l.id_variante JOIN modelo m ON m.id_modelo = v.id_modelo WHERE p.tipo = 'CUSTOM' AND p.estado = 'CONFIRMADO' ORDER BY p.ref_odoo, l.talla) TO 'ficha_fabricacion.csv' WITH (FORMAT csv, HEADER, ENCODING 'UTF8')

COMMIT;
