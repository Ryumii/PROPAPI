"""Seed a production user + API key on Azure PG."""
import os
import secrets

import bcrypt
import psycopg2

db_url = os.environ["DATABASE_URL_SYNC"]
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute(
    "INSERT INTO user_account (id, email, password_hash, plan) "
    "VALUES (1, 'admin@propapi.jp', 'dummy_not_used', 'professional') "
    "ON CONFLICT (id) DO NOTHING"
)

prefix = "cs_live_"
random_part = secrets.token_urlsafe(32)
plain_key = f"{prefix}{random_part}"
key_prefix_12 = plain_key[:12]
key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

cur.execute(
    "INSERT INTO api_key (user_id, key_hash, key_prefix, plan, monthly_limit, rate_per_sec, is_active) "
    "VALUES (1, %s, %s, 'professional', 100000, 100, true)",
    (key_hash, key_prefix_12),
)

conn.commit()
cur.close()
conn.close()
print(f"PRODUCTION_API_KEY={plain_key}")
