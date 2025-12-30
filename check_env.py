import os

print("=" * 60)
print("CHECKING ENVIRONMENT VARIABLES")
print("=" * 60)

# Check all environment variables
print("\nAll environment variables:")
for key, value in sorted(os.environ.items()):
    if 'DATABASE' in key or 'POSTGRES' in key or 'SECRET' in key or 'DEBUG' in key or 'PORT' in key:
        if 'SECRET' in key or 'PASS' in key or 'KEY' in key:
            print(f"  {key}: {'*' * 10} (hidden)")
        else:
            print(f"  {key}: {value}")

# Check specifically for DATABASE_URL
db_url = os.environ.get('DATABASE_URL')
if db_url:
    print(f"\n✅ DATABASE_URL is set: {db_url[:50]}...")
else:
    print(f"\n❌ DATABASE_URL is NOT set!")
    print("This is why Django is using SQLite instead of PostgreSQL")

# Check PORT
port = os.environ.get('PORT')
print(f"\nPORT: {port if port else 'NOT SET'}")

print("\n" + "=" * 60)
