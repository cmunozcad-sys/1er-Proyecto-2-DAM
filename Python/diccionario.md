# Diccionario de datos

## Formato de los CSV

| Propiedad | Valor |
|---|---|
| Origen | Exportación de PostgreSQL (base `sneaker_factory`) |
| Codificación | UTF-8 |
| Delimitador | `,` |
| Separador decimal | `.` |
| Cabecera | Primera fila |
| Fechas | `AAAA-MM-DD` |
| Fecha y hora | `AAAA-MM-DD HH:MM:SS` (puede incluir microsegundos) |
| Nulos | Texto `NULL` o celda vacía |
| Booleanos | `True` / `False` |
| Moneda | Euros (EUR), precios con IVA según la tienda |

Los identificadores (`id_*`) se leen como texto. No se usan en cálculos numéricos.

## clientes.csv

| Columna | Significado | Tipo | Unidad | Valores permitidos | Nulos |
|---|---|---|---|---|---|
| id_cliente | Identificador del cliente | texto | - | Único | No admitido: registro rechazado |
| ref_odoo | Referencia del cliente en Odoo | texto | - | `CLI-NNN` | Advertencia |
| tipo | Tipo de cliente | texto | - | CLUB, EQUIPO, EMPRESA, PARTICULAR | Incidencia recuperable |
| ciudad | Ciudad del cliente | texto | - | Libre | Advertencia |
| activo | Cliente activo | booleano | - | True, False | Advertencia |
| fecha_alta | Fecha de alta | fecha | - | No posterior a la fecha de corte | Advertencia |

## modelos.csv

| Columna | Significado | Tipo | Unidad | Valores permitidos | Nulos |
|---|---|---|---|---|---|
| id_modelo | Identificador del modelo | texto | - | Único | No admitido: registro rechazado |
| ref_odoo | Referencia del modelo en Odoo | texto | - | `SF-NNN` | Advertencia |
| nombre | Nombre comercial | texto | - | Libre | Advertencia |
| categoria | Categoría del modelo | texto | - | correr, botas, futbol, baloncesto | Incidencia recuperable |
| precio_base | Precio de venta base | decimal | EUR | Mayor que 0 | No admitido: registro rechazado |
| personalizable | Admite pedido Custom | booleano | - | True, False | Advertencia |
| activo | Modelo a la venta | booleano | - | True, False | Advertencia |

## pedidos.csv

| Columna | Significado | Tipo | Unidad | Valores permitidos | Nulos |
|---|---|---|---|---|---|
| id_pedido | Identificador del pedido | texto | - | Único | No admitido: registro rechazado |
| ref_odoo | Referencia del pedido | texto | - | `PED-NNNN` (estándar), `CUS-NNNN` (Custom) | Advertencia |
| tipo | Tipo de pedido | texto | - | ESTANDAR, CUSTOM | No admitido: registro rechazado |
| estado | Estado del pedido | texto | - | BORRADOR, CONFIRMADO, CANCELADO | No admitido: registro rechazado |
| fecha_pedido | Fecha de creación | fecha y hora | - | Válida y no futura | No admitido: registro rechazado |
| fecha_entrega_prevista | Entrega prevista | fecha | - | Igual o posterior a fecha_pedido | Permitido (borradores) |
| fecha_confirmacion | Momento de confirmación | fecha y hora | - | Igual o posterior a fecha_pedido | Permitido si estado = BORRADOR |
| fecha_cancelacion | Momento de cancelación | fecha y hora | - | Solo si estado = CANCELADO | Permitido si no está cancelado |
| total | Importe total guardado en la base | decimal | EUR | Mayor o igual que 0 | Se recalcula desde las líneas |
| id_cliente | Cliente que hace el pedido | texto | - | Debe existir en clientes.csv | No admitido: registro rechazado |

## lineas_pedido.csv

| Columna | Significado | Tipo | Unidad | Valores permitidos | Nulos |
|---|---|---|---|---|---|
| id_linea | Identificador de la línea | texto | - | Único | No admitido: registro rechazado |
| id_pedido | Pedido al que pertenece | texto | - | Debe existir en pedidos.csv | No admitido: registro rechazado |
| id_variante | Variante (modelo y color) | texto | - | Debe existir en stock.csv | No admitido: registro rechazado |
| id_modelo | Modelo de la zapatilla | texto | - | Debe existir en modelos.csv | No admitido: registro rechazado |
| color | Color de la variante | texto | - | Libre | Advertencia |
| talla | Talla | decimal | EU | Entre 30 y 48 | No admitido: registro rechazado |
| cantidad | Pares de la línea | entero | pares | Mayor que 0 | No admitido: registro rechazado |
| precio_unitario | Precio por par | decimal | EUR | Mayor o igual que 0 | No admitido: registro rechazado |
| logo_club | Lleva logo de club | booleano | - | True, False | Advertencia |
| personalizada | Línea personalizada | booleano | - | True, False | Advertencia |

## stock.csv

| Columna | Significado | Tipo | Unidad | Valores permitidos | Nulos |
|---|---|---|---|---|---|
| id_variante | Variante (modelo y color) | texto | - | Clave junto con talla | No admitido: registro rechazado |
| id_modelo | Modelo de la variante | texto | - | Debe existir en modelos.csv | No admitido: registro rechazado |
| color | Color de la variante | texto | - | Libre | Advertencia |
| talla | Talla | decimal | EU | Entre 30 y 48 | No admitido: registro rechazado |
| cantidad | Pares disponibles en la fecha de corte | entero | pares | Mayor o igual que 0 | No admitido: registro rechazado |
| stock_minimo | Umbral de alerta | entero | pares | Mayor o igual que 0 | Se usa 5 por defecto |
| ultima_actualizacion | Fecha de corte del stock | fecha y hora | - | Válida | Advertencia |

El stock es una foto del momento de la exportación, no un histórico de movimientos.

## Relaciones

| Origen | Destino | Cardinalidad |
|---|---|---|
| pedidos.id_cliente | clientes.id_cliente | muchos a uno |
| lineas.id_pedido | pedidos.id_pedido | muchos a uno |
| lineas.id_modelo | modelos.id_modelo | muchos a uno |
| lineas.(id_variante, talla) | stock.(id_variante, talla) | muchos a uno |
| stock.id_modelo | modelos.id_modelo | muchos a uno |

## Reglas de negocio

- Venta válida: pedido con estado CONFIRMADO.
- BORRADOR y CANCELADO cuentan en la actividad, no en las ventas.
- Importe de línea = cantidad × precio_unitario.
- Un pedido con varias líneas cuenta como un solo pedido.
- No existe coste unitario, así que no se calcula beneficio ni margen.