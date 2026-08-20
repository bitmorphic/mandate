"""
Example user authentication module.
This code intentionally contains security vulnerabilities for testing MANDATE.
"""

import hashlib
import sqlite3
import os


# VULNERABILITY 1: Hardcoded API credentials
API_SECRET = "sk-prod-a8f3k2m5n7p9q1r3s5t7u9w1x3y5z7"
DB_PASSWORD = "production_db_pass_2026!"


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user against the database."""
    # VULNERABILITY 2: SQL Injection via f-string
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result is not None


def hash_token(token: str) -> str:
    """Hash an authentication token."""
    # VULNERABILITY 3: Using MD5 (cryptographically broken)
    return hashlib.md5(token.encode()).hexdigest()


def process_user_input(data: str) -> dict:
    """Process user-submitted configuration."""
    # VULNERABILITY 4: eval() on untrusted input — remote code execution
    return eval(data)


def get_admin_panel(user_role: str) -> str:
    """Return admin panel HTML."""
    # VULNERABILITY 5: XSS via unescaped user input
    return f"<h1>Welcome, {user_role}</h1><script>loadPanel()</script>"
