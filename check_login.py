import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect('app_data.db')
c = conn.cursor()

# Show all users
print("=== ALL USERS IN DATABASE ===")
c.execute("SELECT id, name, email, password FROM users")
for row in c.fetchall():
    print(f"ID: {row[0]}, Name: {row[1]}, Email: {row[2]}")
    print(f"Hashed Password: {row[3][:20]}...")
    print()

# Test login
email = input("Enter email to test: ")
password = input("Enter password to test: ")

c.execute("SELECT name, password FROM users WHERE email=?", (email,))
result = c.fetchone()

if result:
    stored_hash = result[1]
    entered_hash = hash_password(password)
    
    print(f"\nStored hash:  {stored_hash[:20]}...")
    print(f"Entered hash: {entered_hash[:20]}...")
    print(f"Match: {stored_hash == entered_hash}")
else:
    print(f"\nEmail not found!")

conn.close()
