# Start our service listener in the background
/etc/init.d/nginx start

python /home/service_configurator.py

#Start nginx in the foreground
# nginx -g "daemon off;"