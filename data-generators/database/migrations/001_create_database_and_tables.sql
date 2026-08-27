-- ============================================================
-- MODELO TRANSACCIONAL E-COMMERCE
-- PostgreSQL
-- ============================================================

-- Crear la base de datos

CREATE DATABASE ecommerce;
-- ============================================================
-- EXTENSIONES
-- ============================================================

\c ecommerce

CREATE EXTENSION IF NOT EXISTS pgcrypto;



-- ============================================================
-- 1. USERS
-- ============================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    phone VARCHAR(30),
    birth_date DATE,
    gender VARCHAR(30),

    status VARCHAR(30) NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_users_status
        CHECK (status IN ('active', 'inactive', 'blocked'))
);


-- ============================================================
-- 2. ADDRESSES
-- ============================================================

CREATE TABLE addresses (
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    address_type VARCHAR(30) NOT NULL,
    address_line VARCHAR(255) NOT NULL,

    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20),

    is_default BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_addresses_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_addresses_type
        CHECK (address_type IN ('shipping', 'billing'))
);


-- ============================================================
-- 3. CATEGORIES
-- ============================================================

CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(100) NOT NULL UNIQUE,

    parent_category_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES categories(category_id)
        ON DELETE SET NULL
);


-- ============================================================
-- 4. PRODUCTS
-- ============================================================

CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(255) NOT NULL,
    description TEXT,

    brand VARCHAR(100),

    base_price NUMERIC(12,2) NOT NULL,
    cost_price NUMERIC(12,2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_products_base_price
        CHECK (base_price >= 0),

    CONSTRAINT chk_products_cost_price
        CHECK (cost_price >= 0),

    CONSTRAINT chk_products_status
        CHECK (status IN ('active', 'inactive', 'discontinued'))
);


-- ============================================================
-- 5. PRODUCT_VARIANTS
-- ============================================================

CREATE TABLE product_variants (
    variant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    product_id UUID NOT NULL,

    sku VARCHAR(100) NOT NULL UNIQUE,

    color VARCHAR(50),
    size VARCHAR(50),

    price NUMERIC(12,2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_variants_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_product_variants_price
        CHECK (price >= 0),

    CONSTRAINT chk_product_variants_status
        CHECK (status IN ('active', 'inactive', 'discontinued'))
);


-- ============================================================
-- 6. PRODUCT_CATEGORIES
-- ============================================================

CREATE TABLE product_categories (
    product_id UUID NOT NULL,
    category_id UUID NOT NULL,

    PRIMARY KEY (product_id, category_id),

    CONSTRAINT fk_product_categories_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_product_categories_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON DELETE CASCADE
);


-- ============================================================
-- 7. PRODUCT_INVENTORY
-- ============================================================

CREATE TABLE product_inventory (
    inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    variant_id UUID NOT NULL,

    warehouse VARCHAR(100) NOT NULL,

    quantity_available INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,

    reorder_level INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_inventory_variant
        FOREIGN KEY (variant_id)
        REFERENCES product_variants(variant_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_inventory_quantity_available
        CHECK (quantity_available >= 0),

    CONSTRAINT chk_inventory_quantity_reserved
        CHECK (quantity_reserved >= 0),

    CONSTRAINT chk_inventory_reorder_level
        CHECK (reorder_level >= 0),

    CONSTRAINT uq_inventory_variant_warehouse
        UNIQUE (variant_id, warehouse)
);


-- ============================================================
-- 8. ORDERS
-- ============================================================

CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    shipping_address_id UUID,
    billing_address_id UUID,

    status VARCHAR(30) NOT NULL DEFAULT 'pending',

    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    shipping_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,

    currency VARCHAR(3) NOT NULL DEFAULT 'COP',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_orders_shipping_address
        FOREIGN KEY (shipping_address_id)
        REFERENCES addresses(address_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_orders_billing_address
        FOREIGN KEY (billing_address_id)
        REFERENCES addresses(address_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_orders_status
        CHECK (
            status IN (
                'pending',
                'confirmed',
                'processing',
                'shipped',
                'delivered',
                'cancelled',
                'refunded'
            )
        ),

    CONSTRAINT chk_orders_subtotal
        CHECK (subtotal >= 0),

    CONSTRAINT chk_orders_discount
        CHECK (discount_amount >= 0),

    CONSTRAINT chk_orders_tax
        CHECK (tax_amount >= 0),

    CONSTRAINT chk_orders_shipping
        CHECK (shipping_amount >= 0),

    CONSTRAINT chk_orders_total
        CHECK (total_amount >= 0),

    CONSTRAINT chk_orders_currency
        CHECK (currency ~ '^[A-Z]{3}$')
);


-- ============================================================
-- 9. ORDER_ITEMS
-- ============================================================

CREATE TABLE order_items (
    order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,
    variant_id UUID NOT NULL,

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    subtotal NUMERIC(12,2) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_items_variant
        FOREIGN KEY (variant_id)
        REFERENCES product_variants(variant_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_order_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_order_items_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_order_items_discount
        CHECK (discount_amount >= 0),

    CONSTRAINT chk_order_items_tax
        CHECK (tax_amount >= 0),

    CONSTRAINT chk_order_items_subtotal
        CHECK (subtotal >= 0)
);


-- ============================================================
-- 10. PAYMENTS
-- ============================================================

CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    payment_method VARCHAR(50) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'pending',

    amount NUMERIC(12,2) NOT NULL,

    transaction_reference VARCHAR(150) UNIQUE,

    paid_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_payments_amount
        CHECK (amount >= 0),

    CONSTRAINT chk_payments_status
        CHECK (
            status IN (
                'pending',
                'approved',
                'failed',
                'refunded'
            )
        ),

    CONSTRAINT chk_payments_method
        CHECK (
            payment_method IN (
                'credit_card',
                'debit_card',
                'pse',
                'paypal',
                'bank_transfer',
                'cash_on_delivery'
            )
        )
);


-- ============================================================
-- 11. CARTS
-- ============================================================

CREATE TABLE carts (
    cart_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_carts_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_carts_status
        CHECK (
            status IN (
                'active',
                'converted',
                'abandoned',
                'expired'
            )
        )
);


-- ============================================================
-- 12. CART_ITEMS
-- ============================================================

CREATE TABLE cart_items (
    cart_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cart_id UUID NOT NULL,
    variant_id UUID NOT NULL,

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(12,2) NOT NULL,

    added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMPTZ,

    CONSTRAINT fk_cart_items_cart
        FOREIGN KEY (cart_id)
        REFERENCES carts(cart_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_cart_items_variant
        FOREIGN KEY (variant_id)
        REFERENCES product_variants(variant_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_cart_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_cart_items_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_cart_items_dates
        CHECK (
            removed_at IS NULL
            OR removed_at >= added_at
        )
);


-- ============================================================
-- 13. PRODUCT_REVIEWS
-- ============================================================

CREATE TABLE product_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    product_id UUID NOT NULL,
    order_id UUID,

    rating SMALLINT NOT NULL,

    title VARCHAR(255),
    comment TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_reviews_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_product_reviews_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_product_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_product_reviews_rating
        CHECK (rating BETWEEN 1 AND 5)
);


-- ============================================================
-- ÍNDICES
-- ============================================================

-- USERS
CREATE INDEX idx_users_created_at
    ON users(created_at);

CREATE INDEX idx_users_status
    ON users(status);


-- ADDRESSES
CREATE INDEX idx_addresses_user_id
    ON addresses(user_id);

CREATE INDEX idx_addresses_city
    ON addresses(city);


-- CATEGORIES
CREATE INDEX idx_categories_parent_category
    ON categories(parent_category_id);


-- PRODUCTS
CREATE INDEX idx_products_brand
    ON products(brand);

CREATE INDEX idx_products_status
    ON products(status);

CREATE INDEX idx_products_created_at
    ON products(created_at);


-- PRODUCT VARIANTS
CREATE INDEX idx_product_variants_product_id
    ON product_variants(product_id);

CREATE INDEX idx_product_variants_status
    ON product_variants(status);


-- PRODUCT CATEGORIES
CREATE INDEX idx_product_categories_category_id
    ON product_categories(category_id);


-- INVENTORY
CREATE INDEX idx_product_inventory_variant_id
    ON product_inventory(variant_id);

CREATE INDEX idx_product_inventory_warehouse
    ON product_inventory(warehouse);


-- ORDERS
CREATE INDEX idx_orders_user_id
    ON orders(user_id);

CREATE INDEX idx_orders_status
    ON orders(status);

CREATE INDEX idx_orders_created_at
    ON orders(created_at);

CREATE INDEX idx_orders_user_created_at
    ON orders(user_id, created_at);


-- ORDER ITEMS
CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_variant_id
    ON order_items(variant_id);


-- PAYMENTS
CREATE INDEX idx_payments_order_id
    ON payments(order_id);

CREATE INDEX idx_payments_status
    ON payments(status);

CREATE INDEX idx_payments_paid_at
    ON payments(paid_at);


-- CARTS
CREATE INDEX idx_carts_user_id
    ON carts(user_id);

CREATE INDEX idx_carts_status
    ON carts(status);

CREATE INDEX idx_carts_created_at
    ON carts(created_at);


-- CART ITEMS
CREATE INDEX idx_cart_items_cart_id
    ON cart_items(cart_id);

CREATE INDEX idx_cart_items_variant_id
    ON cart_items(variant_id);

CREATE INDEX idx_cart_items_added_at
    ON cart_items(added_at);


-- REVIEWS
CREATE INDEX idx_product_reviews_product_id
    ON product_reviews(product_id);

CREATE INDEX idx_product_reviews_user_id
    ON product_reviews(user_id);

CREATE INDEX idx_product_reviews_created_at
    ON product_reviews(created_at);


-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================