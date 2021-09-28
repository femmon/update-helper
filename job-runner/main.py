import boto3
import json
import os
import pymysql
from projectcontroller import GitController
from projectcontroller import OreoController
import shutil
from updatehelperdatabase import job
import uuid
from initjob import initjob
from runjobcomponent import run_job_component


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
WORKSPACE_NAME = 'job-workspace'

HOST = os.environ['MYSQL_HOST']
PORT = int(os.environ['MYSQL_PORT'])
USER = os.environ['MYSQL_USER']
PASSWORD = os.environ['MYSQL_PASSWORD']
DATABASE = os.environ['MYSQL_DATABASE']


def lambda_handler(event, context):
    with pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, local_infile=True) as connection:
        with connection.cursor() as cursor:
            statuses = job.get_statuses(cursor)
        print('Finish setting up')

        for record in event['Records']:
            # Body is string when deployed, object when run locally
            body = json.loads(record['body']) if isinstance(record['body'], str) else record['body']
            print(f'Got message {body}')
            message_router('/mnt/tmp/', statuses, connection, body)

        print('Processed messages')

    return {
        'statusCode': 200,
        'body': {}
    }
 

def message_router(wordspace_root, statuses, connection, body):
    workspace_path = f'{wordspace_root}{WORKSPACE_NAME}/{body["status"]}'
    if body['status'] == statuses['INITIALIZING']:
        workspace_path += f'-{body["job_id"]}/'
    elif body['status'] == statuses['QUEUEING']:
        workspace_path += f'-{body["job_id"]}-{body["job_component_id"]}/'
    # TODO: consider what happends if there are 2 Lambda functions using the same workspace_path,
    # or if this is the second time a message is processed
    try:
        shutil.rmtree(workspace_path)
    except:
        pass

    oreo_path = workspace_path + 'oreo-artifact/'
    git_controller = GitController(oreo_path, 'https://github.com/Mondego/oreo-artifact.git')
    oreo_controller = OreoController(oreo_path, init_java_parser=True)

    try:
        if body['status'] == statuses['INITIALIZING']:
            initjob(workspace_path, oreo_controller, connection, body)
        elif body['status'] == statuses['QUEUEING']:
            run_job_component(workspace_path, oreo_controller, connection, body)
    finally:
        shutil.rmtree(workspace_path)


if __name__ == '__main__':
    with pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, local_infile=True) as connection:
        with connection.cursor() as cursor:
            statuses = job.get_statuses(cursor)

        sqs = boto3.resource('sqs', region_name='ap-southeast-2')
        queue = sqs.get_queue_by_name(QueueName='update-helper_job')
        print('Finish setting up. Awaiting for message')
        while True:
            for message in queue.receive_messages():
                body = json.loads(message.body)
                print(f'Got message {body}')
                message_router(SCRIPT_PATH, statuses, connection, body)

                print('Processed message')
                message.delete()
