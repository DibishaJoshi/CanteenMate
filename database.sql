CREATE TABLE user (
        id INTEGER NOT NULL, 
        fullname VARCHAR(100) NOT NULL, 
        email VARCHAR(100) NOT NULL, 
        password VARCHAR(200) NOT NULL, 
        role VARCHAR(20) NOT NULL, 
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, phone TEXT, 
        PRIMARY KEY (id), 
        UNIQUE (email)
);
CREATE TABLE categories (
        id INTEGER NOT NULL, 
        name VARCHAR(100) NOT NULL, 
        status BOOLEAN, 
        PRIMARY KEY (id), 
        UNIQUE (name)
);
CREATE TABLE attributes (
        id INTEGER NOT NULL,
        name VARCHAR(100) NOT NULL,
        status BOOLEAN,
        PRIMARY KEY (id),
        UNIQUE (name)
);
CREATE TABLE attribute_values (
        id INTEGER NOT NULL,
        value VARCHAR(100) NOT NULL,
        price_adjustment FLOAT,
        attribute_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(attribute_id) REFERENCES attributes (id)
);
CREATE TABLE item_attribute_values (
        item_id INTEGER NOT NULL,
        attribute_value_id INTEGER NOT NULL,
        PRIMARY KEY (item_id, attribute_value_id),
        FOREIGN KEY(item_id) REFERENCES items (id),
        FOREIGN KEY(attribute_value_id) REFERENCES attribute_values (id)
);
CREATE TABLE menus (
        id INTEGER NOT NULL,
        day VARCHAR(20) NOT NULL,
        category_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        created_at DATETIME,
        PRIMARY KEY (id),
        CONSTRAINT unique_menu_item UNIQUE (day, category_id, item_id),
        FOREIGN KEY(category_id) REFERENCES categories (id),
        FOREIGN KEY(item_id) REFERENCES items (id)
);
CREATE TABLE order_item (
        id INTEGER NOT NULL,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        name VARCHAR(100) NOT NULL,
        quantity INTEGER NOT NULL,
        price FLOAT NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(order_id) REFERENCES "order" (id)
);
CREATE TABLE reviews (
        id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        service_rating INTEGER,
        delivery_rating INTEGER,
        would_recommend BOOLEAN,
        is_verified BOOLEAN,
        helpful_count INTEGER,
        created_at DATETIME,
        updated_at DATETIME,
        PRIMARY KEY (id),
        FOREIGN KEY(user_id) REFERENCES user (id),
        FOREIGN KEY(order_id) REFERENCES "order" (id),
        FOREIGN KEY(item_id) REFERENCES items (id)
);
CREATE TABLE review_helpful (
        id INTEGER NOT NULL,
        review_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        is_helpful BOOLEAN,
        created_at DATETIME,
        PRIMARY KEY (id),
        CONSTRAINT unique_review_vote UNIQUE (review_id, user_id),
        FOREIGN KEY(review_id) REFERENCES reviews (id),
        FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE addons (
        id INTEGER NOT NULL,
        name VARCHAR(100) NOT NULL,
        price FLOAT NOT NULL,
        category VARCHAR(50) NOT NULL,
        description TEXT,
        status BOOLEAN,
        PRIMARY KEY (id)
);
CREATE TABLE addon_item_association (
        addon_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        PRIMARY KEY (addon_id, item_id),
        FOREIGN KEY(addon_id) REFERENCES addons (id),
        FOREIGN KEY(item_id) REFERENCES items (id)
);
CREATE TABLE cart_items (
        id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER,
        created_at DATETIME, created_date DATE,
        PRIMARY KEY (id),
        FOREIGN KEY(user_id) REFERENCES user (id),
        FOREIGN KEY(item_id) REFERENCES items (id)
);
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price FLOAT NOT NULL,
    category_id INTEGER NOT NULL,
    description TEXT,
    image_filename TEXT,
    available BOOLEAN DEFAULT 1
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE IF NOT EXISTS "order_addons" (
            id INTEGER PRIMARY KEY,
            order_item_id INTEGER NOT NULL,
            addon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category TEXT,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE CASCADE,
            FOREIGN KEY (addon_id) REFERENCES addons(id) ON DELETE CASCADE
        );
CREATE TABLE IF NOT EXISTS "order" (
    id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL,
    delivery VARCHAR(20) NOT NULL,
    building VARCHAR(100),
    floor VARCHAR(100),
    payment VARCHAR(20) NOT NULL,
    created_at DATETIME,
    total_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Pending',
    khalti_token VARCHAR(255),
    esewa_transaction_code TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES user(id)
);