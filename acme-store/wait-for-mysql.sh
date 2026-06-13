#!/bin/sh
# Wait for MySQL to be ready before starting Apache
echo "Waiting for MySQL..."
for i in $(seq 1 30); do
  if php -r "new mysqli('${MYSQL_HOST:-acme-mysql}','${MYSQL_USER:-acme_app}','${MYSQL_PASSWORD:-AcmeDB#P@ss!2024}','${MYSQL_DATABASE:-acme}');" 2>/dev/null; then
    echo "MySQL ready!"
    exit 0
  fi
  sleep 2
done
echo "WARNING: MySQL not ready after 60s, starting anyway..."
exit 0
