# ⚠️ INTENTIONALLY VULNERABLE CODE — MANDATE Finale Demo
# This file simulates a dangerous pull request that MANDATE must review and block.

import sqlite3
import hashlib
import os
import pickle
import subprocess


# ============================================================
# VULNERABILITY 1: SQL Injection (CRITICAL)
# An attacker can bypass authentication with: ' OR 1=1 --
# ============================================================
def login(username, password):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    user = conn.execute(query).fetchone()
    conn.close()
    return user


# ============================================================
# VULNERABILITY 2: Hardcoded API Keys & Secrets (HIGH)
# These should NEVER be in source code
# ============================================================
STRIPE_SECRET_KEY = "sk_live_fake_stripe_key_12345"
DATABASE_URL = "postgresql://admin:password123@prod-db.internal:5432/main"
JWT_SECRET = "super-secret-jwt-signing-key-do-not-share"


# ============================================================
# VULNERABILITY 3: Weak Cryptography (MEDIUM)
# MD5 is broken — collisions found in seconds
# ============================================================
def hash_user_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# ============================================================
# VULNERABILITY 4: Command Injection (CRITICAL)
# Attacker sends filename="; rm -rf / #" and destroys server
# ============================================================
def count_lines(filename):
    os.system(f"wc -l {filename}")


def run_user_script(script_name):
    subprocess.call(f"bash {script_name}", shell=True)


# ============================================================
# VULNERABILITY 5: Insecure Deserialization (CRITICAL)
# pickle.loads on untrusted data = Remote Code Execution
# ============================================================
def load_session(cookie_data):
    return pickle.loads(cookie_data)


# ============================================================
# VULNERABILITY 6: Path Traversal (HIGH)
# Attacker sends path="../../etc/passwd" to read system files
# ============================================================
def read_user_file(user_path):
    with open(f"/uploads/{user_path}", "r") as f:
        return f.read()


# ============================================================
# VULNERABILITY 7: Hardcoded Admin Backdoor (CRITICAL)
# A secret backdoor that bypasses all authentication
# ============================================================
def authenticate(username, password):
    if username == "admin" and password == "backdoor_master_2024":
        return True  # Backdoor access!
    return login(username, password)
