"""Seed a test user + API key for local development."""
import secrets

import bcrypt
import psycopg2

conn = psycopg2.connect("postgresql://reapi:changeme_local_only@localhost:5432/reapi")
cur = conn.cursor()

# Create test user
cur.execute(
    "INSERT INTO user_account (id, email, password_hash, plan) "
    "VALUES (1, 'test@propapi.jp', 'dummy_not_used', 'professional') "
    "ON CONFLICT (id) DO NOTHING"
)

# Generate API key (key_prefix must be first 12 chars to match _key_prefix lookup)
prefix = "cs_live_"
random_part = secrets.token_urlsafe(32)
plain_key = f"{prefix}{random_part}"
key_prefix_12 = plain_key[:12]  # _key_prefix() uses first 12 chars for DB lookup
key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

cur.execute(
    "INSERT INTO api_key (user_id, key_hash, key_prefix, plan, monthly_limit, rate_per_sec, is_active) "
    "VALUES (1, %s, %s, 'professional', 100000, 100, true)",
    (key_hash, key_prefix_12),
)

conn.commit()
cur.close()
conn.close()

print(f"API_KEY={plain_key}")
