#!/bin/bash
# Rocky Herbals log tail script

echo "📜 Tailing Nginx + Gunicorn logs for Rocky Herbals..."

# Nginx error log
sudo tail -f /var/log/nginx/error.log &

# Nginx access log
sudo tail -f /var/log/nginx/access.log &

# Gunicorn log (adjust path if different)
sudo tail -f /home/senthiltex007/rocky_herbals2/gunicorn.log &

