# Estructura de datos en DynamoDB – E-commerce

## 1. Propósito y alcance

Este documento define las tablas de DynamoDB que alimenta el pipeline de streaming:

```
Google Pub/Sub → Apache Flink → DynamoDB → página / backend
```

DynamoDB es la capa de servicio en tiempo real. Guarda resultados ya calculados que la página o el backend consultan por llave en milisegundos. Cubre dos frentes:

- **Recomendaciones:** actividad reciente, recomendaciones personalizadas, productos relacionados y tendencias.
- **Seguridad y fraude:** inicios de sesión maliciosos, riesgo de órdenes y alertas.

El análisis histórico no se hace aquí. Ese detalle vive en S3 (Bronze/Silver) y BigQuery (Gold).

## 2. Criterio: qué va a DynamoDB y qué no

| Qué se guarda                                                                          | Dónde           | Cómo se consulta                                    |
| -------------------------------------------------------------------------------------- | --------------- | --------------------------------------------------- |
| Resultados finales: recomendaciones, rankings, estado de riesgo, alertas               | DynamoDB        | La página o el backend, por llave y en milisegundos |
| Cálculos intermedios: contadores, último login por cuenta, co-ocurrencias de productos | Estado de Flink | No se consulta; solo lo usa Flink para calcular     |
| Eventos crudos e historia completa                                                     | S3 (batch)      | Con SQL en BigQuery y en Power BI                   |

Por eso no existe una tabla de eventos crudos ni de intentos de login individuales: Flink los cuenta en su estado y solo escribe la conclusión.

## 3. Convenciones

- **Nombres:** tablas y atributos en `snake_case`.
- **Llaves:** la PK se llama según lo que representa (`user_key`, `product_id`, `entity`…). Cuando hay SK, se llama `sk` si es compuesta.
- **SK compuestas:** se separan con `#`. Ejemplo: `2026-10-16T16:20:05Z#3f2a…`.
- **Prefijos de tipo:** cuando una llave puede representar varias cosas, lleva prefijo: `ACCOUNT#`, `IP#`, `DEVICE#`, `CATEGORY#`.
- **`user_key`:** es el `customer_id` si el usuario inició sesión y, si no, el `anonymous_id`. Al hacer login, Flink fusiona el estado de la sesión anónima con el del cliente.
- **Fechas:** texto ISO 8601 en UTC (`2026-10-16T16:20:05Z`).
- **TTL:** atributo `expires_at`, número en epoch segundos (formato que exige DynamoDB). DynamoDB borra el ítem después de esa fecha.
- **Datos sensibles:** no se guardan emails ni IPs en claro. Se usan hashes (`login_identifier_hash`, `ip_hash`), igual que en Silver.
- **Escrituras idempotentes:** Flink escribe con `PutItem` o `UpdateItem` sobre la misma llave. Si reprocesa un evento, sobrescribe en vez de duplicar.
- **Lecturas:** cada tabla responde a una consulta por llave (`GetItem`, `BatchGetItem` o `Query`). No se usan `Scan`.
- **Capacidad:** modo on-demand en todas las tablas.

Los ejemplos de ítems se muestran en JSON plano para facilitar la lectura, no en el formato tipado de DynamoDB (`{"S": …}`).

## 4. Resumen de tablas

|Dominio|Tabla|PK|SK|TTL|Quién la lee|
|---|---|---|---|---|---|
|Recomendaciones|`user_recent_activity`|`user_key`|`sk` (`ts#event_id`)|30 días|Página: "vistos recientemente"|
|Recomendaciones|`user_recommendations`|`user_key`|`placement`|7 días|Página: carruseles personalizados|
|Recomendaciones|`product_realtime`|`product_id`|—|Sin TTL|Ficha de producto|
|Recomendaciones|`trending`|`scope`|`window`|Sin TTL|Home, categorías, buscador|
|Recomendaciones (opcional)|`checkout_sessions`|`user_key`|—|7 días|Página: recordatorio de carrito|
|Seguridad y fraude|`risk_status`|`entity`|—|Según bloqueo|Backend de login|
|Seguridad y fraude|`order_risk`|`order_id`|—|90 días|Backend de despacho, panel interno|
|Seguridad y fraude|`security_alerts`|`customer_key`|`sk` (`ts#alert_id`)|180 días|Página ("¿fuiste tú?"), panel de soporte|

---

## 5. Tablas de recomendaciones

### 5.1 `user_recent_activity`

**Propósito:** últimas interacciones de cada usuario con productos y búsquedas. Alimenta "vistos recientemente" y sirve de entrada para las recomendaciones.

**Eventos:** `product_view`, `add_to_cart`, `remove_from_cart`, `product_favorite`, `search`.

|Atributo|Tipo|Descripción|
|---|---|---|
|`user_key` (PK)|S|`customer_id` o `anonymous_id`|
|`sk` (SK)|S|`event_ts#event_id`|
|`event_type`|S|Tipo de evento de origen|
|`product_id`|S|Producto (vacío en `search`)|
|`variant_id`|S|Variante, si el evento la trae|
|`category_id`|S|Categoría de navegación|
|`search_query`|S|Texto buscado (solo en `search`)|
|`event_ts`|S|Fecha del evento|
|`expires_at`|N|TTL: `event_ts` + 30 días|

**Acceso:** `Query` por `user_key` con `ScanIndexForward = false` y `Limit = 20` para traer lo más reciente primero.

```json
{
  "user_key": "9b1d6c2e-4f7a-4c1b-8e2d-1a2b3c4d5e6f",
  "sk": "2026-10-16T16:20:05Z#a7c3e1f0-2b4d-4e6f-8a9b-0c1d2e3f4a5b",
  "event_type": "product_view",
  "product_id": "5e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
  "category_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "event_ts": "2026-10-16T16:20:05Z",
  "expires_at": 1794759605
}
```

### 5.2 `user_recommendations`

**Propósito:** lista de productos recomendados por usuario y por lugar de la página.

**Eventos:** los mismos de `user_recent_activity`. Flink combina la actividad reciente del usuario con los productos relacionados de `product_realtime`.

|Atributo|Tipo|Descripción|
|---|---|---|
|`user_key` (PK)|S|`customer_id` o `anonymous_id`|
|`placement` (SK)|S|Lugar de la página: `HOME`, `CART`, `PDP`|
|`items`|L|Lista ordenada de `{product_id, score, reason}`|
|`algorithm_version`|S|Versión del cálculo. Se usa para medir con `recommendation_impression` / `recommendation_click`|
|`generated_at`|S|Fecha del cálculo|
|`expires_at`|N|TTL: `generated_at` + 7 días|

**Acceso:** `GetItem` por `user_key` + `placement`. Si no hay ítem (usuario nuevo), la página usa `trending` con `scope = GLOBAL`.

```json
{
  "user_key": "9b1d6c2e-4f7a-4c1b-8e2d-1a2b3c4d5e6f",
  "placement": "HOME",
  "items": [
    {"product_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "score": 0.91, "reason": "related_to_viewed"},
    {"product_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f", "score": 0.84, "reason": "same_category"}
  ],
  "algorithm_version": "v1.2",
  "generated_at": "2026-10-16T16:20:07Z",
  "expires_at": 1792772407
}
```

### 5.3 `product_realtime`

**Propósito:** datos en tiempo real de cada producto para su ficha: productos relacionados ("quienes vieron esto también vieron"), personas viéndolo ahora y unidades vendidas hoy.

**Eventos:** `product_view`, `add_to_cart` y el evento de venta (ver sección 8).

|Atributo|Tipo|Descripción|
|---|---|---|
|`product_id` (PK)|S|Producto|
|`related_products`|L|Top‑N de `{product_id, score}` vistos o agregados en la misma sesión|
|`related_window`|S|Ventana usada para el cálculo (ej. `7d`)|
|`related_updated_at`|S|Última actualización de relacionados|
|`viewing_now`|N|Usuarios distintos que lo vieron en los últimos minutos|
|`viewing_updated_at`|S|Última actualización de `viewing_now`|
|`sold_today`|N|Unidades vendidas en el día|
|`sold_date`|S|Día al que corresponde `sold_today` (`2026-10-16`)|

**Escritura:** cada job de Flink actualiza solo sus atributos con `UpdateItem … SET`, para no pisar los de otro job. La página ignora `sold_today` si `sold_date` no es el día actual.

**Acceso:** `GetItem` por `product_id`.

```json
{
  "product_id": "5e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
  "related_products": [
    {"product_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "score": 0.37},
    {"product_id": "4b5c6d7e-8f9a-4b0c-9d1e-2f3a4b5c6d7e", "score": 0.29}
  ],
  "related_window": "7d",
  "related_updated_at": "2026-10-16T16:00:00Z",
  "viewing_now": 14,
  "viewing_updated_at": "2026-10-16T16:20:00Z",
  "sold_today": 32,
  "sold_date": "2026-10-16"
}
```

### 5.4 `trending`

**Propósito:** rankings de productos y búsquedas populares, globales o por categoría.

**Eventos:** `product_view`, evento de venta, `search`.

|Atributo|Tipo|Descripción|
|---|---|---|
|`scope` (PK)|S|`GLOBAL`, `CATEGORY#<category_id>` o `SEARCH`|
|`window` (SK)|S|`1h` o `24h`|
|`items`|L|Lista ordenada de `{product_id, score, rank}`; en `SEARCH`, `{query, count, rank}`|
|`computed_at`|S|Fecha del cálculo|

**Acceso:** `GetItem` por `scope` + `window`.

```json
{
  "scope": "CATEGORY#c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "window": "24h",
  "items": [
    {"product_id": "5e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b", "score": 812, "rank":1},
    {"product_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "score": 640, "rank":2}
  ],
  "computed_at": "2026-10-16T16:15:00Z"
}
```

### 5.5 `checkout_sessions` (opcional)

**Propósito:** detectar abandono de checkout con un timer en Flink y mostrar un recordatorio ("¿olvidaste algo?"). Reemplaza al `checkout_abandoned` que emite el productor, que no sabe con certeza cuándo el usuario se fue.

**Eventos:** `checkout_started`, `checkout_shipping`, `checkout_payment` y el evento de venta.

|Atributo|Tipo|Descripción|
|---|---|---|
|`user_key` (PK)|S|`customer_id` o `anonymous_id`|
|`cart_id`|S|Carrito del checkout|
|`checkout_status`|S|`IN_PROGRESS`, `ABANDONED` o `COMPLETED`|
|`last_step`|S|Último evento `checkout_*` recibido|
|`started_at`|S|Fecha de `checkout_started`|
|`last_event_ts`|S|Fecha del último evento|
|`expires_at`|N|TTL: `last_event_ts` + 7 días|

**Acceso:** `GetItem` por `user_key`.

---

## 6. Tablas de seguridad y fraude

### 6.1 `risk_status`

**Propósito:** estado de riesgo vigente de una cuenta, una IP o un dispositivo. El backend lo consulta **antes** de validar la contraseña para decidir si exige CAPTCHA, MFA o bloquea el intento.

**Eventos:** `login` (exitosos y fallidos).

|Atributo|Tipo|Descripción|
|---|---|---|
|`entity` (PK)|S|`ACCOUNT#<login_identifier_hash>`, `IP#<ip_hash>` o `DEVICE#<device_id>`|
|`entity_type`|S|`ACCOUNT`, `IP` o `DEVICE`|
|`risk_level`|S|`LOW`, `MEDIUM` o `HIGH`|
|`action`|S|`NONE`, `CAPTCHA`, `MFA` o `BLOCK`|
|`reasons`|L|Reglas que se activaron (ver sección 7)|
|`failed_attempts`|N|Intentos fallidos en la ventana actual|
|`distinct_accounts`|N|Cuentas distintas intentadas (solo para `IP` y `DEVICE`)|
|`blocked_until`|S|Hasta cuándo aplica la acción|
|`updated_at`|S|Última actualización|
|`expires_at`|N|TTL: `blocked_until` + 24 horas|

**Acceso:** `BatchGetItem` con las tres llaves del intento (cuenta, IP, dispositivo). Se aplica la acción más restrictiva de las tres.

```json
{
  "entity": "IP#e3b0c44298fc1c149afbf4c8996fb924",
  "entity_type": "IP",
  "risk_level": "HIGH",
  "action": "BLOCK",
  "reasons": ["CREDENTIAL_STUFFING"],
  "failed_attempts": 57,
  "distinct_accounts": 23,
  "blocked_until": "2026-10-16T17:20:00Z",
  "updated_at": "2026-10-16T16:20:00Z",
  "expires_at": 1792257600
}
```

### 6.2 `order_risk`

**Propósito:** score de riesgo de cada orden, para retenerla o mandarla a revisión antes de despacharla.

**Eventos:** evento de venta, eventos de pago, `checkout_payment` y el `login` más reciente del cliente (desde el estado de Flink).

|Atributo|Tipo|Descripción|
|---|---|---|
|`order_id` (PK)|S|Orden (mismo UUID de Postgres)|
|`customer_id`|S|Cliente|
|`risk_score`|N|0 a 100|
|`decision`|S|`APPROVE`, `REVIEW` o `HOLD`|
|`reasons`|L|Reglas que se activaron|
|`order_amount`|N|Monto de la orden|
|`currency`|S|Moneda|
|`evaluated_at`|S|Fecha de evaluación|
|`expires_at`|N|TTL: `evaluated_at` + 90 días|

**Índice secundario:** `decision-index` (PK `decision`, SK `evaluated_at`) para que el panel interno liste la cola de órdenes en `REVIEW` u `HOLD`.

**Acceso:** `GetItem` por `order_id` desde el backend; `Query` sobre `decision-index` desde el panel.

```json
{
  "order_id": "d4e5f6a7-b8c9-4d0e-8f1a-2b3c4d5e6f7a",
  "customer_id": "9b1d6c2e-4f7a-4c1b-8e2d-1a2b3c4d5e6f",
  "risk_score": 78,
  "decision": "REVIEW",
  "reasons": ["NEW_DEVICE_PURCHASE", "AMOUNT_ABOVE_HISTORY"],
  "order_amount": 2450000,
  "currency": "COP",
  "evaluated_at": "2026-10-16T16:21:10Z",
  "expires_at": 1799943670
}
```

### 6.3 `security_alerts`

**Propósito:** registro de alertas de seguridad y fraude. La página lo usa para avisar al cliente ("¿fuiste tú?") y el equipo de soporte para revisarlas.

**Eventos:** todos los de `risk_status` y `order_risk`.

|Atributo|Tipo|Descripción|
|---|---|---|
|`customer_key` (PK)|S|`customer_id`; si la alerta no tiene cliente (ataque desde una IP), la `entity` (`IP#…`)|
|`sk` (SK)|S|`created_at#alert_id`|
|`alert_id`|S|UUID de la alerta|
|`alert_type`|S|`BRUTE_FORCE`, `CREDENTIAL_STUFFING`, `IMPOSSIBLE_TRAVEL`, `ACCOUNT_TAKEOVER`, `PAYMENT_ANOMALY`|
|`severity`|S|`LOW`, `MEDIUM` o `HIGH`|
|`status`|S|`OPEN`, `CONFIRMED` o `DISMISSED`|
|`entity`|S|Cuenta, IP o dispositivo involucrado|
|`order_id`|S|Orden relacionada, si aplica|
|`evidence`|M|Datos que activaron la regla (países, tiempos, conteos)|
|`created_at`|S|Fecha de la alerta|
|`expires_at`|N|TTL: `created_at` + 180 días|

**Índice secundario:** `status-index` (PK `status`, SK `created_at`) para listar alertas abiertas. En un sistema real convendría repartir esta PK (ej. `OPEN#<día>`) porque tiene pocos valores; para el alcance del proyecto basta así.

**Acceso:** `Query` por `customer_key` (alertas de un cliente) y `Query` sobre `status-index` (cola de soporte).

```json
{
  "customer_key": "9b1d6c2e-4f7a-4c1b-8e2d-1a2b3c4d5e6f",
  "sk": "2026-10-16T16:19:40Z#f1e2d3c4-b5a6-4978-8d9e-0f1a2b3c4d5e",
  "alert_id": "f1e2d3c4-b5a6-4978-8d9e-0f1a2b3c4d5e",
  "alert_type": "IMPOSSIBLE_TRAVEL",
  "severity": "HIGH",
  "status": "OPEN",
  "entity": "ACCOUNT#5d41402abc4b2a76b9719d911017c592",
  "evidence": {
    "previous_country": "CO",
    "previous_login_ts": "2026-10-16T15:50:02Z",
    "current_country": "RU",
    "minutes_between": 29
  },
  "created_at": "2026-10-16T16:19:40Z",
  "expires_at": 1807719580
}
```

---

## 7. Reglas de detección en Flink

Los umbrales son valores iniciales de ejemplo; se ajustan con los datos reales.

|Regla|Condición (ejemplo)|Entidad|Acción|Tablas|
|---|---|---|---|---|
|`BRUTE_FORCE`|5 o más logins fallidos sobre la misma cuenta en 15 min|`ACCOUNT`|`CAPTCHA`; desde 10, `BLOCK` por 30 min|`risk_status`, `security_alerts`|
|`CREDENTIAL_STUFFING`|Una IP o dispositivo intenta 10 o más cuentas distintas en 10 min|`IP`, `DEVICE`|`BLOCK` por 1 h|`risk_status`, `security_alerts`|
|`IMPOSSIBLE_TRAVEL`|Dos logins exitosos de la misma cuenta desde países distintos con menos de 2 h entre ellos|`ACCOUNT`|`MFA`|`risk_status`, `security_alerts`|
|`ACCOUNT_TAKEOVER`|Login desde dispositivo o país nuevo seguido de compra en menos de 30 min|`ACCOUNT`|Orden en `REVIEW`|`order_risk`, `security_alerts`|
|`PAYMENT_ANOMALY`|3 o más pagos fallidos seguidos de la misma cuenta en 30 min|`ACCOUNT`|Orden en `HOLD`|`order_risk`, `security_alerts`|
|`AMOUNT_ABOVE_HISTORY`|Monto de la orden mayor a 3 veces el promedio del cliente|—|Suma al `risk_score`|`order_risk`|

Flink guarda en su estado lo que estas reglas necesitan recordar: intentos por ventana, último país y fecha de login, dispositivos y países conocidos por cuenta, y el promedio de compra por cliente.

## 8. Requisitos sobre los eventos

Para que estas tablas funcionen, los eventos deben traer:

- **`login`:** `customer_id` (en exitosos), `anonymous_id`, `login_identifier_hash` (también en fallidos), `ip_hash`, `ip_country`, `device_id`, `success` y `failure_reason`. Sin `login_identifier_hash` no se pueden contar fallos por cuenta; sin `ip_hash` solo se detectan cambios de país.
- **`login` exitoso:** ambos IDs (`customer_id` y `anonymous_id`) para fusionar la sesión anónima.
- **Evento de venta único:** elegir `purchase` o `payment_success` como señal de venta confirmada, para que `sold_today` y `trending` no cuenten doble.
- **Eventos de pago:** `order_id`, `customer_id`, monto y resultado (exitoso o fallido).
- **`recommendation_impression` / `recommendation_click`:** con `algorithm_version`, para medir en Gold si las recomendaciones de `user_recommendations` funcionan.

## 9. Integración con el batch

- Las alertas (`security_alerts`) y las evaluaciones de órdenes (`order_risk`) también se publican desde Flink a un tópico de Pub/Sub (ej. `security-alerts`). Glue las lleva a Bronze en S3 como cualquier otro evento, y así se pueden analizar en BigQuery y Power BI sin consultar DynamoDB.
- Las demás tablas no se exportan: su información se puede reconstruir en batch a partir de los eventos crudos que ya llegan a S3.

## 10. Configuración de las tablas

|Tabla|Modo de capacidad|TTL (`expires_at`)|Índices secundarios|PITR|
|---|---|---|---|---|
|`user_recent_activity`|On-demand|Sí|—|No|
|`user_recommendations`|On-demand|Sí|—|No|
|`product_realtime`|On-demand|No|—|No|
|`trending`|On-demand|No|—|No|
|`checkout_sessions`|On-demand|Sí|—|No|
|`risk_status`|On-demand|Sí|—|Sí|
|`order_risk`|On-demand|Sí|`decision-index`|Sí|
|`security_alerts`|On-demand|Sí|`status-index`|Sí|

PITR (point-in-time recovery) se activa solo en las tablas de seguridad, porque las de recomendaciones se pueden recalcular desde los eventos.