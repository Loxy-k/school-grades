# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
# Start Django on Railway

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn on port $PORT"
exec gunicorn school_grades.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level info
EOF

# Make it executable
chmod +x start.sh

# Update Procfile
echo "web: ./start.sh" > Procfile
