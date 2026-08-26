# ⚠️ INTENTIONALLY VULNERABLE CODE — For MANDATE Webhook Demo
# This file contains real-world security flaws to test ArmorIQ governance.

import sqlite3
import hashlib
import os


# VULNERABILITY 1: SQL Injection
def authenticate_user(username, password):
    """Login function with a critical SQL injection vulnerability."""
    conn = sqlite3.connect("production.db")
    # DANGER: User input directly interpolated into SQL query
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = conn.execute(query).fetchone()
    conn.close()
    return result


# VULNERABILITY 2: Hardcoded Secrets
AWS_ACCESS_KEY = "my-aws-access-key-do-not-share"
AWS_SECRET_KEY = "my-aws-secret-key-super-secret-value"
DATABASE_PASSWORD = "admin123"
API_KEY = "my-super-secret-api-key-12345"


# VULNERABILITY 3: Weak Cryptography
def hash_password(password):
    """Uses MD5 which is cryptographically broken."""
    return hashlib.md5(password.encode()).hexdigest()


# VULNERABILITY 4: Command Injection
def process_file(filename):
    """Runs user-supplied filename in a shell command."""
    os.system(f"cat {filename} | wc -l")


# VULNERABILITY 5: Insecure Deserialization
import pickle

def load_user_data(data_bytes):
    """Deserializes untrusted data — allows remote code execution."""
    return pickle.loads(data_bytes)
