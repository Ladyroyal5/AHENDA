
from app.services.identity_service import hash_identifier

first_hash = hash_identifier("NIN", "12345678901")
second_hash = hash_identifier("NIN", "12345678901")

print("First hash:", first_hash)
print("Second hash:", second_hash)

print("Same hash:", first_hash == second_hash)
print("Hash length:", len(first_hash))
