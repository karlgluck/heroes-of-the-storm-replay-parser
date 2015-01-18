web: gunicorn webserver.wsgi --log-file -
worker: celery worker --app=webserver -l info
