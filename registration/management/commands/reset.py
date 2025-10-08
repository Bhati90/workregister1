from django.db import connection
cursor = connection.cursor()
cursor.execute("DELETE FROM django_migrations WHERE app='registration';")
exit()