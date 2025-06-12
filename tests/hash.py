from werkzeug.security import generate_password_hash

password = "kali098"
hashed_password = generate_password_hash(password)

print(f"Password: {password}")
print(f"Hashed: {hashed_password}")

