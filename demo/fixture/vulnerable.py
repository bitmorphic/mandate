"""
MANDATE — Deterministic Vulnerable Fixture

This is intentionally vulnerable Python code for the demo.
The security agent must reliably detect these vulnerabilities.
The vulnerabilities are chosen to be:
1. Detectable by semgrep with default rules
2. Fixable by the remediation tool
3. Representative of real-world security issues

DO NOT use this code in production. It is intentionally insecure.
"""

# ─── VULNERABILITY 1: SQL Injection ─────────────────────────────────
# Semgrep rule: python.lang.security.audit.formatted-sql-query
import sqlite3


def get_user(username):
    """VULNERABLE: SQL injection via string formatting."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # This is the vulnerability — user input directly in SQL
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()


def get_user_by_id(user_id):
    """VULNERABLE: SQL injection via f-string."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()


# ─── VULNERABILITY 2: Hardcoded Secrets ─────────────────────────────
# Semgrep rule: python.lang.security.audit.hardcoded-password
API_KEY = "sk-1234567890abcdef1234567890abcdef"
SECRET_KEY = "super_secret_password_123"
DATABASE_PASSWORD = "admin123"


def connect_to_api():
    """VULNERABLE: Uses hardcoded API key."""
    import requests
    headers = {"Authorization": f"Bearer {API_KEY}"}
    return requests.get("https://api.example.com/data", headers=headers)


# ─── VULNERABILITY 3: eval() Usage ──────────────────────────────────
# Semgrep rule: python.lang.security.audit.eval-detected
def calculate(expression):
    """VULNERABLE: Uses eval() on user input."""
    result = eval(expression)
    return result


def process_config(config_str):
    """VULNERABLE: Uses eval() to parse config."""
    config = eval(config_str)
    return config


# ─── VULNERABILITY 4: Weak Cryptography ─────────────────────────────
# Semgrep rule: python.lang.security.audit.md5-used
import hashlib


def hash_password(password):
    """VULNERABLE: Uses MD5 for password hashing."""
    return hashlib.md5(password.encode()).hexdigest()


def verify_integrity(data):
    """VULNERABLE: Uses SHA1 for integrity checks."""
    return hashlib.sha1(data.encode()).hexdigest()


# ─── PERFORMANCE ISSUES (for the performance agent) ─────────────────
import time


def slow_search(items, targets):
    """PERFORMANCE: O(n²) nested loop."""
    results = []
    for item in items:
        for target in targets:
            if item == target:
                results.append(item)
    return results


def blocking_operation():
    """PERFORMANCE: Blocking sleep call."""
    time.sleep(5)
    return "done"


# ─── LINT ISSUES (for the linter agent) ──────────────────────────────
import os, sys  # noqa: E401 — multiple imports on one line

def unused_variable():
    """LINT: Unused variable."""
    x = 42
    y = "never used"
    return x

def bare_except():
    """LINT: Bare except clause."""
    try:
        result = 1 / 0
    except:
        pass
