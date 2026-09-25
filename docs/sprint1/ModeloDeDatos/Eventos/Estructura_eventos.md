# Estructura del Evento — Documentación

## Descripción general

Este documento describe el esquema estándar que deben seguir todos los eventos generados en la plataforma de e-commerce, tanto para el flujo de **procesamiento batch** como para el de **streaming**. El objetivo de esta estructura es tener un formato único, versionado y extensible que permita:

- Identificar de forma inequívoca cada evento (evitar duplicados).
- Enrutar el evento al pipeline correcto (batch, streaming o ambos).
- Reconstruir el recorrido de un usuario dentro de una sesión.
- Analizar comportamiento por dispositivo, canal y origen.
- Evolucionar el esquema en el tiempo sin romper eventos ya emitidos.

## Ejemplo de evento

```json
{
  "event_id": "evt_01JXYZ123",
  "event_type": "product_view",
  "event_version": 1,
  "event_time": "2026-08-24T16:30:25.123Z",
  "processing": {
    "targets": ["streaming", "batch"]
  },

  "customer": {
    "customer_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "anonymous_id": null
  },

  "session": {
    "session_id": "ses_98765"
  },
  
  "device": {
    "device_type": "mobile",
    "os": "Android",
    "browser": "Chrome"
  },

  "source": {
    "channel": "web",
    "page": "/products/123",
    "referrer": "/search?q=laptop"
  },

  "payload": {
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "category_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
  }
}
```

## Campos del evento

### 1. `event_id`
Identificador único del evento. Permite diferenciar cada acción realizada y evitar duplicados (idempotencia) en el procesamiento downstream.

- **Tipo:** `string`
- **Ejemplo:** `evt_01JXYZ123`

### 2. `event_type`
Indica qué acción ocurrió en el e-commerce. Es también el campo que el **router** usa para decidir si el evento va al flujo de streaming, batch o ambos (ver sección `processing`).

- **Tipo:** `string`
- **Ejemplos:** `product_view`, `add_to_cart`, `search`, `purchase`, `login`

### 3. `event_version`
Versión de la estructura del evento. Permite modificar el esquema en el futuro (agregar/quitar campos, cambiar tipos) sin romper la compatibilidad con eventos antiguos ya almacenados.

- **Tipo:** `integer`
- **Ejemplo:** `1`

### 4. `event_time`
Fecha y hora exacta en la que ocurrió el evento, en formato **ISO 8601 / UTC**.

- **Tipo:** `string` (timestamp ISO 8601)
- **Ejemplo:** `2026-08-24T16:30:25.123Z`

### 5. `processing`
Metadatos de enrutamiento que indican a qué pipeline(s) debe enviarse el evento.

| Campo     | Descripción                                           |
| --------- | ----------------------------------------------------- |
| `targets` | Arreglo con uno o ambos valores: `streaming`, `batch` |

**Ejemplo:**
```json
"processing": {
  "targets": ["streaming", "batch"]
}
```

### 6. `customer`
Información para identificar al usuario que generó el evento.

| Campo          | Descripción                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `customer_id`  | ID del usuario registrado. Corresponde exactamente a `users.user_id` (UUID) de la base de datos PostgreSQL. `null` si el usuario aún no ha iniciado sesión |
| `anonymous_id` | ID temporal asignado a usuarios anónimos, para poder seguir su comportamiento antes de que se registren o inicien sesión |


### 7. `session`
Identifica la sesión de navegación en la que ocurrió el evento.

| Campo        | Descripción                                         |
| ------------ | --------------------------------------------------- |
| `session_id` | Agrupa todos los eventos de una misma visita/sesión |

Permite reconstruir el recorrido del usuario dentro de una sesión, por ejemplo:

```
product_view -> add_to_cart -> checkout -> purchase
```

### 8. `device`
Información básica del dispositivo desde el que se generó el evento.

| Campo | Descripción | Ejemplos |
|---|---|---|
| `device_type` | Tipo de dispositivo | `mobile`, `desktop`, `tablet` |
| `os` | Sistema operativo | `Android`, `iOS`, `Windows` |
| `browser` | Navegador utilizado | `Chrome`, `Safari`, `Firefox` |

Sirve para analizar diferencias de comportamiento según el dispositivo desde el que se conecta el usuario.

### 9. `source`
Información sobre el contexto desde donde ocurrió la acción.

| Campo | Descripción |
|---|---|
| `channel` | Canal de origen: `web`, `app`, etc. |
| `page` | Página/ruta donde ocurrió el evento |
| `referrer` | Página o fuente desde la que llegó el usuario |

Esta sección puede ampliarse en el futuro con información de campañas de marketing (UTM, `campaign_id`, etc.) sin romper el esquema, gracias a `event_version`.

Permite analizar de dónde vienen los usuarios y cómo navegan por el sitio.

### 10. `payload`
Contiene los datos específicos de cada evento. Es la **única sección que cambia según `event_type`**; el resto de los campos (`event_id`, `customer`, `session`, `device`, `source`, etc.) son comunes a todos los eventos.

**Ejemplo — `product_view`:**
```json
"payload": {
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
}
```

> Nota: cada `event_type` (`add_to_cart`, `search`, `purchase`, `login`, etc.) tendrá su propio contrato de `payload`.

## Consideraciones de diseño

- **Identificadores compartidos con PostgreSQL:** todos los IDs de entidades de negocio que viajan en los eventos (`customer_id`, `product_id`, `variant_id`, `category_id`, `cart_id`, `order_id`) deben ser los mismos UUID que existen en la base de datos transaccional. Así los eventos se pueden cruzar directamente con las tablas de la tienda en la capa Silver sin tablas de mapeo. Los IDs propios del tracking (`event_id`, `session_id`, `anonymous_id`) no existen en Postgres y pueden conservar su formato con prefijo.
- **Idempotencia:** usar `event_id` como clave para deduplicar eventos tanto en Flink (streaming) como en los jobs de Glue (batch).
- **Evolución de esquema:** cualquier cambio estructural debe incrementar `event_version`, nunca reutilizar o eliminar campos existentes sin una estrategia de migración.
- **Usuarios anónimos vs. registrados:** `customer.anonymous_id` y `customer.customer_id` son mutuamente relevantes; conviene definir una regla clara de cuál prevalece cuando ambos están presentes (por ejemplo, tras un login durante la sesión).
- **Enrutamiento:** `processing.targets` desacopla la lógica de negocio (qué es el evento) de la lógica de infraestructura (a dónde va el evento), lo que facilita agregar nuevos destinos en el futuro sin tocar el productor del evento.