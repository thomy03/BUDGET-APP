#!/usr/bin/env python3
"""
Create test user for AI classification validation
"""

import sqlite3
import bcrypt

def create_test_user():
    """Create a test user with proper password hashing"""
    
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    
    # Hash the password properly
    password = "admin123"
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # Update existing user's password
        cursor.execute(
            "UPDATE users SET hashed_password = ? WHERE username = ?",
            (hashed_password.decode('utf-8'), "admin")
        )
        print("✅ Updated admin user password")
    else:
        # Create new user
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password, is_active) VALUES (?, ?, ?, ?)",
            ("admin", "admin@test.com", hashed_password.decode('utf-8'), True)
        )
        print("✅ Created new admin user")
    
    conn.commit()
    conn.close()
    
    print("Admin user credentials:")
    print("  Username: admin")
    print("  Password: admin123")

if __name__ == "__main__":
    create_test_user()