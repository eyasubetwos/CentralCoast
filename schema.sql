-- Create global inventory table
CREATE TABLE global_inventory (
    id SERIAL PRIMARY KEY,
    num_green_potions INT NOT NULL CHECK (num_green_potions >= 0),
    num_red_potions INT NOT NULL CHECK (num_red_potions >= 0),
    num_blue_potions INT NOT NULL CHECK (num_blue_potions >= 0),
    num_green_ml INT NOT NULL CHECK (num_green_ml >= 0),
    num_red_ml INT NOT NULL CHECK (num_red_ml >= 0),
    num_blue_ml INT NOT NULL CHECK (num_blue_ml >= 0),
    gold INT NOT NULL CHECK (gold >= 0)
);

-- Create capacity inventory table
CREATE TABLE capacity_inventory (
    id SERIAL PRIMARY KEY,
    potion_capacity INT NOT NULL CHECK (potion_capacity >= 0),
    ml_capacity INT NOT NULL CHECK (ml_capacity >= 0),
    gold_cost_per_unit INT NOT NULL CHECK (gold_cost_per_unit >= 0)
);

-- Create potion mixes table
CREATE TABLE potion_mixes (
    potion_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    potion_composition JSONB NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    inventory_quantity INT NOT NULL CHECK (inventory_quantity >= 0)
);

-- Create customer visits table
CREATE TABLE customer_visits (
    visit_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    visit_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create carts table
CREATE TABLE carts (
    cart_id SERIAL PRIMARY KEY,
    visit_id INT NOT NULL REFERENCES customer_visits(visit_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create cart items table
CREATE TABLE cart_items (
    cart_items_id SERIAL PRIMARY KEY,
    cart_id INT NOT NULL REFERENCES carts(cart_id),
    item_sku VARCHAR(50) NOT NULL REFERENCES potion_mixes(sku),
    quantity INT NOT NULL CHECK (quantity >= 0)
);

-- Add unique constraint for SKU
ALTER TABLE potion_mixes
    ADD CONSTRAINT uq_sku UNIQUE (sku);

-- Add foreign key constraint for cart items
ALTER TABLE cart_items
    ADD CONSTRAINT fk_cart_id FOREIGN KEY (cart_id) REFERENCES carts(cart_id);

-- Add foreign key constraint for customer visits
ALTER TABLE carts
    ADD CONSTRAINT fk_visit_id FOREIGN KEY (visit_id) REFERENCES customer_visits(visit_id);

-- Insert initial data into global inventory table
INSERT INTO global_inventory (num_green_potions, num_red_potions, num_blue_potions, num_green_ml, num_red_ml, num_blue_ml, gold)
VALUES (100, 100, 100, 50000, 50000, 50000, 10000);

-- Insert initial data into capacity inventory table
INSERT INTO capacity_inventory (potion_capacity, ml_capacity, gold_cost_per_unit)
VALUES (100, 10000, 1000);

-- Insert initial data into potion mixes table
INSERT INTO potion_mixes (name, potion_composition, sku, price, inventory_quantity)
VALUES 
    ('Green Potion', '{"green": 100, "red": 0, "blue": 0, "dark": 0}', 'GP-001', 50.00, 50),
    ('Red Potion', '{"green": 0, "red": 100, "blue": 0, "dark": 0}', 'RP-001', 75.00, 50),
    ('Blue Potion', '{"green": 0, "red": 0, "blue": 100, "dark": 0}', 'BP-001', 65.00, 50),
    ('Purple Potion', '{"green": 50, "red": 0, "blue": 50, "dark": 0}', 'PP-001', 90.00, 25);

-- Insert initial data into customer visits table
INSERT INTO customer_visits (customer_name)
VALUES ('Customer A'), ('Customer B');

-- Insert initial data into carts table
INSERT INTO carts (visit_id)
VALUES (1), (2);

-- Insert initial data into cart items table
INSERT INTO cart_items (cart_id, item_sku, quantity)
VALUES 
    (1, 'GP-001', 2),
    (1, 'RP-001', 1),
    (2, 'BP-001', 3);