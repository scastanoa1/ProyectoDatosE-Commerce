# Estructura de datos en S3 (Iceberg) – E-commerce

Fecha: 15 de octubre de 2026

## 1. Propósito y alcance

Los datos del e-commerce se guardan en Amazon S3 como tablas Apache Iceberg, registradas en AWS Glue Data Catalog. Este documento define las capas Bronze y Silver; la capa Gold se construye en BigQuery y se documenta aparte.

- **Quién escribe:** AWS Glue (PySpark), orquestado por EventBridge Scheduler y Step Functions.
- **Fuentes:**
    - Base de datos PostgreSQL de la tienda: 13 tablas, definidas en `Modelo_de_datos.md`.
    - Eventos web y eventos de login, recibidos vía Google Pub/Sub, con el contrato definido en `Estructura_eventos.md`.
- **Quién lee:** los jobs de Glue que construyen Silver y la carga hacia BigQuery.

## 2. Organización del bucket y del catálogo

Se usa un solo bucket con una carpeta (prefijo) por capa, y cada capa es una base de datos en el Glue Data Catalog. Cada tabla vive en `s3://ecommerce-lakehouse/<capa>/<tabla>/`.

```
s3://ecommerce-lakehouse/                 (catálogo: AWS Glue Data Catalog)
├── bronze/                               → Glue DB: bronze
│   ├── web_events/                       · days(event_time)
│   ├── login_events/                     · days(event_time)
│   ├── pg_users/                         · days(_ingestion_ts)
│   ├── pg_addresses/                     · days(_ingestion_ts)
│   ├── pg_categories/                    · days(_ingestion_ts)
│   ├── pg_products/                      · days(_ingestion_ts)
│   ├── pg_product_variants/              · days(_ingestion_ts)
│   ├── pg_product_categories/            · days(_ingestion_ts)
│   ├── pg_product_inventory/             · days(_ingestion_ts)
│   ├── pg_orders/                        · days(_ingestion_ts)
│   ├── pg_order_items/                   · days(_ingestion_ts)
│   ├── pg_payments/                      · days(_ingestion_ts)
│   ├── pg_carts/                         · days(_ingestion_ts)
│   ├── pg_cart_items/                    · days(_ingestion_ts)
│   └── pg_product_reviews/               · days(_ingestion_ts)
└── silver/                               → Glue DB: silver
    ├── events/                           · days(event_time)
    ├── logins/                           · days(event_time)
    ├── customers/                        · sin partición
    ├── addresses/                        · sin partición
    ├── categories/                       · sin partición
    ├── products/                         · sin partición
    ├── product_variants/                 · sin partición
    ├── product_categories/               · sin partición
    ├── inventory/                        · sin partición
    ├── orders/                           · months(order_date)
    ├── order_items/                      · months(created_at)
    ├── payments/                         · months(created_at)
    ├── carts/                            · months(created_at)
    ├── cart_items/                       · months(added_at)
    └── reviews/                          · sin partición
```

Dentro de cada tabla (ejemplo: `bronze/web_events/`), Iceberg crea y administra estas carpetas:

```
web_events/
├── data/
│   └── event_time_day=2026-10-11/
│       └── 00000-0-….parquet             (los datos)
└── metadata/
    ├── vN.metadata.json                  (esquema, partición, snapshots)
    └── snap-….avro, manifests            (archivos de cada versión)
```

> [!NOTE] Tener en cuenta Las carpetas `data/` y `metadata/` las crea Iceberg: no se escriben a mano. Lo que el equipo define es qué tablas hay, su esquema y su partición.

## 3. Convenciones

Todas las tablas siguen las mismas reglas de nombres, tipos y formato, para que cualquier job de Glue las lea igual.

|Elemento|Convención|Ejemplo|
|---|---|---|
|Base de datos (Glue)|Nombre de la capa|`bronze`, `silver`|
|Tablas Bronze|`<fuente>_<tabla de origen>`|`pg_orders`, `web_events`|
|Tablas Silver|Entidad de negocio en plural|`orders`, `customers`|
|Columnas|snake_case, en inglés|`customer_id`, `created_at`|
|Columnas en Bronze|Mismo nombre que en el origen|`user_id`|
|Usuario en Silver|`user_id` de Postgres se renombra a `customer_id`, como en los eventos|`orders.customer_id`|
|IDs de negocio|`string` con el mismo UUID de PostgreSQL|`customer_id`, `variant_id`|
|IDs de tracking|`string` con prefijo (no existen en Postgres)|`evt_01JXYZ123`, `ses_98765`|
|Fecha y hora|`timestamp` en UTC, sufijo `_at`|`created_at`|
|Hora del evento|Se conserva el nombre del contrato: `event_time`|`event_time`|
|Solo fecha|`date`, sufijo `_date`|`order_date`|
|Montos|`decimal(12,2)`|`total_amount`|
|Formato de archivo|Parquet comprimido con zstd|`write.format.default = parquet`|
|Versión de Iceberg|v2 (permite `MERGE` y `DELETE`)|`format-version = 2`|

Conversión de tipos de PostgreSQL a Iceberg:

|PostgreSQL|Iceberg|
|---|---|
|`uuid`|`string`|
|`varchar(n)`, `text`|`string`|
|`numeric(12,2)`|`decimal(12,2)`|
|`integer`|`int`|
|`boolean`|`boolean`|
|`date`|`date`|
|`timestamp`|`timestamp` (se asume que Postgres guarda la hora en UTC)|

Los UUID se guardan como `string` y no con el tipo `uuid` de Iceberg, porque Spark en Glue y BigQuery lo manejan de forma limitada.

Cada tabla Bronze lleva además estas columnas técnicas:

|Columna|Tipo|Descripción|
|---|---|---|
|`_ingestion_ts`|timestamp|Momento en que Glue escribió el registro|
|`_source`|string|Origen: `postgres`, `pubsub_web` o `pubsub_login`|
|`_extraction_type`|string|`incremental` o `full`; solo en tablas de Postgres|
|`_batch_id`|string|Id de la ejecución de Step Functions que lo cargó|

En Silver se conserva solo `_updated_at`: cuándo se actualizó la fila por última vez.

## 4. Capa Bronze

Bronze guarda los datos tal como llegan de cada fuente, una tabla por fuente, solo con append. Cada tabla se documenta con una ficha y su esquema.

### 4.1 Eventos

En los eventos se respeta la forma del JSON: las secciones del contrato se guardan como `struct`, y `payload` queda como JSON en texto porque cambia según `event_type`.

#### bronze.web_events

|Propiedad|Valor|
|---|---|
|Fuente|Pub/Sub, tópico de eventos web|
|Filtro|Solo eventos cuyo `processing.targets` incluye `batch`|
|Granularidad|1 fila = 1 mensaje recibido (puede haber duplicados)|
|Llave|`event_id`|
|Partición|`days(event_time)`|
|Escritura|Append|
|Ubicación|`s3://ecommerce-lakehouse/bronze/web_events/`|

|Columna|Tipo|Nulo|Descripción|
|---|---|---|---|
|`event_id`|string|No|Id único del evento|
|`event_type`|string|No|`product_view`, `add_to_cart`, `search`, `purchase`…|
|`event_version`|int|No|Versión del contrato del evento|
|`event_time`|timestamp|No|Cuándo ocurrió el evento; se convierte del texto ISO 8601 UTC|
|`processing`|struct<targets: array<string>>|No|Pipelines destino: `streaming`, `batch`|
|`customer`|struct<customer_id: string, anonymous_id: string>|No|Usuario registrado (UUID de `users.user_id`) o anónimo|
|`session`|struct<session_id: string>|No|Sesión de navegación|
|`device`|struct<device_type: string, os: string, browser: string>|Sí|Dispositivo desde el que se generó|
|`source`|struct<channel: string, page: string, referrer: string>|Sí|Canal, página y página de origen|
|`payload`|string (JSON)|Sí|Datos propios de cada `event_type`, sin transformar|
|`_ingestion_ts`, `_source`, `_batch_id`|—|No|Columnas técnicas|

`bronze.login_events` tiene la misma ficha y el mismo esquema, con origen en el tópico de eventos de login.

### 4.2 Tablas de PostgreSQL

Cada tabla de Postgres tiene su tabla `bronze.pg_<tabla>` con las mismas columnas y nombres del origen (ver `Modelo_de_datos.md`), los tipos convertidos según la sección 3 y las columnas técnicas. Todas se escriben con append y se particionan por `days(_ingestion_ts)`, así cada carga queda separada y se puede reprocesar.

La estrategia de extracción define qué llega en cada carga:

- **Incremental:** solo las filas nuevas o cambiadas desde la última carga, según el campo de control.
- **Completa:** la tabla entera en cada carga. Bronze acumula una foto por carga, y Silver usa solo la más reciente.

| Tabla Bronze                   | Tabla Postgres       | Estrategia                   | Campo de control                 |
| ------------------------------ | -------------------- | ---------------------------- | -------------------------------- |
| `bronze.pg_users`              | `users`              | Incremental                  | `updated_at`                     |
| `bronze.pg_addresses`          | `addresses`          | Completa                     | —                                |
| `bronze.pg_categories`         | `categories`         | Completa                     | —                                |
| `bronze.pg_products`           | `products`           | Incremental                  | `updated_at`                     |
| `bronze.pg_product_variants`   | `product_variants`   | Completa                     | —                                |
| `bronze.pg_product_categories` | `product_categories` | Completa                     | —                                |
| `bronze.pg_product_inventory`  | `product_inventory`  | Incremental                  | `updated_at`                     |
| `bronze.pg_orders`             | `orders`             | Incremental                  | `updated_at`                     |
| `bronze.pg_order_items`        | `order_items`        | Incremental (solo inserción) | `created_at`                     |
| `bronze.pg_payments`           | `payments`           | Completa                     | —                                |
| `bronze.pg_carts`              | `carts`              | Incremental                  | `updated_at`                     |
| `bronze.pg_cart_items`         | `cart_items`         | Incremental                  | `GREATEST(added_at, removed_at)` |
| `bronze.pg_product_reviews`    | `product_reviews`    | Incremental (solo inserción) | `created_at`                     |

> [!WARNING] Datos sensibles `users.password_hash` no se extrae: se excluye desde la consulta de origen y no llega a ninguna capa de S3. `email` y `phone` sí llegan a Bronze tal como vienen y se protegen en Silver (sección 5.2).

#### Ejemplo de ficha: bronze.pg_orders

|Propiedad|Valor|
|---|---|
|Fuente|PostgreSQL, tabla `orders`|
|Estrategia|Incremental por `updated_at`|
|Granularidad|1 fila = 1 versión extraída de una orden|
|Llave|`order_id` + `_ingestion_ts`|
|Partición|`days(_ingestion_ts)`|
|Escritura|Append (guarda el historial de extracciones)|
|Ubicación|`s3://ecommerce-lakehouse/bronze/pg_orders/`|

|Columna|Tipo|Nulo|Descripción|
|---|---|---|---|
|`order_id`|string (UUID)|No|Id de la orden|
|`user_id`|string (UUID)|No|Cliente que compró|
|`shipping_address_id`|string (UUID)|Sí|Dirección de envío|
|`billing_address_id`|string (UUID)|Sí|Dirección de facturación|
|`status`|string|No|Estado tal como viene de Postgres|
|`subtotal`|decimal(12,2)|No|Subtotal|
|`discount_amount`|decimal(12,2)|Sí|Descuento|
|`tax_amount`|decimal(12,2)|Sí|Impuestos|
|`shipping_amount`|decimal(12,2)|Sí|Envío|
|`total_amount`|decimal(12,2)|No|Total|
|`currency`|string|No|Moneda (código de 3 letras)|
|`created_at`|timestamp|No|Creación de la orden|
|`updated_at`|timestamp|No|Último cambio en Postgres|
|`_ingestion_ts`, `_source`, `_extraction_type`, `_batch_id`|—|No|Columnas técnicas|

## 5. Capa Silver

Silver tiene una tabla por entidad de negocio, limpia, tipada y sin duplicados. Como los eventos usan los mismos UUID de Postgres, se cruzan directamente con `orders`, `products`, `product_variants` y `customers` sin tablas de mapeo. Además de la ficha y el esquema, cada tabla documenta sus reglas de limpieza.

El modo de escritura depende de cómo se extrae el origen:

- **Origen incremental → `MERGE INTO`** por la llave: inserta lo nuevo y actualiza lo que cambió.
- **Origen completo → `INSERT OVERWRITE`** con la foto más reciente de Bronze: la tabla queda igual al origen, incluidas las filas borradas en Postgres.

### 5.1 silver.orders

|Propiedad|Valor|
|---|---|
|Origen|`bronze.pg_orders`|
|Granularidad|1 fila = 1 orden, en su versión más reciente|
|Llave primaria|`order_id`|
|Partición|`months(order_date)`|
|Escritura|`MERGE INTO` por `order_id`|
|Ubicación|`s3://ecommerce-lakehouse/silver/orders/`|

|Columna|Tipo|Nulo|Descripción|
|---|---|---|---|
|`order_id`|string (UUID)|No|Llave primaria|
|`customer_id`|string (UUID)|No|`orders.user_id`; llave hacia `silver.customers`|
|`shipping_address_id`|string (UUID)|Sí|Llave hacia `silver.addresses`|
|`billing_address_id`|string (UUID)|Sí|Llave hacia `silver.addresses`|
|`status`|string|No|`pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`|
|`subtotal`|decimal(12,2)|No|Subtotal|
|`discount_amount`|decimal(12,2)|No|Descuento (0 si viene vacío)|
|`tax_amount`|decimal(12,2)|No|Impuestos (0 si viene vacío)|
|`shipping_amount`|decimal(12,2)|No|Envío (0 si viene vacío)|
|`total_amount`|decimal(12,2)|No|Total|
|`currency`|string|No|Moneda en mayúsculas (`COP`, `USD`…)|
|`order_date`|date|No|Fecha de la orden, derivada de `created_at`|
|`created_at`|timestamp|No|Creación de la orden (UTC)|
|`updated_at`|timestamp|No|Último cambio en Postgres|
|`_updated_at`|timestamp|No|Última actualización en Silver|

Reglas de limpieza:

1. Deduplicar por `order_id`, quedándose con el `updated_at` más reciente.
2. Normalizar `status` a minúsculas y validar que esté entre los 7 estados permitidos.
3. Reemplazar montos vacíos de descuento, impuestos y envío por 0.
4. Descartar filas sin `order_id` o con `total_amount` negativo y registrarlas aparte.

### 5.2 silver.customers

|Propiedad|Valor|
|---|---|
|Origen|`bronze.pg_users`|
|Granularidad|1 fila = 1 cliente, en su versión más reciente|
|Llave primaria|`customer_id` (= `users.user_id`)|
|Partición|Sin partición|
|Escritura|`MERGE INTO` por `customer_id`|
|Ubicación|`s3://ecommerce-lakehouse/silver/customers/`|

|Columna|Tipo|Nulo|Descripción|
|---|---|---|---|
|`customer_id`|string (UUID)|No|Llave primaria|
|`email_hash`|string|No|Hash SHA-256 del correo en minúsculas|
|`phone_hash`|string|Sí|Hash SHA-256 del teléfono|
|`first_name`|string|Sí|Nombre|
|`last_name`|string|Sí|Apellido|
|`age_range`|string|Sí|Rango de edad derivado de `birth_date` (propuesta: `18-24`, `25-34`, `35-44`, `45-54`, `55+`)|
|`gender`|string|Sí|Género, opcional|
|`status`|string|No|`active`, `inactive`, `blocked`|
|`created_at`|timestamp|No|Fecha de registro|
|`updated_at`|timestamp|No|Último cambio en Postgres|
|`_updated_at`|timestamp|No|Última actualización en Silver|

Reglas de limpieza:

1. Deduplicar por `customer_id`, quedándose con el `updated_at` más reciente.
2. Reemplazar `email` y `phone` por su hash; las columnas originales no pasan a Silver.
3. Reemplazar `birth_date` por `age_range`.

### 5.3 silver.events

|Propiedad|Valor|
|---|---|
|Origen|`bronze.web_events`|
|Granularidad|1 fila = 1 evento único|
|Llave primaria|`event_id`|
|Partición|`days(event_time)`|
|Orden de escritura|`session_id`, `event_time`|
|Escritura|`MERGE INTO` por `event_id` (evita duplicados de Pub/Sub)|
|Ubicación|`s3://ecommerce-lakehouse/silver/events/`|

Los `struct` de Bronze se aplanan en columnas, y los IDs de negocio del `payload` se extraen a columnas propias.

|Columna|Tipo|Nulo|Descripción|
|---|---|---|---|
|`event_id`|string|No|Llave primaria|
|`event_type`|string|No|Tipo de evento|
|`event_version`|int|No|Versión del contrato con la que se leyó el evento|
|`event_time`|timestamp|No|Cuándo ocurrió el evento (UTC)|
|`customer_id`|string (UUID)|Sí|Usuario registrado; llave hacia `silver.customers`|
|`anonymous_id`|string|Sí|Id temporal del usuario anónimo|
|`session_id`|string|No|Sesión de navegación|
|`device_type`|string|Sí|`mobile`, `desktop`, `tablet`|
|`os`|string|Sí|Sistema operativo|
|`browser`|string|Sí|Navegador|
|`channel`|string|Sí|`web`, `app`…|
|`page`|string|Sí|Página donde ocurrió|
|`referrer`|string|Sí|Página o fuente de origen|
|`product_id`|string (UUID)|Sí|Llave hacia `silver.products`, si el evento lo trae|
|`variant_id`|string (UUID)|Sí|Llave hacia `silver.product_variants`, si el evento lo trae|
|`category_id`|string (UUID)|Sí|Llave hacia `silver.categories`, si el evento lo trae|
|`cart_id`|string (UUID)|Sí|Llave hacia `silver.carts`, si el evento lo trae|
|`order_id`|string (UUID)|Sí|Llave hacia `silver.orders`, si el evento lo trae|
|`payload`|string (JSON)|Sí|Resto del `payload`, hasta definir el contrato de cada `event_type`|
|`_updated_at`|timestamp|No|Última actualización en Silver|

Reglas de limpieza:

1. Deduplicar por `event_id`.
2. Leer cada evento según su `event_version`, para que los cambios de contrato no rompan eventos viejos.
3. Descartar eventos sin `event_id`, `event_type` o `event_time` válido y registrarlos aparte.
4. Pendiente de definir: qué identificador prevalece cuando un evento trae `customer_id` y `anonymous_id` (por ejemplo, tras un login en la sesión).

`silver.logins` sigue la misma ficha, con origen en `bronze.login_events`.

### 5.4 Resto de tablas Silver

Estas tablas conservan las columnas de Postgres con los cambios de la sección 3 (`user_id` pasa a `customer_id`) y las reglas indicadas en la última columna.

|Tabla|Origen|Llave|Partición|Escritura|Reglas particulares|
|---|---|---|---|---|---|
|`silver.addresses`|`bronze.pg_addresses`|`address_id`|Sin partición|INSERT OVERWRITE|Se excluye `address_line`; para análisis geográfico bastan `city`, `state` y `country`|
|`silver.categories`|`bronze.pg_categories`|`category_id`|Sin partición|INSERT OVERWRITE|Se conserva `parent_category_id` para la jerarquía|
|`silver.products`|`bronze.pg_products`|`product_id`|Sin partición|MERGE|Se conserva `cost_price` para calcular margen|
|`silver.product_variants`|`bronze.pg_product_variants`|`variant_id`|Sin partición|INSERT OVERWRITE|—|
|`silver.product_categories`|`bronze.pg_product_categories`|`product_id` + `category_id`|Sin partición|INSERT OVERWRITE|—|
|`silver.inventory`|`bronze.pg_product_inventory`|`inventory_id`|Sin partición|MERGE|—|
|`silver.order_items`|`bronze.pg_order_items`|`order_item_id`|`months(created_at)`|MERGE|—|
|`silver.payments`|`bronze.pg_payments`|`payment_id`|`months(created_at)`|INSERT OVERWRITE|`transaction_reference` se conserva solo para conciliación; no pasa a Gold|
|`silver.carts`|`bronze.pg_carts`|`cart_id`|`months(created_at)`|MERGE|—|
|`silver.cart_items`|`bronze.pg_cart_items`|`cart_item_id`|`months(added_at)`|MERGE|`removed_at` vacío = el producto sigue en el carrito|
|`silver.reviews`|`bronze.pg_product_reviews`|`review_id`|Sin partición|MERGE|Validar que `rating` esté entre 1 y 5|

## 6. Criterios de partición y escritura

La partición se elige por la columna con la que más se filtra cada tabla, y el modo de escritura por si los registros cambian o no.

Iceberg usa _hidden partitioning_: la partición se define en la tabla con una transformación (`days`, `months`) y no existe una columna extra. Las consultas filtran por `event_time` u `order_date` normalmente e Iceberg descarta los archivos que no aplican.

|Caso|Partición|Por qué|
|---|---|---|
|Eventos de alto volumen|`days(event_time)`|Se consultan por rangos de días|
|Transacciones (órdenes, ítems, pagos, carritos)|`months(<fecha>)`|Volumen menor; por día quedarían archivos muy pequeños|
|Dimensiones (clientes, productos, categorías, inventario)|Sin partición|Pocas filas; particionar solo crea archivos diminutos|
|Todas las tablas de Postgres en Bronze|`days(_ingestion_ts)`|Separa cada carga y permite reprocesarla|

- **Append:** todo Bronze; los datos no se modifican una vez escritos.
- **MERGE INTO:** Silver con origen incremental; los registros se actualizan o pueden llegar duplicados.
- **INSERT OVERWRITE:** Silver con origen de carga completa; se reemplaza con la foto más reciente.
- Si una partición deja de servir, Iceberg permite cambiarla sin reescribir la tabla (_partition evolution_).

## 7. Mantenimiento y evolución

Iceberg acumula archivos pequeños y versiones viejas, así que se programan tareas de mantenimiento con Glue. Los valores son una propuesta de ejemplo.

|Tarea|Procedimiento de Iceberg|Frecuencia propuesta|
|---|---|---|
|Compactar archivos pequeños|`rewrite_data_files`|Semanal|
|Borrar versiones viejas|`expire_snapshots` (conservar 7 días)|Diaria|
|Borrar archivos huérfanos|`remove_orphan_files`|Mensual|
|Borrar fotos viejas de tablas con carga completa en Bronze|`DELETE` por `_ingestion_ts` (conservar 30 días)|Semanal|

Reglas para cambiar el esquema:

- Agregar columnas opcionales está permitido sin aviso.
- Renombrar, cambiar de tipo o borrar columnas se registra en este documento antes de aplicarse.
- Cuando el contrato de eventos cambia, sube `event_version`: Bronze lo guarda sin cambios y Silver agrega la lógica para leer la nueva versión.
- Si se agrega `updated_at` a `payments`, `product_variants` o `addresses` (pendiente recomendado en `Modelo_de_datos.md`), su extracción pasa a incremental y su tabla Silver a `MERGE INTO`.
- Cada cambio se anota con fecha, tabla y motivo.