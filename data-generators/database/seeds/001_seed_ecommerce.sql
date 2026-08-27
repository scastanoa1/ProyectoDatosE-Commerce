-- ============================================================
-- SEED / DATA GENERATOR - ECOMMERCE
-- PostgreSQL
-- ============================================================
--
-- Requisito:
-- Ejecutar primero el script de creación de tablas.
--
-- El script genera datos coherentes para:
--   users
--   addresses
--   categories
--   products
--   product_variants
--   product_categories
--   product_inventory
--   orders
--   order_items
--   payments
--   carts
--   cart_items
--   product_reviews
--
-- ============================================================


-- ============================================================
-- 0. LIMPIAR DATOS EXISTENTES
-- ============================================================

\c ecommerce;

TRUNCATE TABLE
    product_reviews,
    cart_items,
    carts,
    payments,
    order_items,
    orders,
    product_inventory,
    product_categories,
    product_variants,
    products,
    categories,
    addresses,
    users
RESTART IDENTITY CASCADE;


-- ============================================================
-- 1. USERS
-- ============================================================

INSERT INTO users (
    user_id,
    email,
    password_hash,
    first_name,
    last_name,
    phone,
    birth_date,
    gender,
    status,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    'user' || gs || '@example.com',
    crypt('Password123!', gen_salt('bf')),
    (
        ARRAY[
            'Carlos',
            'Maria',
            'Juan',
            'Laura',
            'Andres',
            'Sofia',
            'Daniel',
            'Valentina',
            'Sebastian',
            'Camila',
            'Mateo',
            'Isabella',
            'Nicolas',
            'Gabriela',
            'Felipe'
        ]
    )[1 + floor(random() * 15)::int],
    (
        ARRAY[
            'Gomez',
            'Rodriguez',
            'Martinez',
            'Lopez',
            'Garcia',
            'Perez',
            'Sanchez',
            'Ramirez',
            'Torres',
            'Vargas',
            'Castro',
            'Morales'
        ]
    )[1 + floor(random() * 12)::int],
    '+57 3' || floor(random() * 100000000)::bigint,
    DATE '1970-01-01' + floor(random() * 13000)::int,
    (
        ARRAY[
            'male',
            'female'
        ]
    )[1 + floor(random() * 2)::int],
    CASE
        WHEN random() < 0.94 THEN 'active'
        WHEN random() < 0.98 THEN 'inactive'
        ELSE 'blocked'
    END,
    CURRENT_TIMESTAMP
        - (floor(random() * 730)::int || ' days')::interval,
    CURRENT_TIMESTAMP
FROM generate_series(1, 1000) gs;


-- ============================================================
-- 2. ADDRESSES
-- ============================================================

INSERT INTO addresses (
    address_id,
    user_id,
    address_type,
    address_line,
    city,
    state,
    country,
    postal_code,
    is_default,
    created_at
)
SELECT
    gen_random_uuid(),
    u.user_id,
    CASE
        WHEN gs % 2 = 0 THEN 'shipping'
        ELSE 'billing'
    END,
    (
        ARRAY[
            'Carrera 43A # 10-15',
            'Calle 10 # 34-25',
            'Carrera 7 # 72-41',
            'Calle 80 # 15-30',
            'Carrera 27 # 48-20',
            'Calle 45 # 20-10',
            'Carrera 53 # 80-60',
            'Calle 93 # 14-50'
        ]
    )[1 + floor(random() * 8)::int],
    location_data.city,
    location_data.state,
    'Colombia',
    location_data.postal_code,
    true,
    u.created_at + (floor(random() * 30)::int || ' days')::interval
FROM users u
CROSS JOIN LATERAL (
    SELECT *
    FROM (
        VALUES
            ('Medellin', 'Antioquia', '050001'),
            ('Bogota', 'Cundinamarca', '110111'),
            ('Cali', 'Valle del Cauca', '760001'),
            ('Barranquilla', 'Atlantico', '080001'),
            ('Cartagena', 'Bolivar', '130001'),
            ('Bucaramanga', 'Santander', '680001'),
            ('Pereira', 'Risaralda', '660001'),
            ('Manizales', 'Caldas', '170001')
    ) AS locations(city, state, postal_code)
    ORDER BY random()
    LIMIT 1
) location_data
CROSS JOIN LATERAL (
    SELECT floor(random() * 2)::int AS gs
) x;


-- ============================================================
-- 3. CATEGORIES
-- ============================================================

INSERT INTO categories (
    category_id,
    name,
    parent_category_id
)
VALUES
    (gen_random_uuid(), 'Electronica', NULL),
    (gen_random_uuid(), 'Hogar', NULL),
    (gen_random_uuid(), 'Ropa', NULL),
    (gen_random_uuid(), 'Deportes', NULL),
    (gen_random_uuid(), 'Belleza', NULL),
    (gen_random_uuid(), 'Videojuegos', NULL);


-- Subcategorias
INSERT INTO categories (
    category_id,
    name,
    parent_category_id
)
SELECT
    gen_random_uuid(),
    sub.name,
    c.category_id
FROM categories c
JOIN (
    VALUES
        ('Electronica', 'Celulares'),
        ('Electronica', 'Computadores'),
        ('Electronica', 'Audio'),
        ('Electronica', 'Accesorios'),
        ('Hogar', 'Cocina'),
        ('Hogar', 'Muebles'),
        ('Hogar', 'Electrodomesticos'),
        ('Ropa', 'Camisetas'),
        ('Ropa', 'Pantalones'),
        ('Ropa', 'Calzado'),
        ('Deportes', 'Fitness'),
        ('Deportes', 'Futbol'),
        ('Deportes', 'Ciclismo'),
        ('Belleza', 'Cuidado facial'),
        ('Belleza', 'Cuidado corporal'),
        ('Videojuegos', 'Consolas'),
        ('Videojuegos', 'Juegos')
) AS sub(parent_name, name)
    ON c.name = sub.parent_name;


-- ============================================================
-- 4. PRODUCTS
-- ============================================================

INSERT INTO products (
    product_id,
    name,
    description,
    brand,
    base_price,
    cost_price,
    status,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    p.name,
    p.description,
    p.brand,
    p.price,
    ROUND((p.price * p.cost_percentage)::numeric, 2),
    'active',
    CURRENT_TIMESTAMP - (floor(random() * 365)::int || ' days')::interval,
    CURRENT_TIMESTAMP
FROM (
    VALUES
        ('iPhone 15', 'Smartphone Apple de 128GB', 'Apple', 3499000, 0.72),
        ('Samsung Galaxy S24', 'Smartphone Samsung gama alta', 'Samsung', 3199000, 0.70),
        ('Xiaomi Redmi Note 13', 'Smartphone Xiaomi de gama media', 'Xiaomi', 899000, 0.68),
        ('MacBook Air M3', 'Portatil Apple con chip M3', 'Apple', 5999000, 0.73),
        ('Dell Inspiron 15', 'Portatil Dell para trabajo y estudio', 'Dell', 2899000, 0.72),
        ('Lenovo IdeaPad 3', 'Portatil Lenovo de uso general', 'Lenovo', 2199000, 0.71),
        ('Sony WH-1000XM5', 'Audifonos inalambricos con cancelacion de ruido', 'Sony', 1599000, 0.69),
        ('AirPods Pro 2', 'Audifonos Apple con cancelacion de ruido', 'Apple', 1099000, 0.70),
        ('JBL Flip 6', 'Parlante Bluetooth portatil', 'JBL', 599000, 0.67),
        ('Logitech MX Master 3S', 'Mouse ergonomico inalambrico', 'Logitech', 449000, 0.65),
        ('Teclado Logitech K380', 'Teclado Bluetooth compacto', 'Logitech', 189000, 0.64),
        ('Monitor LG 27 pulgadas', 'Monitor IPS Full HD', 'LG', 899000, 0.71),
        ('Camiseta Nike Sportswear', 'Camiseta deportiva de algodon', 'Nike', 149000, 0.55),
        ('Tenis Adidas Runfalcon', 'Tenis deportivos para running', 'Adidas', 299000, 0.58),
        ('Chaqueta North Face', 'Chaqueta impermeable para exteriores', 'The North Face', 699000, 0.62),
        ('Jeans Levi Strauss', 'Jeans clasicos de corte recto', 'Levis', 249000, 0.57),
        ('Xbox Series X', 'Consola de videojuegos Microsoft', 'Microsoft', 2599000, 0.76),
        ('PlayStation 5 Slim', 'Consola Sony PlayStation 5 Slim', 'Sony', 2699000, 0.77),
        ('Nintendo Switch OLED', 'Consola portatil Nintendo', 'Nintendo', 1799000, 0.74),
        ('FIFA 26', 'Videojuego de futbol', 'EA Sports', 299000, 0.62),
        ('Control Xbox Wireless', 'Control inalambrico para Xbox', 'Microsoft', 299000, 0.63),
        ('Proteina Whey 2kg', 'Suplemento de proteina', 'Optimum Nutrition', 249000, 0.65),
        ('Mat de Yoga', 'Mat antideslizante para yoga', 'Everlast', 119000, 0.55),
        ('Balon Adidas Mundial', 'Balon oficial de futbol', 'Adidas', 179000, 0.58),
        ('Licuadora Oster', 'Licuadora de alta potencia', 'Oster', 399000, 0.66),
        ('Cafetera Nespresso', 'Cafetera automatica de capsulas', 'Nespresso', 799000, 0.69),
        ('Sofa 3 puestos', 'Sofa moderno de tres puestos', 'Home Collection', 2199000, 0.70),
        ('Set de sartenes', 'Set de 3 sartenes antiadherentes', 'Tramontina', 249000, 0.61),
        ('Kit cuidado facial', 'Kit de limpieza e hidratacion facial', 'Neutrogena', 129000, 0.57),
        ('Perfume Eros 100ml', 'Perfume masculino', 'Versace', 499000, 0.65)
) AS p(name, description, brand, price, cost_percentage);


-- ============================================================
-- 5. PRODUCT VARIANTS
-- ============================================================

INSERT INTO product_variants (
    variant_id,
    product_id,
    sku,
    color,
    size,
    price,
    status
)
SELECT
    gen_random_uuid(),
    p.product_id,
    'SKU-' || LPAD(row_number() OVER ()::text, 6, '0'),
    v.color,
    v.size,
    p.base_price + v.price_adjustment,
    'active'
FROM products p
CROSS JOIN LATERAL (
    VALUES
        ('Negro', NULL::varchar, 0),
        ('Blanco', NULL::varchar, 0)
) v(color, size, price_adjustment)
WHERE p.name IN (
    'iPhone 15',
    'Samsung Galaxy S24',
    'Xiaomi Redmi Note 13',
    'MacBook Air M3',
    'Dell Inspiron 15',
    'Sony WH-1000XM5',
    'AirPods Pro 2',
    'JBL Flip 6',
    'Logitech MX Master 3S',
    'Teclado Logitech K380',
    'Monitor LG 27 pulgadas',
    'Xbox Series X',
    'PlayStation 5 Slim',
    'Nintendo Switch OLED',
    'Control Xbox Wireless',
    'Licuadora Oster',
    'Cafetera Nespresso'
)

UNION ALL

SELECT
    gen_random_uuid(),
    p.product_id,
    'SKU-' || LPAD((10000 + row_number() OVER ())::text, 6, '0'),
    v.color,
    v.size,
    p.base_price,
    'active'
FROM products p
CROSS JOIN LATERAL (
    VALUES
        ('Negro', 'S'),
        ('Negro', 'M'),
        ('Negro', 'L'),
        ('Azul', 'S'),
        ('Azul', 'M'),
        ('Azul', 'L')
) v(color, size)
WHERE p.name IN (
    'Camiseta Nike Sportswear',
    'Tenis Adidas Runfalcon',
    'Chaqueta North Face',
    'Jeans Levi Strauss'
)

UNION ALL

SELECT
    gen_random_uuid(),
    p.product_id,
    'SKU-' || LPAD((20000 + row_number() OVER ())::text, 6, '0'),
    NULL,
    NULL,
    p.base_price,
    'active'
FROM products p
WHERE p.name IN (
    'FIFA 26',
    'Proteina Whey 2kg',
    'Mat de Yoga',
    'Balon Adidas Mundial',
    'Sofa 3 puestos',
    'Set de sartenes',
    'Kit cuidado facial',
    'Perfume Eros 100ml'
);


-- ============================================================
-- 6. PRODUCT CATEGORIES
-- ============================================================

INSERT INTO product_categories (
    product_id,
    category_id
)
SELECT DISTINCT
    p.product_id,
    c.category_id
FROM products p
JOIN categories c
    ON (
        (p.name IN (
            'iPhone 15',
            'Samsung Galaxy S24',
            'Xiaomi Redmi Note 13'
        ) AND c.name = 'Celulares')

        OR

        (p.name IN (
            'MacBook Air M3',
            'Dell Inspiron 15',
            'Lenovo IdeaPad 3'
        ) AND c.name = 'Computadores')

        OR

        (p.name IN (
            'Sony WH-1000XM5',
            'AirPods Pro 2',
            'JBL Flip 6'
        ) AND c.name = 'Audio')

        OR

        (p.name IN (
            'Logitech MX Master 3S',
            'Teclado Logitech K380',
            'Monitor LG 27 pulgadas'
        ) AND c.name = 'Accesorios')

        OR

        (p.name IN (
            'Camiseta Nike Sportswear'
        ) AND c.name = 'Camisetas')

        OR

        (p.name IN (
            'Tenis Adidas Runfalcon'
        ) AND c.name = 'Calzado')

        OR

        (p.name IN (
            'Chaqueta North Face',
            'Jeans Levi Strauss'
        ) AND c.name = 'Ropa')

        OR

        (p.name IN (
            'Xbox Series X',
            'PlayStation 5 Slim',
            'Nintendo Switch OLED'
        ) AND c.name = 'Consolas')

        OR

        (p.name IN (
            'FIFA 26',
            'Control Xbox Wireless'
        ) AND c.name = 'Juegos')

        OR

        (p.name IN (
            'Proteina Whey 2kg',
            'Mat de Yoga'
        ) AND c.name = 'Fitness')

        OR

        (p.name IN (
            'Balon Adidas Mundial'
        ) AND c.name = 'Futbol')

        OR

        (p.name IN (
            'Licuadora Oster',
            'Cafetera Nespresso',
            'Set de sartenes'
        ) AND c.name = 'Cocina')

        OR

        (p.name IN (
            'Sofa 3 puestos'
        ) AND c.name = 'Muebles')

        OR

        (p.name IN (
            'Kit cuidado facial',
            'Perfume Eros 100ml'
        ) AND c.name = 'Cuidado facial')
    );


-- ============================================================
-- 7. PRODUCT INVENTORY
-- ============================================================

INSERT INTO product_inventory (
    inventory_id,
    variant_id,
    warehouse,
    quantity_available,
    quantity_reserved,
    reorder_level,
    updated_at
)
SELECT
    gen_random_uuid(),
    pv.variant_id,
    w.warehouse,
    CASE
        WHEN random() < 0.08 THEN floor(random() * 10)::int
        WHEN random() < 0.20 THEN floor(random() * 30)::int
        ELSE floor(random() * 150 + 30)::int
    END,
    floor(random() * 10)::int,
    CASE
        WHEN random() < 0.5 THEN 20
        ELSE 50
    END,
    CURRENT_TIMESTAMP
FROM product_variants pv
CROSS JOIN (
    VALUES
        ('Bogota'),
        ('Medellin'),
        ('Cali')
) w(warehouse);


-- ============================================================
-- 8. ORDERS
-- ============================================================

INSERT INTO orders (
    order_id,
    user_id,
    shipping_address_id,
    billing_address_id,
    status,
    subtotal,
    discount_amount,
    tax_amount,
    shipping_amount,
    total_amount,
    currency,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    u.user_id,
    a.address_id,
    a.address_id,
    status_data.status,
    0,
    0,
    0,
    CASE
        WHEN random() < 0.75 THEN 0
        ELSE 15900
    END,
    0,
    'COP',
    order_date,
    order_date
FROM (
    SELECT
        u.user_id,
        (ARRAY_AGG(a.address_id))[1] AS address_id,
        gs,
        CURRENT_TIMESTAMP
            - (floor(random() * 180)::int || ' days')::interval
            - (floor(random() * 24)::int || ' hours')::interval AS order_date
    FROM users u
    JOIN addresses a
        ON a.user_id = u.user_id
    CROSS JOIN generate_series(1, 5) gs
    GROUP BY u.user_id
) data
JOIN users u
    ON u.user_id = data.user_id
JOIN addresses a
    ON a.address_id = data.address_id
CROSS JOIN LATERAL (
    SELECT
        CASE
            WHEN random() < 0.05 THEN 'cancelled'
            WHEN random() < 0.10 THEN 'pending'
            WHEN random() < 0.20 THEN 'confirmed'
            WHEN random() < 0.30 THEN 'processing'
            WHEN random() < 0.45 THEN 'shipped'
            ELSE 'delivered'
        END AS status
) status_data
ORDER BY random();


-- ============================================================
-- 9. ORDER ITEMS
-- ============================================================

INSERT INTO order_items (
    order_item_id,
    order_id,
    variant_id,
    quantity,
    unit_price,
    discount_amount,
    tax_amount,
    subtotal,
    created_at
)
SELECT
    gen_random_uuid(),
    o.order_id,
    pv.variant_id,
    item.quantity,
    pv.price,
    item.discount_amount,
    item.tax_amount,
    (
        item.quantity * pv.price
        - item.discount_amount
        + item.tax_amount
    ),
    o.created_at
FROM orders o
CROSS JOIN LATERAL (
    SELECT
        pv.variant_id,
        floor(random() * 3 + 1)::int AS quantity,
        ROUND(
            (
                pv.price
                * CASE
                    WHEN random() < 0.15 THEN random() * 0.15
                    ELSE 0
                  END
            )::numeric,
            2
        ) AS discount_amount,
        0::numeric AS tax_amount
    FROM product_variants pv
    ORDER BY random()
    LIMIT (
        CASE
            WHEN random() < 0.65 THEN 1
            WHEN random() < 0.90 THEN 2
            ELSE 3
        END
    )
) item
JOIN product_variants pv
    ON pv.variant_id = item.variant_id;


-- ============================================================
-- 10. ACTUALIZAR TOTALES DE ORDERS
-- ============================================================

UPDATE orders o
SET
    subtotal = totals.subtotal,
    discount_amount = totals.discount_amount,
    tax_amount = totals.tax_amount,
    total_amount =
        totals.subtotal
        - totals.discount_amount
        + totals.tax_amount
        + o.shipping_amount,
    updated_at = CURRENT_TIMESTAMP
FROM (
    SELECT
        oi.order_id,
        SUM(oi.quantity * oi.unit_price) AS subtotal,
        SUM(oi.discount_amount) AS discount_amount,
        SUM(oi.tax_amount) AS tax_amount
    FROM order_items oi
    GROUP BY oi.order_id
) totals
WHERE o.order_id = totals.order_id;


-- ============================================================
-- 11. PAYMENTS
-- ============================================================

INSERT INTO payments (
    payment_id,
    order_id,
    payment_method,
    status,
    amount,
    transaction_reference,
    paid_at,
    created_at
)
SELECT
    gen_random_uuid(),
    o.order_id,
    payment_data.payment_method,
    CASE
        WHEN o.status = 'cancelled'
            THEN 'failed'

        WHEN random() < 0.04
            THEN 'failed'

        WHEN o.status = 'pending'
            THEN 'pending'

        ELSE 'approved'
    END,
    o.total_amount,
    'TXN-' || UPPER(REPLACE(gen_random_uuid()::text, '-', '')),
    CASE
        WHEN o.status IN (
            'confirmed',
            'processing',
            'shipped',
            'delivered'
        )
        THEN o.created_at + INTERVAL '15 minutes'
        ELSE NULL
    END,
    o.created_at
FROM orders o
CROSS JOIN LATERAL (
    SELECT
        (
            ARRAY[
                'credit_card',
                'debit_card',
                'pse',
                'paypal',
                'bank_transfer'
            ]
        )[1 + floor(random() * 5)::int] AS payment_method
) payment_data;


-- ============================================================
-- 12. CARTS
-- ============================================================

INSERT INTO carts (
    cart_id,
    user_id,
    status,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    u.user_id,
    CASE
        WHEN random() < 0.30 THEN 'abandoned'
        WHEN random() < 0.50 THEN 'converted'
        WHEN random() < 0.85 THEN 'active'
        ELSE 'expired'
    END,
    CURRENT_TIMESTAMP - (floor(random() * 90)::int || ' days')::interval,
    CURRENT_TIMESTAMP - (floor(random() * 10)::int || ' days')::interval
FROM users u
CROSS JOIN generate_series(1, 2);


-- ============================================================
-- 13. CART ITEMS
-- ============================================================

INSERT INTO cart_items (
    cart_item_id,
    cart_id,
    variant_id,
    quantity,
    unit_price,
    added_at,
    removed_at
)
SELECT
    gen_random_uuid(),
    c.cart_id,
    pv.variant_id,
    floor(random() * 3 + 1)::int,
    pv.price,
    c.created_at + (floor(random() * 48)::int || ' hours')::interval,
    CASE
        WHEN c.status IN ('abandoned', 'expired')
            THEN c.updated_at
        ELSE NULL
    END
FROM carts c
CROSS JOIN LATERAL (
    SELECT variant_id, price
    FROM product_variants
    ORDER BY random()
    LIMIT (
        CASE
            WHEN random() < 0.60 THEN 1
            WHEN random() < 0.90 THEN 2
            ELSE 3
        END
    )
) pv;


-- ============================================================
-- 14. PRODUCT REVIEWS
-- ============================================================

INSERT INTO product_reviews (
    review_id,
    user_id,
    product_id,
    order_id,
    rating,
    title,
    comment,
    created_at
)
SELECT
    gen_random_uuid(),
    o.user_id,
    p.product_id,
    o.order_id,
    review_data.rating,
    review_data.title,
    review_data.comment,
    o.created_at + (floor(random() * 20)::int || ' days')::interval
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.order_id
JOIN product_variants pv
    ON pv.variant_id = oi.variant_id
JOIN products p
    ON p.product_id = pv.product_id
CROSS JOIN LATERAL (
    SELECT
        CASE
            WHEN random() < 0.08 THEN 1
            WHEN random() < 0.18 THEN 2
            WHEN random() < 0.35 THEN 3
            WHEN random() < 0.70 THEN 4
            ELSE 5
        END AS rating,

        CASE
            WHEN random() < 0.50 THEN 'Muy buen producto'
            WHEN random() < 0.75 THEN 'Buena relacion calidad precio'
            WHEN random() < 0.90 THEN 'Cumple con lo esperado'
            ELSE 'Podria mejorar'
        END AS title,

        CASE
            WHEN random() < 0.50 THEN
                'El producto llego en buen estado y funciona correctamente.'
            WHEN random() < 0.75 THEN
                'La calidad es buena y la entrega fue rapida.'
            WHEN random() < 0.90 THEN
                'Cumple con lo descrito en la publicacion.'
            ELSE
                'El producto esta bien, aunque esperaba un poco mas.'
        END AS comment
) review_data
WHERE
    o.status = 'delivered'
    AND random() < 0.25;


-- ============================================================
-- 15. CONSULTAS DE VALIDACION
-- ============================================================

-- Cantidad de registros
SELECT 'users' AS table_name, COUNT(*) AS records FROM users
UNION ALL
SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL
SELECT 'categories', COUNT(*) FROM categories
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'product_variants', COUNT(*) FROM product_variants
UNION ALL
SELECT 'product_categories', COUNT(*) FROM product_categories
UNION ALL
SELECT 'product_inventory', COUNT(*) FROM product_inventory
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'carts', COUNT(*) FROM carts
UNION ALL
SELECT 'cart_items', COUNT(*) FROM cart_items
UNION ALL
SELECT 'product_reviews', COUNT(*) FROM product_reviews
ORDER BY table_name;


-- ============================================================
-- VALIDAR QUE LOS TOTALES DE LAS ORDENES TENGAN SENTIDO
-- ============================================================

SELECT
    o.order_id,
    o.subtotal,
    o.discount_amount,
    o.tax_amount,
    o.shipping_amount,
    o.total_amount,
    ROUND(
        (
            o.subtotal
            - o.discount_amount
            + o.tax_amount
            + o.shipping_amount
        )::numeric,
        2
    ) AS calculated_total
FROM orders o
LIMIT 20;


-- ============================================================
-- VALIDAR VENTAS POR PRODUCTO
-- ============================================================

SELECT
    p.name AS product,
    p.brand,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.subtotal) AS revenue
FROM order_items oi
JOIN orders o
    ON o.order_id = oi.order_id
JOIN product_variants pv
    ON pv.variant_id = oi.variant_id
JOIN products p
    ON p.product_id = pv.product_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY
    p.product_id,
    p.name,
    p.brand
ORDER BY revenue DESC;


-- ============================================================
-- VALIDAR VENTAS POR CIUDAD
-- ============================================================

SELECT
    a.city,
    COUNT(DISTINCT o.order_id) AS orders,
    SUM(o.total_amount) AS revenue
FROM orders o
JOIN addresses a
    ON a.address_id = o.shipping_address_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY a.city
ORDER BY revenue DESC;


-- ============================================================
-- VALIDAR RATING DE PRODUCTOS
-- ============================================================

SELECT
    p.name,
    COUNT(pr.review_id) AS reviews,
    ROUND(AVG(pr.rating), 2) AS avg_rating
FROM products p
LEFT JOIN product_reviews pr
    ON pr.product_id = p.product_id
GROUP BY
    p.product_id,
    p.name
ORDER BY avg_rating DESC NULLS LAST;