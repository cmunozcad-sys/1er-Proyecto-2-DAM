# Sneaker Factory / DACA

Proyecto Intermodular de 2º DAM. **DACA** es una marca de zapatillas personalizadas para clubes y equipos. El proyecto reúne el trabajo de varias asignaturas sobre el mismo negocio:

| Parte | Carpeta | Qué hace |
|---|---|---|
| [Acceso a Datos](#acceso-a-datos) | `acceso_a_datos/` | Base de datos PostgreSQL `sneaker_factory`: tablas, datos, triggers y exportación a CSV. |
| [Desarrollo de Interfaces](#desarrollo-de-interfaces) | `desarrollo_de_interfaces/` y `api/` | Tienda web con panel de administración, servida por una API Node.js que se arranca con Docker. |
| [Integración con Odoo](#integración-con-odoo) | `api/` | Envía a Odoo, como presupuestos, los pedidos de la web que se confirman. |
| [Programación de Servicios y Procesos](#programación-de-servicios-y-procesos) | `ProgramacionDeServiciosyProcesos/` | Programa Java que procesa fichas de fabricación con varios procesos. |
| [Python · Análisis de datos](#python--análisis-de-datos) | `Python/` | Pipeline de datos, analítica, predicción, gráficos, dashboard y tests. |

## Antes de empezar

1. Clona el repositorio:
   ```bash
   git clone https://github.com/cmunozcad-sys/1er-Proyecto-2-DAM.git
   cd 1er-Proyecto-2-DAM
   ```
2. Monta las partes en este orden, porque unas dependen de otras:
   1. **Acceso a Datos**: la base de datos es la base de todo lo demás.
   2. **Desarrollo de Interfaces**: la web y la API leen y escriben en esa base de datos.
   3. **Integración con Odoo**: funciona dentro de la API.
   4. **Python**: analiza los datos que se exportan de la base de datos.

   **Programación de Servicios y Procesos** es independiente y se puede montar en cualquier momento.

Las versiones que se indican en cada apartado son las que se han usado en el proyecto.

## Caso de uso común

Los enunciados usan como ejemplo el pedido "SO024" del modelo "Runner X" para "Club Halcones". En este proyecto, el caso equivalente es el pedido **`CUS-0001`** de `carga_de_datos.sql`:

| Dato | Enunciado | Este proyecto |
|---|---|---|
| Pedido | SO024 | `CUS-0001`, tipo `CUSTOM`, estado `CONFIRMADO` |
| Cliente | Club Halcones | Club Atletismo Halcones (`CLI-001`) |
| Modelo | Runner X | Cometa (`SF-001`), color negro y blanco |
| Cantidad | — | 40 pares en 9 tallas, del 38 al 46 |

El mismo pedido aparece en todas las partes:
- en la base de datos;
- en la ficha de fabricación que procesa el programa Java;
- en los indicadores de Python: con `--modelo 1`, 40 pares y 2.799,60 €.

---

## Acceso a Datos

### Descripción

Base de datos PostgreSQL `sneaker_factory`:
- **Usuarios, roles y permisos**: Administrador, Comercial y Almacén.
- **Catálogo**: modelos, variantes de color y stock por talla.
- **Clientes y pedidos**, con sus líneas, personalización y bordado.
- **Registro de auditoría**.

Los triggers automatizan tres cosas:
- recalculan el total del pedido al cambiar sus líneas;
- descuentan o devuelven stock al confirmar o cancelar un pedido;
- registran cada cambio en `log_eventos`.

### Archivos

| Archivo | Contenido |
|---|---|
| `creacion_tablas_daca.sql` | Borra y vuelve a crear todas las tablas y los índices. Activa la extensión `pgcrypto`. |
| `carga_de_datos.sql` | Datos de ejemplo: roles, permisos, usuarios, modelos, variantes, stock, clientes, pedidos y líneas. |
| `triggers.sql` | Triggers de importes, de stock y de auditoría. |
| `integracion_odoo.sql` | Columnas de `pedido` para la integración con Odoo. |
| `consultas.sql` | Consultas de ejemplo: búsquedas, agregados y transacciones. La consulta 6 genera la ficha de fabricación que procesa el programa Java. |
| `pruebas.sql` | Pruebas de inserción, modificación, borrado y de los triggers. |
| `exportar_csv.sql` | Exporta las tablas a `Python/entrada/` para el análisis en Python. |
| `exportar_ficha.sql` | Exporta la ficha de fabricación (la consulta 6) a `ProgramacionDeServiciosyProcesos/datos/ficha_fabricacion.csv` para el programa Java. |
| `daca_model_er.dbm` | Modelo entidad-relación, hecho con pgModeler. |

### Aplicaciones y versiones

| Aplicación | Versión | Para qué |
|---|---|---|
| PostgreSQL | 18 (18.6) | Servidor de base de datos. Incluye `psql`. |
| pgAdmin 4 | La que se instala con PostgreSQL 18 | Ejecutar los scripts con una interfaz gráfica (opcional). |
| pgModeler | 0.9.4 | Solo para abrir el modelo `daca_model_er.dbm` (opcional). |

### Cómo montarlo

1. Instala **PostgreSQL 18**. Apunta la contraseña que pongas al usuario `postgres`: la necesitarás en el `.env`.
2. Crea la base de datos:
   ```sql
   CREATE DATABASE sneaker_factory;
   ```
3. En pgAdmin, selecciona la base de datos `sneaker_factory` y abre el **Query Tool**. Ejecuta los scripts **uno a uno y en este orden**: abre cada archivo, ejecútalo y comprueba que termina sin errores antes de pasar al siguiente.

   | Orden | Script |
   |---|---|
   | 1 | `creacion_tablas_daca.sql` |
   | 2 | `carga_de_datos.sql` |
   | 3 | `triggers.sql` |
   | 4 | `integracion_odoo.sql` |

**Por qué este orden:**
- Los triggers van **después** de la carga. El trigger de importes no deja añadir líneas a un pedido que no esté en `BORRADOR`, y la carga inserta pedidos ya confirmados con sus líneas.
- `integracion_odoo.sql` marca como `SINCRONIZADO` todos los pedidos que existen al ejecutarlo, que son los de la carga de datos. Así no se envían a Odoo todos de golpe ni se duplican; solo se envían los pedidos nuevos que se confirmen después. Este script solo se puede ejecutar una vez: si las columnas ya existen, falla. Para volver a empezar, ejecuta de nuevo los cuatro scripts desde el primero.

### Cómo ejecutarlo

- **Consultas y pruebas:** abre `consultas.sql` o `pruebas.sql` en el Query Tool de pgAdmin y ejecútalos. Algunas pruebas de transacciones están pensadas para fallar a propósito, para comprobar los triggers.
- **Exportar a CSV para Python:** se explica en [Python · Análisis de datos](#exportar-los-csv-de-la-base-de-datos).
- **Exportar la ficha de fabricación para Java:** se explica en [Programación de Servicios y Procesos](#de-dónde-sale-la-ficha-de-fabricación).

### Usuarios de prueba y permisos

`carga_de_datos.sql` crea tres usuarios de prueba, uno por rol. Sus contraseñas están en ese mismo script; no se repiten aquí.

| Usuario | Rol (tabla `rol`) |
|---|---|
| `admin` | Administrador |
| `comercial` | Comercial |
| `almacen` | Almacen |

Permisos de cada rol, sacados de las tablas `permiso` y `rol_permiso`:

| Permiso | Para qué | Administrador | Comercial | Almacen |
|---|---|:---:|:---:|:---:|
| `PEDIDO_VER` | Consultar pedidos y sus líneas | ✔ | ✔ | ✔ |
| `PEDIDO_CREAR` | Crear pedidos y añadir líneas | ✔ | ✔ | |
| `PEDIDO_EDITAR` | Modificar pedidos en borrador | ✔ | ✔ | |
| `PEDIDO_CONFIRMAR` | Confirmar pedidos | ✔ | ✔ | |
| `PEDIDO_CANCELAR` | Cancelar pedidos | ✔ | ✔ | |
| `STOCK_VER` | Consultar existencias | ✔ | ✔ | ✔ |
| `INDICADORES_VER` | Ver el panel de indicadores | ✔ | ✔ | |
| `EXPORTAR_CSV` | Exportar consultas a CSV | ✔ | ✔ | ✔ |
| `AUDITORIA_VER` | Consultar la tabla `log_eventos` | ✔ | | |
| `USUARIOS_GESTIONAR` | Crear, modificar y desactivar usuarios | ✔ | | |
| `USUARIOS_EXPORTAR` | Exportar los usuarios a JSON | ✔ | | |
| `STOCK_REPONER` | Añadir pares a las existencias | ✔ | | |

La API de la web comprueba cinco de estos permisos:
- `PEDIDO_VER` para listar pedidos;
- `PEDIDO_CREAR` para hacer pedidos del carrito o personalizados;
- `PEDIDO_CONFIRMAR` y `PEDIDO_CANCELAR` para aprobar o cancelar pedidos;
- `STOCK_REPONER` para reponer stock.

---

## Desarrollo de Interfaces

### Descripción

Tienda web de DACA con:
- catálogo de modelos, página de producto y detalle;
- carrito para hacer pedidos;
- formulario de pedidos personalizados para clubes;
- inicio de sesión;
- **panel de administración**, para aprobar o cancelar pedidos y reponer stock.

La web la sirve una **API en Node.js (Express)** que se conecta a PostgreSQL, gestiona las sesiones y comprueba los permisos de cada usuario. La API se arranca con **Docker**, así que no hace falta instalar Node.js.

### Archivos

| Archivo | Contenido |
|---|---|
| `desarrollo_de_interfaces/index.html` | Página principal y catálogo. |
| `desarrollo_de_interfaces/producto.html`, `detalle.html` | Página de producto y detalle de modelos. |
| `desarrollo_de_interfaces/login.html` | Inicio de sesión. |
| `desarrollo_de_interfaces/admin.html` | Panel de administración. |
| `desarrollo_de_interfaces/styles.css` | Estilos. |
| `desarrollo_de_interfaces/javascript/` | `script.js` (catálogo y pedidos personalizados), `carrito.js`, `login.js` y `admin.js`. |
| `desarrollo_de_interfaces/json/productos.json` | Datos del catálogo. |
| `desarrollo_de_interfaces/img/` | Imágenes de los modelos y de la web. |
| `api/server.js` | API: sesiones, permisos, pedidos y stock. Sirve la web. |
| `api/db.js` | Conexión con PostgreSQL. |
| `api/Dockerfile`, `docker-compose.yml` | Imagen y arranque del contenedor de la API. |
| `api/package.json` | Dependencias: `express` ^5.3.0, `express-session` ^1.19.0 y `pg` ^8.23.1. |
| `.env.example` | Plantilla de las variables de entorno. |

### Aplicaciones y versiones

| Aplicación | Versión | Para qué |
|---|---|---|
| Docker Desktop | Docker 29.8 y Docker Compose v5.5 | Arrancar la API. |
| Node.js | 24, dentro de la imagen `node:24-alpine` | Lo instala Docker; no hace falta instalarlo aparte. |
| PostgreSQL | 18 | La base de datos de [Acceso a Datos](#acceso-a-datos), ya montada. |
| Navegador web | Cualquiera actual | Abrir la tienda. |

### Cómo montarlo

1. Ten montada la base de datos de [Acceso a Datos](#acceso-a-datos).
2. Instala **Docker Desktop** y ábrelo.
3. En la raíz del proyecto, copia la plantilla de variables de entorno:
   ```bash
   cp .env.example .env
   ```
4. Rellena el `.env` con tus datos. Cada persona tiene su propio `.env`. Contiene contraseñas y claves, así que **no se sube a Git**: está en `.gitignore`.

   | Variable | Valor de ejemplo | Para qué sirve |
   |---|---|---|
   | `DB_HOST` | `host.docker.internal` | Equipo donde está PostgreSQL. Con este valor, la API, que corre en Docker, se conecta al PostgreSQL de tu ordenador. |
   | `DB_PORT` | `5432` | Puerto de PostgreSQL. |
   | `DB_NAME` | `sneaker_factory` | Nombre de la base de datos. |
   | `DB_USER` | `postgres` | Usuario de PostgreSQL. |
   | `DB_PASSWORD` | `pon_aqui_tu_contrasena` | Contraseña de ese usuario. |
   | `SESSION_SECRET` | `pon_aqui_un_texto_largo_y_dificil` | Texto secreto con el que se firman las sesiones de la web. |
   | `ODOO_URL` | `http://IP_DE_LA_VM:8069` | Dirección de Odoo. Ver [Integración con Odoo](#integración-con-odoo). |
   | `ODOO_DB` | `daca` | Base de datos de Odoo. |
   | `ODOO_USER` | `admin@example.com` | Usuario con el que se inicia sesión en Odoo. |
   | `ODOO_API_KEY` | `pon_aqui_tu_clave_api` | Clave API de ese usuario en Odoo. |
   | `SINCRONIZACION_SEGUNDOS` | `30` | Cada cuántos segundos se buscan pedidos para enviar a Odoo. |

   Si todavía no tienes Odoo, la web funciona igual: los pedidos confirmados se quedan pendientes de enviar.

### Cómo ejecutarlo

1. En la raíz del proyecto:
   ```bash
   docker compose up --build
   ```
   `--build` solo hace falta la primera vez o cuando cambia algo de `api/`.
2. Abre <http://localhost:3000>.
3. Para hacer pedidos o entrar al panel de administración, inicia sesión con uno de los usuarios de prueba: `admin`, `comercial` o `almacen`. Sus contraseñas están en `carga_de_datos.sql`. Cada usuario puede hacer lo que permite su rol (ver [Usuarios de prueba y permisos](#usuarios-de-prueba-y-permisos)). Por ejemplo, `almacen` puede ver los pedidos, pero no crearlos, aprobarlos ni reponer stock.

La terminal se queda mostrando los logs mientras la API está encendida:
- Para pararla, pulsa `Ctrl + C`.
- Para arrancarla en segundo plano, usa `docker compose up -d`.
  - Ver los logs: `docker compose logs -f`.
  - Apagarla: `docker compose down`.

La API sirve la carpeta `desarrollo_de_interfaces/`, montada dentro del contenedor, así que los cambios en HTML, CSS o JavaScript se ven al recargar la página, sin reconstruir nada.

---

## Integración con Odoo

### Descripción

Cuando un pedido de la web pasa a `CONFIRMADO`, la API lo envía a Odoo como presupuesto. No lo duplica y lo reintenta si falla. Forma parte de la API, así que se arranca junto con ella.

### Archivos

| Archivo | Contenido |
|---|---|
| `api/sincronizador.js` | Busca los pedidos confirmados pendientes y los envía a Odoo. |
| `api/odoo.js` | Conexión con la API JSON-RPC de Odoo. |
| `api/probar_odoo.js` | Script para comprobar la conexión. |
| `acceso_a_datos/integracion_odoo.sql` | Columnas `estado_odoo`, `odoo_id`, `error_odoo` e `intentos_odoo` de la tabla `pedido`. |

### Aplicaciones y versiones

| Aplicación | Versión | Para qué |
|---|---|---|
| VirtualBox | 7.2 (7.2.2) | Máquina virtual donde corre Odoo. |
| Ubuntu | 24.04.5 LTS | Sistema de la máquina virtual. |
| Odoo | 18 Community | ERP que recibe los presupuestos. Base de datos `daca`. |

### Cómo montarlo

1. **Arranca la máquina virtual de Odoo** en VirtualBox, con el adaptador de red en **modo puente**.
2. **Mira la IP de la máquina virtual.** Con el modo puente, la IP cambia según la red a la que esté conectado el ordenador. Ejecuta en el Ubuntu de la VM:
   ```bash
   hostname -I
   ```
   Pon esa IP en `ODOO_URL` de tu `.env`, con el puerto 8069. Por ejemplo, `http://IP_DE_LA_VM:8069`.
3. **Crea tu clave API en Odoo:** avatar del usuario → **Mis preferencias** → **Seguridad de la cuenta** → **Nueva clave API**. Ponla en `ODOO_API_KEY` y el usuario en `ODOO_USER`. Cada persona usa la suya.
4. **Productos en Odoo.** Cada modelo tiene que existir en Odoo con el mismo código (`SF-001`, `SF-002`…) o el mismo nombre que en la base de datos, y con las tallas como variantes. Si no, el pedido se queda en `ERROR` con el mensaje `El producto … no existe en Odoo`.
5. Si la API ya estaba arrancada, reiníciala para que lea el `.env` nuevo.

### Cómo ejecutarlo

Con la API arrancada, comprueba la conexión:

```bash
docker compose exec api node probar_odoo.js
```

Si todo va bien, muestra `Conexión correcta con Odoo` y algunos clientes y productos leídos de Odoo.

**Flujo de un pedido:**

1. **Se hace un pedido en la web**, con la sesión iniciada de un usuario con permiso `PEDIDO_CREAR`. Se guarda en PostgreSQL en estado `BORRADOR`, con la referencia `WEB-<número>` si es un pedido del carrito o `CUS-<número>` si es personalizado.
2. **Un usuario con permiso `PEDIDO_CONFIRMAR` lo aprueba** desde el panel de administración. El pedido pasa a `CONFIRMADO` y el trigger de stock descuenta las existencias. Si no hay stock suficiente, la aprobación se rechaza.
3. **El sincronizador** se ejecuta cada `SINCRONIZACION_SEGUNDOS` (30 por defecto). Busca los pedidos `CONFIRMADO` cuyo `estado_odoo` es `PENDIENTE` o `ERROR` y que lleven menos de 5 intentos, y los envía a Odoo:
   - **Sin duplicados:** primero busca en Odoo un presupuesto con la misma referencia de cliente. Si ya existe, no crea otro.
   - **Cliente:** lo busca por su referencia y, si no lo encuentra, por su email. Si tampoco aparece, lo crea.
   - **Productos:** busca cada línea por el código o el nombre del modelo, junto con la talla.
   - **Personalización:** la añade a la descripción de la línea, junto con el texto bordado.
4. **El pedido aparece en Odoo, en Ventas → Presupuestos**, con su referencia (`WEB-...` o `CUS-...`) en **Referencia del cliente** y "Web DACA" como origen.

**Estado de la sincronización**, en la tabla `pedido`:

| Columna | Significado |
|---|---|
| `estado_odoo` | `PENDIENTE`: todavía no se ha enviado. `SINCRONIZADO`: el presupuesto ya existe en Odoo. `ERROR`: el último intento falló y se volverá a intentar. |
| `odoo_id` | Id del presupuesto en Odoo. |
| `error_odoo` | Mensaje del último error, recortado a 300 caracteres. |
| `intentos_odoo` | Número de intentos. A partir de 5, el pedido deja de reintentarse. |

Si Odoo está apagado o no responde, el pedido se queda `PENDIENTE` y no cuenta como intento. Se envía solo cuando Odoo vuelve a estar disponible.

Para ver el estado de los pedidos en PostgreSQL:

```sql
SELECT ref_odoo, estado, estado_odoo, odoo_id, error_odoo FROM pedido ORDER BY id_pedido DESC;
```

---

## Programación de Servicios y Procesos

### Descripción

Programa Java que procesa una ficha de fabricación con varios procesos. `Coordinador` lanza cada paso como un proceso Java aparte, le pasa los datos por la entrada estándar y lee su salida:

1. **`Validador`** comprueba la ficha.
2. **`Analizador`** genera el resumen del pedido.
3. **`GeneradorInformacionTaller`** genera las fichas para el taller.

Si un proceso falla o tarda más de 10 segundos, el `Coordinador` lo detiene y termina con un código de error.

### Archivos

| Archivo | Contenido |
|---|---|
| `src/Coordinador.java` | Lanza y controla los procesos hijos. |
| `src/Validador.java`, `src/Analizador.java`, `src/GeneradorInformacionTaller.java` | Los tres pasos del procesamiento. |
| `datos/ficha_fabricacion.csv` | Ficha de fabricación de los pedidos Custom confirmados (`CUS-0001` y `CUS-0004`). Se regenera con `acceso_a_datos/exportar_ficha.sql`. |
| `datos/pedido_erroneo.csv` | Ficha con errores, para probar la validación. |
| `salida/resumen_pedido.txt` | Resumen del pedido. Se genera al ejecutar. |
| `salida/fichas_taller.txt` | Fichas para el taller. Se genera al ejecutar. |
| `salida/procesamiento.log` | Registro de cada ejecución. |

### Aplicaciones y versiones

| Aplicación | Versión | Para qué |
|---|---|---|
| JDK (Java) | 17 (17.0.12) | Compilar y ejecutar el programa. |
| IntelliJ IDEA | Cualquiera compatible con Java 17 | Abrir el proyecto (opcional). |

### Cómo montarlo

1. Instala el **JDK 17** y comprueba que funciona:
   ```bash
   java -version
   javac -version
   ```
2. Si usas IntelliJ, abre la carpeta `ProgramacionDeServiciosyProcesos/` como proyecto. Ya está configurado como proyecto de IntelliJ con Java 17.

### De dónde sale la ficha de fabricación

`datos/ficha_fabricacion.csv` es el resultado de la **consulta 6** de `acceso_a_datos/consultas.sql` ("Ficha de fabricación de los pedidos Custom"). La consulta saca una fila por cada línea de los pedidos `CUSTOM` en estado `CONFIRMADO`, con estas columnas:

```
referencia, cliente, modelo, color, personalizacion, texto_bordado, logo_club, talla, cantidad
```

Se exporta con **`acceso_a_datos/exportar_ficha.sql`**. El script ejecuta esa misma consulta con un `\copy` y escribe `ficha_fabricacion.csv` con cabecera y en UTF-8, dentro de una transacción de solo lectura. Funciona igual que `exportar_csv.sql`.

Desde la terminal, en la raíz del proyecto:

```bash
psql -U postgres -d sneaker_factory -f acceso_a_datos/exportar_ficha.sql
```

Desde la **PSQL Tool de pgAdmin**:
1. Cambia la primera línea del script, `\cd ProgramacionDeServiciosyProcesos/datos`, por la ruta completa de esa carpeta en tu ordenador.
2. Ejecútalo con `\i` y su ruta completa. Es lo mismo que en [Exportar los CSV de la base de datos](#exportar-los-csv-de-la-base-de-datos).

El fichero que genera `\copy` no es idéntico al que hay ahora en el repositorio, pero el programa Java lo acepta igual:

| Diferencia | Por qué no afecta |
|---|---|
| `logo_club` sale como `t`/`f` en vez de `True`/`False`. | Ni el `Validador` ni el `Analizador` leen esa columna; solo comprueban que haya 9. |
| Las comillas solo aparecen cuando hacen falta, por ejemplo si un texto tiene una coma. | Los dos programas quitan las comillas y respetan las comas que van dentro de un campo entre comillas. |
| Un campo vacío (`NULL`) sale como nada entre dos comas. | Solo son obligatorios la referencia, el cliente y el modelo, y nunca son nulos. |

Si un texto lleva comillas dobles dentro, por ejemplo un bordado `"VAMOS"`, las comillas se pierden en las fichas del taller y queda `VAMOS`.

### Cómo ejecutarlo

Las rutas `datos/` y `salida/` son relativas, así que hay que ejecutarlo **desde la carpeta `ProgramacionDeServiciosyProcesos/`**.

Desde la terminal:

```bash
cd ProgramacionDeServiciosyProcesos
javac -d out src/*.java
java -cp out Coordinador
```

| Comando | Qué hace |
|---|---|
| `java -cp out Coordinador` | Procesa `datos/ficha_fabricacion.csv` y genera los archivos de `salida/`. |
| `java -cp out Coordinador datos/pedido_erroneo.csv` | Procesa la ficha con errores: el `Validador` muestra cada error y el proceso se detiene. |
| `java -cp out Coordinador --bloquear` | El `Validador` se queda bloqueado y el `Coordinador` lo detiene a los 10 segundos. |

Desde IntelliJ: ejecuta la clase `Coordinador`. Para las otras dos opciones, añade el argumento en la configuración de ejecución.

**Códigos de salida del `Coordinador`**, sacados de `Coordinador.java`:

| Código | Cuándo |
|---|---|
| `0` | Todo correcto: se han generado `salida/resumen_pedido.txt` y `salida/fichas_taller.txt`. |
| `10` | El `Validador` rechaza la ficha: cabecera incorrecta, fichero vacío, o líneas con columnas, talla o cantidad no válidas. |
| `20` | El `Validador` no termina en 10 segundos y se detiene (`--bloquear`). |
| `30` | No existe el fichero de entrada, o falla el `Analizador` o el `GeneradorInformacionTaller`. |

Cada paso, con su PID, su código y su duración, queda registrado en `salida/procesamiento.log`.

---

## Python · Análisis de datos

### Descripción

Análisis de los datos de ventas:
- **Pipeline**: carga los CSV exportados de la base de datos, los valida (claves, tipos, fechas, rangos y relaciones entre tablas) y registra cada incidencia con su gravedad.
- **Analítica**: KPIs de ventas, clasificación ABC de modelos, matriz modelo × talla, matriz modelo × mes, productos estacionales, cambios en la mezcla de tallas, Custom frente a estándar, segmentación RFM de clientes, cohortes, cobertura de stock, anomalías, estadísticos y contraste de hipótesis.
- **Modelos**: clustering de clientes (K-means) y predicción de demanda (RandomForest comparado con un baseline).
- **Conciliación**: compara los indicadores calculados en Python con los calculados en SQL.
- **Salidas**: gráficos, un **dashboard interactivo** con Streamlit y tests automáticos.

### Archivos

| Archivo | Contenido |
|---|---|
| `main.py` | Análisis por consola: carga, valida, aplica los filtros, calcula todo o solo una fase (`--fase`) y guarda los resultados. |
| `pipeline.py` | Carga, validación e integración de los CSV. |
| `analiticas.py` | Cálculos: filtros, KPIs, ABC, matrices modelo × talla y modelo × mes, estacionalidad, mezcla de tallas, RFM, cohortes, stock, anomalías, hipótesis, clustering y conciliación con SQL. |
| `prediccion.py` | Predicción de demanda por modelo y mes. |
| `visualizaciones.py` | Gráficos PNG. |
| `generador_datos.py` | Genera el histórico sintético y la copia con errores. |
| `app_dashboard.py` | Dashboard con Streamlit: origen de datos, filtros, vistas y refresco automático. |
| `dashboard/` | Piezas del dashboard: `vistas.py` (las seis vistas), `interfaz.py` (componentes visuales), `dashboard.css` y `logo.png`. |
| `refresco.py` | Ciclo de refresco del dashboard: comprueba los CSV, los valida, recalcula y decide el estado. |
| `.streamlit/config.toml` | Tema visual del dashboard. |
| `config.py` | Rutas, reglas de negocio y parámetros, como `INTERVALO_REFRESCO`. |
| `utils/trazas.py` | Registro de incidencias, logs y columnas de linaje. |
| `entrada/` | CSV exportados de la base de datos y `referencia_sql.csv`. |
| `datos_sinteticos/` | Histórico sintético (`normal/`) y copia con errores (`con_errores/`). |
| `outputs/` | Resultados en CSV y gráficos, por modo. |
| `logs/` | `pipeline.log` (carga, validación y ejecuciones de `main.py`) y `refresco.log` (una línea por cada ciclo del dashboard). |
| `tests/` | 63 tests con pytest, entre ellos `test_refresco.py` (ciclo de refresco) y `test_main.py` (consola). Ver [Tests](#tests). |
| `diccionario.md` | Descripción de los CSV de entrada y de las reglas de negocio. |
| `requirements.txt` | Librerías necesarias. |

### Datos reales y datos sintéticos

Hay dos orígenes de datos, que nunca se mezclan:

| Origen | Carpeta | De dónde sale | Cómo se identifica |
|---|---|---|---|
| **Datos reales** | `entrada/` | CSV exportados de la base de datos de [Acceso a Datos](#acceso-a-datos). | Insignia "Datos reales" y procedencia `ACC · REAL`. |
| **Histórico sintético** | `datos_sinteticos/normal/` | Generado por `generador_datos.py`. No representa clientes reales. | Insignia "Datos sintéticos" y procedencia `SINTÉTICO · LABORATORIO`. |

- **El dashboard arranca siempre con los datos reales**, que son la primera opción de "Origen de los datos" en la barra lateral.
- **Los datos reales tienen pocos meses y pocos clientes.** Por eso el clustering, la predicción y las cohortes salen como "no calculable", con el motivo. En la vista de modelos predictivos aparece el aviso **Laboratorio sintético**, que propone cambiar al histórico sintético para ver el método funcionando.
- **Al elegir "Histórico sintético", todas las vistas pasan a mostrar ese origen**, siempre con su etiqueta.

`datos_sinteticos/con_errores/` es una copia del histórico sintético con errores introducidos a propósito. Solo se usa desde la consola (`--modo errores`), para probar la validación.

### Contrato de datos

El pipeline espera estos cinco CSV en la carpeta de entrada, codificados en UTF-8 y separados por comas. `NULL` o una celda vacía significan nulo. El detalle de cada columna, sus tipos y las reglas de negocio están en [`Python/diccionario.md`](Python/diccionario.md).

| CSV | Clave | Relaciones | Columnas obligatorias |
|---|---|---|---|
| `clientes.csv` | `id_cliente` | — | `id_cliente`, `ref_odoo`, `tipo`, `ciudad`, `activo`, `fecha_alta` |
| `modelos.csv` | `id_modelo` | — | `id_modelo`, `ref_odoo`, `nombre`, `categoria`, `precio_base`, `personalizable`, `activo` |
| `pedidos.csv` | `id_pedido` | `id_cliente` → clientes | `id_pedido`, `ref_odoo`, `tipo`, `estado`, `fecha_pedido`, `fecha_entrega_prevista`, `fecha_confirmacion`, `fecha_cancelacion`, `total`, `id_cliente` |
| `lineas_pedido.csv` | `id_linea` | `id_pedido` → pedidos, `id_modelo` → modelos, (`id_variante`, `talla`) → stock | `id_linea`, `id_pedido`, `id_variante`, `id_modelo`, `color`, `talla`, `cantidad`, `precio_unitario`, `logo_club`, `personalizada` |
| `stock.csv` | `id_variante` + `talla` | `id_modelo` → modelos | `id_variante`, `id_modelo`, `color`, `talla`, `cantidad`, `stock_minimo`, `ultima_actualizacion` |

Además, `entrada/referencia_sql.csv` contiene los indicadores calculados en SQL, para la conciliación.

Si falta un CSV, falta una columna obligatoria o hay una clave que no existe en la tabla relacionada, la incidencia es **bloqueante** y no se publican resultados.

### Aplicaciones y versiones

| Aplicación | Versión requerida | Versión con la que se ha probado |
|---|---|---|
| Python | 3.14 | 3.14.7 |
| pandas | 2.3.3 o superior | 3.1.1 |
| numpy | 1.26 o superior | 2.5.4 |
| matplotlib | 3.9 o superior | 3.11.2 |
| scikit-learn | 1.4 o superior | 1.9.1 |
| streamlit | 1.50 o superior | 1.67.0 |
| plotly | 5.20 o superior | 7.1.0 |
| pytest | 8.0 o superior | 9.2.0 |

Las versiones requeridas son las de `requirements.txt`.

### Cómo montarlo

Desde la carpeta `Python/`:

1. Crea un entorno virtual:
   ```bash
   python -m venv venv
   ```
2. Actívalo:
   - En PowerShell o CMD: `venv\Scripts\activate`
   - En Git Bash: `source venv/Scripts/activate`
3. Instala las librerías:
   ```bash
   pip install -r requirements.txt
   ```

### Exportar los CSV de la base de datos

Los CSV de `entrada/` ya vienen en el repositorio. Solo hace falta volver a exportarlos si cambian los datos de la base de datos.

`acceso_a_datos/exportar_csv.sql` exporta los clientes, modelos, pedidos, líneas y stock a `Python/entrada/`, junto con `referencia_sql.csv`, que contiene los indicadores calculados en SQL. Todo se exporta dentro de una misma transacción de solo lectura, así que los archivos salen del mismo estado de la base de datos.

Desde la **PSQL Tool de pgAdmin**, conectado a `sneaker_factory`:

1. Abre `acceso_a_datos/exportar_csv.sql` y cambia la primera línea, `\cd Python/entrada`, por la ruta completa de tu carpeta `Python/entrada`. pgAdmin no se ejecuta desde la carpeta del proyecto, así que la ruta relativa no le sirve. Cada persona pone la suya, por ejemplo:
   ```
   \cd C:/Users/TU_USUARIO/Desktop/Proyecto/1er-Proyecto-2-DAM/Python/entrada
   ```
2. Ejecuta el script con `\i` y su ruta completa:
   ```
   \i C:/Users/TU_USUARIO/Desktop/Proyecto/1er-Proyecto-2-DAM/acceso_a_datos/exportar_csv.sql
   ```

Usa barras `/` en las rutas, también en Windows.

Desde la terminal no hace falta cambiar nada: ejecútalo con `psql` desde la raíz del proyecto:

```bash
psql -U postgres -d sneaker_factory -f acceso_a_datos/exportar_csv.sql
```

### Cómo ejecutarlo

Todo se ejecuta desde la carpeta `Python/` con el entorno virtual activado.

#### Consola (`main.py`)

`main.py` carga, valida e integra los datos, calcula todos los resultados y guarda los CSV, y los gráficos si no se indica lo contrario. Opciones (salida de `python main.py --help`):

| Opción | Valores | Qué hace |
|---|---|---|
| `--modo` | `real` (por defecto), `sintetico`, `errores` | `real`: CSV de `entrada/`. `sintetico`: `datos_sinteticos/normal/`. `errores`: `datos_sinteticos/con_errores/`. |
| `--fase` | `calidad`, `descriptivo`, `segmentacion`, `prediccion`, `completo` (por defecto) | Qué parte del análisis se ejecuta. Ver [Fases](#fases). |
| `--sin-figuras` | — | No genera los gráficos PNG. |
| `--entrada` | carpeta | Carpeta con los CSV. Por defecto, la del modo. |
| `--salida` | carpeta | Carpeta de resultados. Por defecto, `outputs/<modo>` (`outputs/real`, `outputs/sintetico` u `outputs/sintetico_errores`). |
| `--desde` | `AAAA-MM-DD` | Pedidos desde esa fecha, incluida. |
| `--hasta` | `AAAA-MM-DD` | Pedidos hasta esa fecha, incluida. |
| `--modelo` | uno o varios `id_modelo` | Solo las líneas de esos modelos. |
| `--talla` | una o varias tallas | Solo las líneas de esas tallas. |
| `--tipo` | `ESTANDAR`, `CUSTOM` | Solo esos tipos de pedido. |
| `--estado` | `BORRADOR`, `CONFIRMADO`, `CANCELADO` | Solo pedidos en esos estados. |
| `--cliente` | uno o varios `id_cliente` | Solo los pedidos de esos clientes. |

Ejemplos con los datos reales:

| Comando | Resultado |
|---|---|
| `python main.py --modo real --sin-figuras --tipo CUSTOM --estado CONFIRMADO` | 2 pedidos confirmados, 50 pares, 3.799,50 €. |
| `python main.py --modo real --sin-figuras --desde 2026-10-01 --hasta 2026-10-31 --talla 41 42` | 2 pedidos confirmados, 17 pares, 1.169,83 €. |
| `python main.py --modo real --sin-figuras --modelo 1` | Modelo Cometa: 1 pedido confirmado, 40 pares, 2.799,60 €. |

##### Fases

Con `--fase` se ejecuta solo una parte del análisis. La calidad se ejecuta siempre, porque las demás fases la necesitan. Si hay incidencias bloqueantes, ninguna fase publica resultados. La fase se puede combinar con `--modo`, `--entrada`, `--salida`, `--sin-figuras` y los filtros.

| Fase | Qué genera |
|---|---|
| `calidad` | Carga y validación, y los CSV de calidad: `manifiesto`, `resumen_calidad`, `incidencias`, `09_calidad_datos` y `09_incidencias_por_regla`. Termina ahí. |
| `descriptivo` | Calidad, más los KPIs y los análisis descriptivos (ventas por mes, ABC, matriz modelo × talla, matriz modelo × mes, productos estacionales, cambios en la mezcla de tallas, Custom frente a estándar, RFM, cohortes, stock, anomalías, margen, conciliación, estadísticos, hipótesis…) y los gráficos. |
| `segmentacion` | Calidad, más `06_clientes_rfm` y los `clusters_*`. |
| `prediccion` | Calidad, más `demanda_modelo_mes`, los `prediccion_*` y la figura `09_real_frente_prediccion.png`. |
| `completo` | Todo lo anterior. Es la opción por defecto: sin `--fase`, `main.py` funciona como siempre. |

Ejemplos ejecutados:

| Comando | Resultado |
|---|---|
| `python main.py --modo real --fase calidad` | Exit 0. Solo los 5 CSV de calidad, sin gráficos. |
| `python main.py --modo real --fase descriptivo --sin-figuras --tipo CUSTOM` | Exit 0. 31 CSV; los KPIs de los pedidos Custom: 50 pares y 3.799,50 €. |
| `python main.py --modo sintetico --fase segmentacion --sin-figuras` | Exit 0. 12 CSV: `CALCULADO con 59 clientes y k = 5 (mayor silhouette)…` |
| `python main.py --modo sintetico --fase prediccion --desde 2025-01-01` | Exit 0. 12 CSV y la figura de predicción: `entrenamiento 2025-04 a 2026-07 (239 filas), prueba 2026-08 a 2026-10 (48 filas). El modelo mejora al baseline: MAE 52.9 frente a 64.4…` |
| `python main.py --modo errores --fase calidad` | Exit 1. Los 5 CSV de calidad con las incidencias, y el aviso de incidencias bloqueantes. |

Si algo falla, `main.py` lo explica sin mostrar errores de Python:

| Situación | Qué muestra | Código de salida |
|---|---|---|
| Todo correcto | La tabla de calidad, los KPIs y la carpeta de resultados. | `0` |
| Incidencias bloqueantes en los CSV | `Hay incidencias BLOQUEANTES: no se publican KPIs ni gráficos.` y la ruta de `incidencias.csv`. | `1` |
| Ningún pedido cumple los filtros | `Ningún pedido cumple los filtros elegidos: no se publican KPIs ni gráficos. Prueba a quitar alguno.` | `1` |
| Fecha mal escrita, por ejemplo `--desde hola` | `error: argument --desde: fecha no válida: 'hola' (formato AAAA-MM-DD)` | `2` |

- **Resultados:** se guardan en `<salida>/csv/` y `<salida>/figuras/`. `indice_resultados.csv` lista los ficheros de resultados con sus filas y la función que los genera.
- **Conciliación:** en modo `real`, `12_reconciliacion_sql.csv` compara los indicadores de Python con los de SQL. Si todos salen `OK`, los datos cuadran.
- **Linaje:** cada CSV de resultados lleva al final las columnas `linaje_origen`, `linaje_fecha_corte`, `linaje_ejecucion`, `linaje_filtros`, `linaje_filas_origen` y `linaje_funcion`. Las descargas del dashboard también.
- **Estacionalidad y mezcla de tallas:**
  - `13_matriz_modelo_mes.csv` tiene un modelo por fila, un mes por columna y los pares vendidos en cada celda.
  - `14_productos_estacionales.csv` calcula, para cada modelo, un índice por mes del año: la media de ese mes entre la media de todos los meses. Por ejemplo, `oct = 1.45` significa que en octubre vende un 45 % más que en un mes normal. Un modelo es estacional si su mes pico llega a `UMBRAL_ESTACIONALIDAD` (1.3). Solo se calcula para los modelos con al menos 12 meses completos desde su primera venta.
  - `15_cambios_mezcla_tallas.csv` compara el % de pares de cada talla en los últimos 6 meses completos con los 6 anteriores. Marca `SUBE` o `BAJA` si la talla cambia `UMBRAL_CAMBIO_TALLA` puntos (2) o más, y `ESTABLE` si no.
  - `estacionales_estado.csv` y `mezcla_tallas_estado.csv` dicen si se han podido calcular.
- **Datos reales insuficientes:** con los datos reales, la predicción de demanda, el clustering, las cohortes, los productos estacionales y los cambios en la mezcla de tallas salen como `NO CALCULABLE`, porque hay pocos meses y pocos clientes. Para verlos funcionar, usa el modo `sintetico`.

#### Filtros

La consola y el dashboard usan los mismos filtros, con la misma función (`aplicar_filtros` de `analiticas.py`), y se pueden combinar:

| Filtro | Consola | Dashboard (barra lateral) |
|---|---|---|
| Periodo | `--desde`, `--hasta` | "Periodo del pedido" |
| Modelo | `--modelo` (por `id_modelo`) | "Modelo" (por nombre) |
| Talla | `--talla` | "Talla" |
| Tipo de pedido | `--tipo` | "Tipo de pedido" |
| Estado | `--estado` | "Estado" |
| Cliente | `--cliente` (por `id_cliente`) | "Cliente" (por referencia, `CLI-...`) |

**Un filtro sin rellenar no restringe los resultados.** En la consola, si no se pone una opción, se usan todos los valores. En el dashboard, una lista vacía equivale a "Todos", y el periodo solo se aplica si se cambian las fechas. **Restablecer filtros** los deja todos vacíos.

Con los filtros de modelo o talla, los totales de cada pedido se recalculan solo con las líneas que cumplen el filtro. La agrupación automática de clientes (KMeans) del dashboard se calcula siempre con todos los datos del origen, sin filtros.

#### Dashboard

```bash
streamlit run app_dashboard.py
```

Se abre en el navegador, en <http://localhost:8501>. En la barra lateral se elige el origen de los datos y se aplican los filtros. También se pueden descargar en CSV los datos filtrados: pedidos, ventas por mes, modelos ABC, clientes RFM y stock. Tiene seis vistas:
- Dirección;
- Producto y ventas;
- Clientes;
- Almacén;
- Calidad y auditoría;
- Modelos predictivos.

Para pararlo, pulsa `Ctrl + C` en la terminal.

#### Refresco automático

El dashboard se recalcula solo **cada 60 segundos**. El intervalo es `INTERVALO_REFRESCO` en `config.py`; `app_dashboard.py` lanza el ciclo y `refresco.py` lo ejecuta. En cada ciclo:

1. **Lee** los CSV de la carpeta del origen elegido.
2. **Valida** los datos con el pipeline: columnas, claves, tipos y relaciones.
3. **Recalcula** todos los resultados, aunque los CSV no hayan cambiado.
4. **Publica** los resultados si los datos son válidos. Si no lo son, sigue mostrando los últimos válidos.

El botón **Actualizar ahora**, en la barra lateral, lanza un ciclo al momento, sin esperar. Los filtros y la vista elegida se mantienen entre ciclos.

La barra de estado de arriba muestra el estado del último ciclo y estos datos:

| Dato | Significado |
|---|---|
| Última comprobación | Cuándo se ejecutó el último ciclo, haya salido bien o mal. |
| Última actualización válida | Cuándo se publicaron por última vez resultados válidos. Si nunca ha habido, pone "ninguna". |
| Filas válidas | Filas válidas de los cinco CSV en la última actualización válida. |
| Procedencia | `ACC · REAL` o `SINTÉTICO · LABORATORIO`. |
| Procesado en | Segundos que tardó el último ciclo. |

| Estado | Significado |
|---|---|
| `correcto` | Los CSV han cambiado y se han publicado resultados nuevos. |
| `sin cambios` | Los CSV son los mismos; se han recalculado y los valores no varían. |
| `datos inválidos` | Falta una columna, hay una clave huérfana u otra incidencia bloqueante. No se publica. |
| `error de carga` | Falta un CSV o no se ha podido leer. No se publica. |

**Insertar datos en PostgreSQL no cambia el dashboard por sí solo.** El dashboard lee los CSV, no la base de datos. Hay que volver a exportarlos con `acceso_a_datos/exportar_csv.sql` (ver [Exportar los CSV de la base de datos](#exportar-los-csv-de-la-base-de-datos)).

#### Probar con datos nuevos

Con el dashboard abierto en "Datos reales":

1. Apunta los indicadores de la vista **Dirección**, por ejemplo los ingresos válidos y los pares vendidos.
2. Crea un pedido en la web y apruébalo en el panel de administración, o aprueba uno que esté en `BORRADOR`. Solo los pedidos `CONFIRMADO` cuentan como venta.
3. Vuelve a exportar los CSV con `exportar_csv.sql`.
4. Espera al siguiente ciclo, como mucho 60 segundos, o pulsa **Actualizar ahora**.
5. La barra de estado pasa a `correcto`, con una nueva "Última actualización válida", y los indicadores incluyen el pedido nuevo. En **Calidad y auditoría**, la conciliación con PostgreSQL debe seguir cuadrando.

#### Si un CSV llega mal

Si en un ciclo falta un CSV o le falta una columna obligatoria, el dashboard **no publica resultados de ese ciclo**:
- la barra de estado pasa a `error de carga` o `datos inválidos`;
- aparece el aviso **No se publican resultados de este ciclo**, con el motivo (por ejemplo, `Error de carga: No existe stock.csv` o `Datos inválidos: pedidos: Faltan columnas: id_cliente`) y la tabla de incidencias;
- si antes hubo datos válidos, se sigue mostrando ese último resultado, marcado como **`DESACTUALIZADO · datos de <fecha y hora>`**. Si nunca los hubo, solo se muestra el error.

Para recuperarlo, vuelve a exportar los CSV correctamente, o corrige el que falla. En el siguiente ciclo, o al pulsar **Actualizar ahora**, el estado vuelve a `correcto` y desaparece el aviso, sin reiniciar la aplicación.

#### Logs

| Fichero | Qué registra |
|---|---|
| `logs/refresco.log` | Una línea por cada ciclo del dashboard: origen, filas válidas/leídas de cada CSV, duración, estado y motivo de la anomalía. Los ciclos correctos se registran como `INFO` y los fallidos como `WARNING`. |
| `logs/pipeline.log` | La carga de cada CSV, el fin de la validación con el número de incidencias, y el final de cada ejecución de `main.py`: correcta, bloqueada o sin resultados. |

Ejemplos de líneas reales:

```
# logs/refresco.log
2026-11-12 09:59:15 | INFO | origen=REAL | filas clientes=6/6 modelos=40/40 pedidos=12/12 lineas=41/41 stock=358/358 | duracion=0.50s | estado=correcto | anomalia=-
2026-11-12 10:00:16 | INFO | origen=REAL | filas clientes=6/6 modelos=40/40 pedidos=12/12 lineas=41/41 stock=358/358 | duracion=0.62s | estado=sin cambios | anomalia=-
2026-11-12 09:57:24 | WARNING | origen=PRUEBA | filas clientes=0/2 modelos=0/2 pedidos=0/0 lineas=0/3 stock=0/3 | duracion=0.06s | estado=datos inválidos | anomalia=pedidos: Faltan columnas: id_cliente

# logs/pipeline.log
2026-11-12 11:07:38 | INFO | lineas: 41 filas leídas
2026-11-12 11:07:38 | INFO | Fin de carga | incidencias=0
2026-11-10 20:17:01 | INFO | Ejecución correcta | origen=REAL | resultados=15 | duracion=3.30s
2026-11-12 11:07:38 | WARNING | Ejecución sin resultados | origen=REAL | ningún pedido cumple los filtros
```

Las líneas con `origen=PRUEBA` las generan los tests.

#### Tests

```bash
python -m pytest tests -v
```

Hay 63 tests:

| Archivo | Tests | Qué comprueba |
|---|---|---|
| `test_carga.py` | 5 | Lectura de los CSV: datos correctos, ruta inexistente, CSV vacío, columna ausente y fecha corrupta. |
| `test_integridad.py` | 7 | Claves huérfanas o duplicadas, cantidades negativas, cardinalidad de los cruces, pedidos con varias líneas o sin líneas, y que el CSV original no se modifica. |
| `test_calculos.py` | 16 | KPIs, filtros, ventas por mes, ABC, RFM, cobertura de stock, anomalías, margen, conciliación con SQL, bootstrap, hipótesis y comparación con el periodo anterior. |
| `test_estacionalidad.py` | 5 | Matriz modelo × mes, productos estacionales y cambios en la mezcla de tallas: con pocos meses no se calculan; con el histórico sintético, los índices tienen media 1 y los % de tallas suman 100. |
| `test_clustering.py` | 2 | Con pocos clientes no se agrupa; con el histórico sintético sí. |
| `test_prediccion.py` | 5 | Predicción de demanda: separación temporal, baseline y formato del resultado. |
| `test_visualizaciones.py` | 1 | Se generan las ocho figuras. |
| `test_reproducibilidad.py` | 3 | Misma semilla, mismos datos; distinta semilla, datos distintos; el sintético cumple los mínimos de tamaño. |
| `test_refresco.py` | 9 | Ciclo de refresco: sin cambios, columna ausente, fichero ausente, recuperación, intervalo, log y linaje. |
| `test_main.py` | 10 | Ejecución de `main.py`: completa, bloqueada, filtros de modelo y cliente, filtro sin resultados, fecha no válida y cada fase de `--fase`. |

#### Regenerar los datos sintéticos

Es opcional: ya vienen en el repositorio.

```bash
python generador_datos.py
```

Usa la semilla 42 por defecto, así que siempre genera los mismos datos. Para otra semilla, usa `--semilla N`. Genera `datos_sinteticos/normal/` y `datos_sinteticos/con_errores/`, junto con `errores_introducidos.csv`, que describe cada error.

---

## Demostración de extremo a extremo

Guion para repetir el caso completo con un pedido nuevo. Necesita montadas todas las partes y la API, la VM de Odoo y el dashboard en marcha.

1. **Pedido en la web.** En <http://localhost:3000>, inicia sesión como `comercial` y haz un pedido personalizado para un club. Queda en `BORRADOR` con la referencia `CUS-<número>`.
2. **Aprobación.** En el panel de administración (`admin.html`), aprueba el pedido. Pasa a `CONFIRMADO` y se descuenta el stock.
3. **Envío a Odoo.** En 30 segundos como mucho, el sincronizador lo envía. Compruébalo en Odoo, en **Ventas → Presupuestos**, con la referencia en **Referencia del cliente**, o en PostgreSQL:
   ```sql
   SELECT ref_odoo, estado, estado_odoo, odoo_id, error_odoo FROM pedido ORDER BY id_pedido DESC;
   ```
4. **Ficha para PSP.** Ejecuta `acceso_a_datos/exportar_ficha.sql`, que regenera `ProgramacionDeServiciosyProcesos/datos/ficha_fabricacion.csv` (ver [De dónde sale la ficha de fabricación](#de-dónde-sale-la-ficha-de-fabricación)). El pedido nuevo aparece junto a `CUS-0001` y `CUS-0004`.
5. **Coordinador.** Desde `ProgramacionDeServiciosyProcesos/`, ejecuta `java -cp out Coordinador`. Termina con código `0` y genera `salida/resumen_pedido.txt` y `salida/fichas_taller.txt` con el pedido nuevo.
6. **CSV para Python.** Ejecuta `acceso_a_datos/exportar_csv.sql` para actualizar `Python/entrada/`.
7. **Dashboard.** En el siguiente ciclo, o con **Actualizar ahora**, la barra pasa a `correcto` y los indicadores de ventas incluyen el pedido nuevo. En **Calidad y auditoría**, la conciliación con PostgreSQL sigue cuadrando.

---

## Autores

- Daniel Aldegunde García
- Carlos Muñoz
