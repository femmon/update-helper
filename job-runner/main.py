import boto3
import json
import os
import pymysql
from updatehelpercommon import GitController
from updatehelpercommon import OreoController
from initjob import initjob
from runjobcomponent import run_job_component


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
WORKSPACE_NAME = 'job-workspace'
WORKSPACE_PATH = SCRIPT_PATH + WORKSPACE_NAME + '/'
OREO_PATH = WORKSPACE_PATH + 'oreo-artifact/'

HOST = os.environ['MYSQL_HOST']
PORT = int(os.environ['MYSQL_PORT'])
USER = os.environ['MYSQL_USER']
PASSWORD = os.environ['MYSQL_PASSWORD']
DATABASE = os.environ['MYSQL_DATABASE']


if __name__ == '__main__':
    git_controller = GitController(OREO_PATH, 'https://github.com/Mondego/oreo-artifact.git', cloned=os.path.exists(OREO_PATH))
    oreo_controller = OreoController(OREO_PATH, init_java_parser=True)

    with pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, local_infile=True) as connection:
        with connection.cursor() as cursor:
            get_status_query = 'SELECT * FROM `update_helper`.`status`'
            cursor.execute(get_status_query)
            statuses = dict((y, x) for x, y in cursor.fetchall())

        sqs = boto3.resource('sqs', region_name='ap-southeast-2')
        queue = sqs.get_queue_by_name(QueueName='update-helper_job')
        print('Finish setting up. Awaiting for message')
        while True:
            for message in queue.receive_messages():
                body = json.loads(message.body)
                print(f'Got message {body}')

                if body['status'] == statuses['INITIALIZING']:
                    initjob(WORKSPACE_PATH, oreo_controller, connection, body)
                elif body['status'] == statuses['QUEUEING']:
                    run_job_component(WORKSPACE_PATH, oreo_controller, connection, body)

                print('Processed message')
                message.delete()
