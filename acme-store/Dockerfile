FROM php:8.2-apache

# Install mysqli
RUN docker-php-ext-install mysqli

# Enable mod_rewrite (optional)
RUN a2enmod rewrite

# Copy app
COPY html/ /var/www/html/

# Wait for MySQL before starting Apache
COPY wait-for-mysql.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/wait-for-mysql.sh

EXPOSE 80

CMD ["sh", "-c", "wait-for-mysql.sh && apache2-foreground"]
