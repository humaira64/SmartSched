import bcrypt
import mysql.connector

# =========================
# ADMIN DETAILS
# =========================

email = "nurhumairaaaa@gmail.com"
full_name = "Admin03"
default_password = "1234"

# =========================
# CREATE BCRYPT PASSWORD
# =========================

password_hash = bcrypt.hashpw(
    default_password.encode("utf-8"),
    bcrypt.gensalt()
).decode("utf-8")

# =========================
# DATABASE CONNECTION
# =========================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Humaira6#",
    database="smartsched"
)

cursor = db.cursor()

# =========================
# INSERT ADMIN
# =========================

cursor.execute("""
    INSERT INTO admin_users
    (
        email,
        full_name,
        password_hash,
        role,
        is_active,
        must_change_password
    )
    VALUES (%s, %s, %s, %s, %s, %s)
""", (
    email,
    full_name,
    password_hash,
    "admin",
    1,
    1
))

db.commit()

cursor.close()
db.close()

print("Admin account created successfully.")
print("Name:", full_name)
print("Email:", email)
print("Default password:", default_password)