# Modelo de Datos - E-commerce

## 1. users

Representa a los clientes registrados.

| Campo | Tipo | Descripción |
|---|---|---|
| user_id | uuid | Identificador único del usuario |
| email | varchar(255) | Correo electrónico |
| password_hash | text | Contraseña almacenada como hash |
| first_name | varchar(100) | Nombre |
| last_name | varchar(100) | Apellido |
| phone | varchar(30) | Teléfono |
| birth_date | date | Fecha de nacimiento |
| gender | varchar(30) | Género, opcional |
| status | varchar(30) | active, inactive, blocked |
| created_at | timestamp | Fecha de creación |
| updated_at | timestamp | Última actualización |

**Útil para Batch:** segmentación de clientes, clientes nuevos vs. antiguos, frecuencia de compra, cohortes y análisis demográfico.

---

## 2. addresses

Permite almacenar varias direcciones por usuario.

| Campo | Tipo | Descripción |
|---|---|---|
| address_id | uuid | ID de la dirección |
| user_id | uuid | Usuario propietario |
| address_type | varchar(30) | shipping, billing |
| address_line | varchar(255) | Dirección |
| city | varchar(100) | Ciudad |
| state | varchar(100) | Departamento/estado |
| country | varchar(100) | País |
| postal_code | varchar(20) | Código postal |
| is_default | boolean | Dirección principal |
| created_at | timestamp | Fecha de creación |

**Batch:** ventas por ciudad, departamento, país y comportamiento geográfico.

---

## 3. categories

Categorías de productos.

| Campo | Tipo | Descripción |
|---|---|---|
| category_id | uuid | ID de categoría |
| name | varchar(100) | Nombre |
| parent_category_id | uuid | Categoría padre, opcional |
| created_at | timestamp | Fecha de creación |

El `parent_category_id` permite crear jerarquías:

```
Electrónica
 ├── Computadores
 │    ├── Laptops
 │    └── Desktop
 └── Celulares
```

**Batch:** ventas por categoría, subcategoría y rentabilidad por línea de producto.

---

## 4. products

Información principal del producto.

| Campo | Tipo | Descripción |
|---|---|---|
| product_id | uuid | ID del producto |
| name | varchar(255) | Nombre |
| description | text | Descripción |
| brand | varchar(100) | Marca |
| base_price | numeric(12,2) | Precio base |
| cost_price | numeric(12,2) | Costo |
| status | varchar(30) | active, inactive, discontinued |
| created_at | timestamp | Fecha de creación |
| updated_at | timestamp | Última actualización |

Tener `cost_price` es especialmente interesante porque permite calcular posteriormente:

```
ingresos
- costo
= margen bruto
```

---

## 5. product_variants

Muy útil si quieren simular un e-commerce real.

Un producto puede tener diferentes colores, tallas, capacidades, etc.

| Campo | Tipo | Descripción |
|---|---|---|
| variant_id | uuid | ID de variante |
| product_id | uuid | Producto |
| sku | varchar(100) | SKU |
| color | varchar(50) | Color |
| size | varchar(50) | Talla |
| price | numeric(12,2) | Precio de la variante |
| status | varchar(30) | Estado |
| created_at | timestamp | Fecha de creación |

**Batch:** productos más vendidos por variante, color o talla y variantes con baja rotación.

---

## 6. product_categories

Relación muchos-a-muchos entre productos y categorías.

| Campo | Tipo | Descripción |
|---|---|---|
| product_id | uuid | Producto |
| category_id | uuid | Categoría |

PK compuesta:

```
(product_id, category_id)
```

Esto permite que un producto pertenezca a múltiples categorías.

---

## 7. product_inventory

Inventario actual y movimientos de stock.

| Campo | Tipo | Descripción |
|---|---|---|
| inventory_id | uuid | ID |
| variant_id | uuid | Variante |
| warehouse | varchar(100) | Bodega |
| quantity_available | integer | Stock disponible |
| quantity_reserved | integer | Stock reservado |
| reorder_level | integer | Nivel para reposición |
| updated_at | timestamp | Última actualización |

**Batch:** productos agotados, productos próximos a agotarse, rotación de inventario y análisis de demanda.

---

## 8. orders

Es probablemente la tabla central del modelo.

| Campo | Tipo | Descripción |
|---|---|---|
| order_id | uuid | ID de orden |
| user_id | uuid | Cliente |
| shipping_address_id | uuid | Dirección de envío |
| billing_address_id | uuid | Dirección de facturación |
| status | varchar(30) | Estado |
| subtotal | numeric(12,2) | Subtotal |
| discount_amount | numeric(12,2) | Descuento |
| tax_amount | numeric(12,2) | Impuestos |
| shipping_amount | numeric(12,2) | Envío |
| total_amount | numeric(12,2) | Total |
| currency | varchar(3) | Moneda |
| created_at | timestamp | Fecha de creación |
| updated_at | timestamp | Fecha de actualización |

Estados posibles:

- pending
- confirmed
- processing
- shipped
- delivered
- cancelled
- refunded

**Batch:** ventas diarias, ingresos, ticket promedio, cancelaciones, clientes recurrentes, etc.

---

## 9. order_items

Detalle de cada orden.

| Campo | Tipo | Descripción |
|---|---|---|
| order_item_id | uuid | ID |
| order_id | uuid | Orden |
| variant_id | uuid | Producto comprado |
| quantity | integer | Cantidad |
| unit_price | numeric(12,2) | Precio unitario |
| discount_amount | numeric(12,2) | Descuento |
| tax_amount | numeric(12,2) | Impuesto |
| subtotal | numeric(12,2) | Subtotal |
| created_at | timestamp | Fecha |

Esta tabla es fundamental para Batch porque permite bajar desde:

```
orden
   ↓
producto
   ↓
categoría
   ↓
marca
```

y construir métricas muy detalladas.

---

## 10. payments

Pagos asociados a órdenes.

| Campo | Tipo | Descripción |
|---|---|---|
| payment_id | uuid | ID |
| order_id | uuid | Orden |
| payment_method | varchar(50) | Tarjeta, PSE, PayPal, etc. |
| status | varchar(30) | pending, approved, failed, refunded |
| amount | numeric(12,2) | Valor |
| transaction_reference | varchar(150) | Referencia externa |
| paid_at | timestamp | Fecha del pago |
| created_at | timestamp | Fecha de creación |

**Batch:** tasa de pagos fallidos, ingresos por método de pago, valor procesado, reembolsos.

---


## 11. carts

Carritos de compra.

| Campo | Tipo | Descripción |
|---|---|---|
| cart_id | uuid | ID |
| user_id | uuid | Usuario |
| status | varchar(30) | active, converted, abandoned, expired |
| created_at | timestamp | Creación |
| updated_at | timestamp | Última actualización |

---

## 12. cart_items

Productos agregados al carrito.

| Campo | Tipo | Descripción |
|---|---|---|
| cart_item_id | uuid | ID |
| cart_id | uuid | Carrito |
| variant_id | uuid | Producto |
| quantity | integer | Cantidad |
| unit_price | numeric(12,2) | Precio |
| added_at | timestamp | Momento de adición |
| removed_at | timestamp | Momento de eliminación |

Esto permite algo muy interesante para Batch:

```
producto agregado al carrito
        ↓
¿terminó en una orden?
```

Así pueden calcular abandono de carrito por producto.

---

## 13. product_reviews

Reseñas de productos.

| Campo | Tipo | Descripción |
|---|---|---|
| review_id | uuid | ID |
| user_id | uuid | Usuario |
| product_id | uuid | Producto |
| order_id | uuid | Orden relacionada |
| rating | integer | 1–5 |
| title | varchar(255) | Título |
| comment | text | Comentario |
| created_at | timestamp | Fecha |

**Batch:** rating promedio, productos con mala percepción, relación entre rating y ventas.

---

## 14. Consideraciones para la ingesta hacia S3

### 14.1 Relación con los eventos

Los eventos web y de login usan los mismos UUID de este modelo (`customer_id` = `users.user_id`, `product_id`, `variant_id`, `category_id`, `cart_id`, `order_id`), lo que permite cruzarlos directamente en la capa Silver.

### 14.2 Estrategia de extracción por tabla

La carga incremental se basa en `updated_at`. Las tablas que no tienen ese campo se extraen por `created_at` cuando sus registros nunca se modifican, o con carga completa cuando sí pueden cambiar.

| Tabla | Estrategia | Campo de control | Motivo |
|---|---|---|---|
| users | Incremental | `updated_at` | Tiene fecha de actualización |
| addresses | Completa | — | Los registros pueden editarse y no tiene `updated_at` |
| categories | Completa | — | Tabla pequeña, sin `updated_at` |
| products | Incremental | `updated_at` | Tiene fecha de actualización |
| product_variants | Completa | — | El precio y el estado cambian y no tiene `updated_at` |
| product_categories | Completa | — | Tabla de relación sin fechas |
| product_inventory | Incremental | `updated_at` | Tiene fecha de actualización |
| orders | Incremental | `updated_at` | El estado de la orden cambia en el tiempo |
| order_items | Incremental (solo inserción) | `created_at` | El detalle de una orden no se modifica |
| payments | Completa | — | El `status` cambia (approved, refunded) y no tiene `updated_at` |
| carts | Incremental | `updated_at` | Tiene fecha de actualización |
| cart_items | Incremental | `GREATEST(added_at, removed_at)` | El registro cambia cuando se llena `removed_at` |
| product_reviews | Incremental (solo inserción) | `created_at` | Las reseñas no se modifican |

> **Pendiente recomendado:** agregar `updated_at` a `payments`, `product_variants` y `addresses` permitiría pasarlas a carga incremental cuando el volumen crezca.

### 14.3 Datos sensibles

| Campo | Tratamiento |
|---|---|
| `users.password_hash` | **No se extrae.** Se excluye desde la consulta de origen; no llega a ninguna capa de S3 |
| `users.email`, `users.phone` | Se almacenan en Bronze tal como vienen y se enmascaran o reemplazan por hash en Silver |
| `users.birth_date` | Se transforma en Silver a rango de edad para análisis demográfico |
| `addresses.address_line` | Se excluye en Silver; para análisis geográfico basta con `city`, `state` y `country` |
| `payments.transaction_reference` | Se conserva solo para conciliación; no se expone en Gold |