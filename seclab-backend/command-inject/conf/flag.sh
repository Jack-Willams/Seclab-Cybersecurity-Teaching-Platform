#!/bin/bash
sed -i "s/flag={flag}/$FLAG/" /flag

export FLAG=not_flag
FLAG=not_flag

php-fpm & nginx &
echo "Running..."