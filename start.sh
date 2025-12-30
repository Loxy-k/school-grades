#!/bin/bash
# start.sh - Startup script for Railway

echo "=========================================="
echo "STARTING SCHOOL GRADES SYSTEM"
echo "=========================================="

# Check environment
echo "1. Checking environment variables..."
python check_env.py

# Run migrations
echo "2. Running database migrations..."
python manage.py migrate --noinput

# Test URLs
echo "3. Testing URL configuration..."
python test_urls.py

# Start server
echo "4. Starting Django development server..."
echo "Server will run on port: $PORT"
python manage.py runserver 0.0.0.0:$PORT --noreload
