# Sneaker Factory · DACA

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
| `consultas.sql` | Consultas de ejemplo: búsquedas, agregados y transacciones. |
| `pruebas.sql` | Pruebas de inserción, modificación, borrado y de los triggers. |
| `exportar_csv.sql` | Exporta las tablas a `Python/entrada/` para el análisis en Python. |
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
3. Para entrar al panel de administración, inicia sesión con uno de los usuarios de prueba de `carga_de_datos.sql`: `admin`, `comercial` o `almacen`. Sus contraseñas están en ese mismo script. Cada usuario puede hacer lo que permite su rol.

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
| Ubuntu | Pendiente de indicar | Sistema de la máquina virtual. |
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

1. **El cliente hace un pedido en la web.** Se guarda en PostgreSQL en estado `BORRADOR`, con la referencia `WEB-<número>` si es un pedido del carrito o `CUS-<número>` si es personalizado.
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
| `datos/ficha_fabricacion.csv` | Ficha de ejemplo correcta. |
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

---

## Python · Análisis de datos

### Descripción

Análisis de los datos de ventas:
- **Pipeline**: carga los CSV exportados de la base de datos, los valida (claves, tipos, fechas, rangos y relaciones entre tablas) y registra cada incidencia con su gravedad.
- **Analítica**: KPIs de ventas, clasificación ABC de modelos, matriz modelo × talla, Custom frente a estándar, segmentación RFM de clientes, cohortes, cobertura de stock, anomalías, estadísticos y contraste de hipótesis.
- **Modelos**: clustering de clientes (K-means) y predicción de demanda (RandomForest comparado con un baseline).
- **Conciliación**: compara los indicadores calculados en Python con los calculados en SQL.
- **Salidas**: gráficos, un **dashboard interactivo** con Streamlit y tests automáticos.

Además de los datos reales, hay un **histórico sintético** para demostrar los métodos que necesitan más datos, y una copia con errores introducidos para probar la validación.

### Archivos

| Archivo | Contenido |
|---|---|
| `main.py` | Ejecuta todo el análisis y guarda los resultados. |
| `pipeline.py` | Carga, validación e integración de los CSV. |
| `analiticas.py` | Cálculos: KPIs, ABC, RFM, cohortes, stock, hipótesis, clustering… |
| `prediccion.py` | Predicción de demanda por modelo y mes. |
| `visualizaciones.py` | Gráficos PNG. |
| `generador_datos.py` | Genera el histórico sintético y la copia con errores. |
| `app_dashboard.py`, `dashboard/` | Dashboard con Streamlit. |
| `.streamlit/config.toml` | Tema visual del dashboard. |
| `config.py` | Rutas, reglas de negocio y parámetros. |
| `utils/trazas.py` | Registro de incidencias y log. |
| `entrada/` | CSV exportados de la base de datos y `referencia_sql.csv`. |
| `datos_sinteticos/` | Histórico sintético (`normal/`) y copia con errores (`con_errores/`). |
| `outputs/` | Resultados en CSV y gráficos, por modo. |
| `tests/` | Tests con pytest. |
| `diccionario.md` | Descripción de los CSV de entrada y de las reglas de negocio. |
| `requirements.txt` | Librerías necesarias. |

### Aplicaciones y versiones

| Aplicación | Versión |
|---|---|
| Python | 3.14 (3.14.7) |
| pandas | 3.1 (mínimo 2.2) |
| numpy | 2.5 (mínimo 1.26) |
| matplotlib | 3.11 (mínimo 3.9) |
| scikit-learn | 1.9 (mínimo 1.4) |
| streamlit | 1.67 (mínimo 1.50) |
| plotly | 7.1 |
| pytest | 9.2 (mínimo 8.0) |

Las versiones mínimas son las de `requirements.txt`.

**Pendiente:** `plotly` lo usa el dashboard, pero no está en `requirements.txt`. Hasta que se añada, hay que instalarlo aparte (paso 3 de "Cómo montarlo").

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
   pip install plotly
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

**Análisis completo:**

| Comando | Qué hace |
|---|---|
| `python main.py --modo real` | Analiza los datos reales de `entrada/`. Es el modo por defecto. |
| `python main.py --modo sintetico` | Analiza el histórico sintético de `datos_sinteticos/normal/`. |
| `python main.py --modo errores` | Usa la copia con errores de `datos_sinteticos/con_errores/`. Se detiene sin publicar KPIs ni gráficos porque hay incidencias bloqueantes. |
| `python main.py --modo ... --sin-figuras` | Igual, pero sin generar los gráficos PNG. |

- **Resultados:** se guardan en `outputs/<modo>/csv/` y `outputs/<modo>/figuras/`. Las incidencias se registran en `logs/pipeline.log`.
- **Conciliación:** en modo `real`, `12_reconciliacion_sql.csv` compara los indicadores de Python con los de SQL. Si todos salen `OK`, los datos cuadran.
- **Datos reales insuficientes:** con los datos reales, la predicción de demanda y el clustering salen como `NO CALCULABLE`, porque hay pocos meses y pocos clientes. Para verlos funcionar, usa el modo `sintetico`.

**Dashboard:**

```bash
streamlit run app_dashboard.py
```

Se abre en el navegador, en <http://localhost:8501>. En la barra lateral se elige el origen de los datos (reales o histórico sintético) y se aplican filtros por periodo, modelo, talla, tipo, estado y cliente. También se pueden descargar los datos filtrados en CSV. Tiene seis vistas:
- Dirección;
- Producto y ventas;
- Clientes;
- Almacén;
- Calidad y auditoría;
- Modelos predictivos.

Para pararlo, pulsa `Ctrl + C` en la terminal.

**Tests:**

```bash
python -m pytest tests -v
```

**Regenerar los datos sintéticos** (opcional; ya vienen en el repositorio):

```bash
python generador_datos.py
```

Usa la semilla 42 por defecto, así que siempre genera los mismos datos. Para otra semilla, usa `--semilla N`.

---

## Autores

- Daniel Aldegunde García
- Carlos Muñoz
