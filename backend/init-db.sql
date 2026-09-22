-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock INTEGER DEFAULT 0,
    language VARCHAR(10) DEFAULT 'zh',
    platform VARCHAR(50),
    embedding vector(1536),  -- For text-embedding-3-large
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on product embeddings for similarity search
CREATE INDEX IF NOT EXISTS products_embedding_idx ON products
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(100),
    customer_email VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    total_amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    language VARCHAR(10) DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_sku VARCHAR(50),
    product_name VARCHAR(255),
    quantity INTEGER,
    unit_price DECIMAL(10, 2)
);

-- Create shipments table
CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_no),
    tracking_number VARCHAR(100),
    carrier VARCHAR(50),
    status VARCHAR(20),
    estimated_delivery DATE,
    actual_delivery DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create FAQ knowledge base table
CREATE TABLE IF NOT EXISTS faq_knowledge (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    language VARCHAR(10) DEFAULT 'zh',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on FAQ embeddings
CREATE INDEX IF NOT EXISTS faq_embedding_idx ON faq_knowledge
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- Create return_policy table
CREATE TABLE IF NOT EXISTS return_policies (
    id SERIAL PRIMARY KEY,
    policy_type VARCHAR(50),
    content TEXT,
    conditions TEXT,
    language VARCHAR(10) DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample return policies (Chinese)
INSERT INTO return_policies (policy_type, content, conditions, language) VALUES
('standard_return', '7天无理由退换货', '商品未拆封，包装完整', 'zh'),
('quality_issue', '质量问题30天包退换', '需提供质量问题的照片证明', 'zh'),
('shipping_damage', '运输损坏免费更换', '签收后48小时内联系客服', 'zh'),
('wrong_item', '发错商品免费退换', '保持商品原样', 'zh');

-- Create audit log table (aligns with app/models/audit.py ORM)
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    user_query TEXT,
    response TEXT,
    intent VARCHAR(32),
    language VARCHAR(8),
    confidence FLOAT,
    should_transfer INTEGER DEFAULT 0,
    transfer_reason VARCHAR(256),
    compliance_blocked INTEGER DEFAULT 0,
    compliance_reason VARCHAR(256),
    event_type VARCHAR(32) NOT NULL,
    user_ip VARCHAR(64),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs (session_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at);