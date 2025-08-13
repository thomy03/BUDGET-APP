#!/usr/bin/env python3
"""
Debug authentication issues
"""

import sqlite3
import bcrypt

def test_auth():
    """Test authentication flow"""
    
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    
    # Check existing user
    cursor.execute("SELECT username, hashed_password FROM users WHERE username = ?", ("demo",))
    user = cursor.fetchone()
    
    if user:
        username, hashed_password = user
        print(f"Found user: {username}")
        print(f"Stored hash: {hashed_password[:20]}...")
        
        # Test different passwords
        test_passwords = ["demo", "demo123", "password", "password123", "admin123"]
        
        for pwd in test_passwords:
            try:
                is_valid = bcrypt.checkpw(pwd.encode('utf-8'), hashed_password.encode('utf-8'))
                print(f"Password '{pwd}': {'✅ VALID' if is_valid else '❌ INVALID'}")
            except Exception as e:
                print(f"Password '{pwd}': ❌ ERROR - {e}")
    else:
        print("❌ User 'demo' not found")
    
    # Create a simple test user
    new_password = "testpass"
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt)
    
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO users (username, email, hashed_password, is_active) VALUES (?, ?, ?, ?)",
            ("testuser", "test@test.com", new_hash.decode('utf-8'), True)
        )
        conn.commit()
        print(f"✅ Created testuser with password: {new_password}")
    except Exception as e:
        print(f"❌ Error creating testuser: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_auth()