import os
import pymysql


HOST = os.environ['MYSQL_HOST']
PORT = int(os.environ['MYSQL_PORT'])
USER = os.environ['MYSQL_USER']
PASSWORD = os.environ['MYSQL_PASSWORD']
DATABASE = os.environ['MYSQL_DATABASE']


def connect():
    return pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, local_infile=True)

def retrieve_statuses():
    with connect() as connection:
        with connection.cursor() as cursor:
            get_status_query = 'SELECT * FROM `update_helper`.`status`'
            cursor.execute(get_status_query)
            return dict((y, x) for x, y in cursor.fetchall())
