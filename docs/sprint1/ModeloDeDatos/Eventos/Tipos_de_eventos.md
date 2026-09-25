# Estructura de `payload` por `event_type`

## Descripción general

Este documento complementa la [documentación general de la estructura del evento](./estructura-evento.md) y detalla el contrato específico del campo `payload` para cada `event_type` manejado en la plataforma.

> **Convención de IDs:** los campos `product_id`, `variant_id`, `category_id`, `cart_id` y `order_id` contienen los mismos UUID de las tablas correspondientes en PostgreSQL (`products`, `product_variants`, `categories`, `carts`, `orders`), para permitir el cruce directo entre eventos y datos transaccionales.


---

## 1. Navegación

### 1.1 `page_view`
Se dispara cuando el usuario visita cualquier página del sitio.

`targets:` batch

| Campo       | Tipo     | Descripción                                                                   |
| ----------- | -------- | ----------------------------------------------------------------------------- |
| `page`      | `string` | Ruta de la página visitada                                                    |
| `page_type` | `string` | Tipo/categoría de la página (`home`, `category`, `product`, `checkout`, etc.) |

```json
{
  "page": "/home",
  "page_type": "home"
}
```

### 1.2 `category_view`
Se dispara cuando el usuario visita una categoría de productos.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `category_id` | `string` | ID de la categoría visitada |

```json
{
  "category_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
}
```

### 1.3 `product_view`
Se dispara cuando el usuario visita la ficha de un producto.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `product_id` | `string` | ID del producto visitado |
| `category_id` | `string` | ID de la categoría desde la que el usuario llegó al producto (contexto de navegación). `null` si llegó desde búsqueda, enlace directo u otra fuente sin categoría |

```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
}
```

> Un producto puede pertenecer a varias categorías (tabla `product_categories`). Este campo **no** representa todas sus categorías, solo el contexto de navegación; la relación completa producto–categorías se obtiene en Silver desde la base de datos.

### 1.4 `search`
Se dispara cuando el usuario realiza una búsqueda con resultados.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `query` | `string` | Texto ingresado por el usuario |
| `results_count` | `integer` | Cantidad de resultados obtenidos |

```json
{
  "query": "laptop gamer",
  "results_count": 15
}
```

### 1.5 `search_no_results`
Se dispara cuando una búsqueda no devuelve resultados. Útil para detectar demanda insatisfecha o gaps de catálogo.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `query` | `string` | Texto ingresado por el usuario |
| `results_count` | `integer` | Siempre `0` |

```json
{
  "query": "laptop gamer roja 32gb",
  "results_count": 0
}
```

---

## 2. Interacción con productos

### 2.1 `product_favorite`
Se dispara al agregar o quitar un producto de favoritos.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `product_id` | `string` | ID del producto |
| `action` | `string` | `add` o `remove` |

**Agregar a favoritos:**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "add"
}
```

**Quitar de favoritos:**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "remove"
}
```

### 2.2 `product_share`
Se dispara cuando el usuario comparte un producto.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `product_id` | `string` | ID del producto compartido |
| `platform` | `string` | Plataforma usada para compartir (`whatsapp`, `facebook`, `email`, etc.) |

```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "whatsapp"
}
```

---

## 3. Carrito

### 3.1 `add_to_cart`
Se dispara al agregar un producto al carrito.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `cart_id` | `string` | ID del carrito (`carts.cart_id`) |
| `product_id` | `string` | ID del producto agregado |
| `variant_id` | `string` | ID de la variante agregada (`product_variants.variant_id`): color, talla, etc. |
| `quantity` | `integer` | Cantidad agregada |
| `unit_price` | `number` | Precio unitario en el momento del evento |
| `currency` | `string` | Moneda (ISO 4217, ej. `COP`) |

```json
{
  "cart_id": "9b2e4f1a-3c5d-4e6f-8a7b-1c2d3e4f5a6b",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "variant_id": "a1b2c3d4-e5f6-4789-abcd-ef0123456789",
  "quantity": 2,
  "unit_price": 149.99,
  "currency": "COP"
}
```

### 3.2 `remove_from_cart`
Se dispara al quitar un producto (total o parcialmente) del carrito.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `cart_id` | `string` | ID del carrito (`carts.cart_id`) |
| `product_id` | `string` | ID del producto removido |
| `variant_id` | `string` | ID de la variante removida (`product_variants.variant_id`) |
| `quantity` | `integer` | Cantidad removida |

```json
{
  "cart_id": "9b2e4f1a-3c5d-4e6f-8a7b-1c2d3e4f5a6b",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "variant_id": "a1b2c3d4-e5f6-4789-abcd-ef0123456789",
  "quantity": 1
}
```

### 3.3 `cart_view`
Se dispara cuando el usuario visualiza el contenido de su carrito.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `cart_id` | `string` | ID del carrito |
| `items_count` | `integer` | Cantidad de ítems distintos en el carrito |
| `total_amount` | `number` | Valor total del carrito |
| `currency` | `string` | Moneda (ISO 4217) |

```json
{
  "cart_id": "9b2e4f1a-3c5d-4e6f-8a7b-1c2d3e4f5a6b",
  "items_count": 3,
  "total_amount": 429.97,
  "currency": "COP"
}
```

---

## 4. Checkout

### 4.1 `checkout_started`
Se dispara cuando el usuario inicia el proceso de checkout.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden en curso |
| `items_count` | `integer` | Cantidad de ítems en la orden |
| `total_amount` | `number` | Valor total de la orden |
| `currency` | `string` | Moneda (ISO 4217) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "items_count": 3,
  "total_amount": 429.97,
  "currency": "COP"
}
```

### 4.2 `checkout_shipping`
Se dispara cuando el usuario selecciona el método de envío.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden |
| `shipping_method` | `string` | Método de envío elegido (`standard`, `express`, etc.) |
| `shipping_cost` | `number` | Costo del envío |
| `currency` | `string` | Moneda (ISO 4217) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "shipping_method": "standard",
  "shipping_cost": 12000,
  "currency": "COP"
}
```

### 4.3 `checkout_payment`
Se dispara cuando el usuario selecciona el método de pago.

`targets:` batch

> ⚠️ **No se debe guardar información sensible del medio de pago** (número de tarjeta, CVV, fecha de expiración, etc.). Solo el método utilizado.

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden |
| `payment_method` | `string` | Método de pago elegido (`credit_card`, `pse`, `cash_on_delivery`, etc.) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method": "credit_card"
}
```

### 4.4 `checkout_abandoned`
Se dispara cuando el usuario abandona el checkout antes de completar la compra.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden abandonada |
| `step` | `string` | Paso del checkout en el que abandonó (`shipping`, `payment`, `review`, etc.) |
| `cart_value` | `number` | Valor del carrito al momento de abandonar |
| `currency` | `string` | Moneda (ISO 4217) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "step": "payment",
  "cart_value": 429.97,
  "currency": "COP"
}
```

> El campo `step` permite saber en qué parte del checkout abandonó el usuario, clave para análisis de fricción en el embudo de compra.

---

## 5. Compra y pagos

### 5.1 `purchase`
Uno de los eventos más importantes del sistema: confirma que la compra se completó.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden completada |
| `total_amount` | `number` | Valor total de la compra |
| `currency` | `string` | Moneda (ISO 4217) |
| `items` | `array` | Lista de ítems comprados |
| `items[].product_id` | `string` | ID del producto |
| `items[].variant_id` | `string` | ID de la variante comprada (`product_variants.variant_id`); equivale a `order_items.variant_id` |
| `items[].quantity` | `integer` | Cantidad comprada |
| `items[].unit_price` | `number` | Precio unitario en el momento de la compra |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "total_amount": 429.97,
  "currency": "COP",
  "items": [
    {
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "variant_id": "a1b2c3d4-e5f6-4789-abcd-ef0123456789",
      "quantity": 2,
      "unit_price": 149.99
    },
    {
      "product_id": "6fa459ea-ee8a-4ca4-894e-db77e160355e",
      "variant_id": "b2c3d4e5-f6a7-4890-bcde-f01234567890",
      "quantity": 1,
      "unit_price": 129.99
    }
  ]
}
```

### 5.2 `payment_success`
Se dispara cuando el pago de una orden se procesa exitosamente.

`targets:` batch, streaming

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden |
| `payment_method` | `string` | Método de pago utilizado |
| `amount` | `number` | Monto pagado |
| `currency` | `string` | Moneda (ISO 4217) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method": "credit_card",
  "amount": 429.97,
  "currency": "COP"
}
```

### 5.3 `payment_failed`
Se dispara cuando el pago de una orden falla.

`targets:` batch, streaming

> ⚠️ No se guardan datos sensibles del medio de pago (número de tarjeta, CVV, etc.).

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden |
| `payment_method` | `string` | Método de pago utilizado |
| `amount` | `number` | Monto que se intentó pagar |
| `currency` | `string` | Moneda (ISO 4217) |
| `error_code` | `string` | Código de error del fallo (`PAYMENT_DECLINED`, `INSUFFICIENT_FUNDS`, etc.) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method": "credit_card",
  "amount": 429.97,
  "currency": "COP",
  "error_code": "PAYMENT_DECLINED"
}
```

### 5.4 `order_cancelled`
Se dispara cuando una orden es cancelada (por el cliente o por el sistema).

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `order_id` | `string` | ID de la orden cancelada |
| `reason` | `string` | Motivo de la cancelación (`customer_request`, `out_of_stock`, `payment_failed`, etc.) |

```json
{
  "order_id": "2c1d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
  "reason": "customer_request"
}
```

---

## 6. Sesiones

### 6.1 `session_started`
Se dispara al iniciar una nueva sesión de navegación.
`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `landing_page` | `string` | Página por la que el usuario ingresó al sitio |

```json
{
  "landing_page": "/home"
}
```

### 6.2 `session_ended`
Se dispara al finalizar una sesión (cierre explícito o por inactividad/timeout). Es un evento agregado que resume la actividad de toda la sesión.

`targets:` batch

| Campo | Tipo | Descripción |
|---|---|---|
| `duration_seconds` | `integer` | Duración total de la sesión en segundos |
| `pages_viewed` | `integer` | Cantidad de páginas vistas durante la sesión |
| `products_viewed` | `integer` | Cantidad de productos distintos vistos |
| `items_added_to_cart` | `integer` | Cantidad de ítems agregados al carrito |
| `purchase_completed` | `boolean` | Indica si la sesión terminó en una compra completada |

```json
{
  "duration_seconds": 842,
  "pages_viewed": 12,
  "products_viewed": 5,
  "items_added_to_cart": 2,
  "purchase_completed": true
}
```

> Las métricas de este evento son calculadas por el productor. En la capa Silver se recalculan a partir de los eventos crudos de la sesión (agrupando por `session_id`), porque hay sesiones que no emiten `session_ended` (cierre del navegador, pérdida de conexión). El valor del productor se conserva como referencia para validación.

### 6.3 `login`

Se dispara cuando un usuario intenta iniciar sesión en el e-commerce. Es útil para analizar el comportamiento de acceso y detectar posibles intentos de acceso sospechosos. 

`targets:` batch, streaming

| **Campo**        | **Tipo**  | **Descripción**                                                                                                            |
| ---------------- | --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `login_method`   | `string`  | Método utilizado para iniciar sesión (`email`, `google`, etc.)                                                             |
| `success`        | `boolean` | Indica si el intento de inicio de sesión fue exitoso                                                                       |
| `ip_country`     | `string`  | País asociado a la dirección IP desde la que se realizó el intento                                                         |
| `failure_reason` | `string`  | Motivo del fallo si el inicio de sesión no fue exitoso (`invalid_password`, `account_locked`, etc.). `null` si fue exitoso |


```json
{
  "login_method": "email",
  "success": false,
  "ip_country": "CO",
  "failure_reason": "invalid_password"
}
```
---

## Resumen de `event_type` por grupo

| Grupo | `event_type` |
|---|---|
| Navegación | `page_view`, `category_view`, `product_view`, `search`, `search_no_results` |
| Interacción con productos | `product_favorite`, `product_share` |
| Carrito | `add_to_cart`, `remove_from_cart`, `cart_view` |
| Checkout | `checkout_started`, `checkout_shipping`, `checkout_payment`, `checkout_abandoned` |
| Compra y pagos | `purchase`, `payment_success`, `payment_failed`, `order_cancelled` |
| Sesiones | `session_started`, `session_ended`, `login` |

## Notas

- Todos los IDs de entidades de negocio son UUID compartidos con PostgreSQL (ver convención al inicio del documento).
- Los eventos de carrito y compra incluyen `variant_id` además de `product_id`, ya que en la base de datos `cart_items` y `order_items` se registran a nivel de variante.
- Todos los campos monetarios (`unit_price`, `total_amount`, `shipping_cost`, `amount`, `cart_value`) deben ir acompañados de su respectivo `currency` cuando apliquen, para evitar ambigüedades en agregaciones multi-moneda.
- Ningún `payload` debe contener información sensible de medios de pago (números de tarjeta, CVV, tokens de pasarela, etc.), como ya se indica en `checkout_payment` y `payment_failed`.