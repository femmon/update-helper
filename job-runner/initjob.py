import boto3
import csv
import json
import os
from projectcontroller import GitController
import shutil
from updatehelperdatabase import file


def initjob(workspace_path, oreo_controller, connection, body):
    temp_path = workspace_path + 'temp.csv'
    clean_up(workspace_path, temp_path, oreo_controller)

    extended_job_id = f'job/{body["job_id"]}'
    serialized_extended_id = extended_job_id.replace('/', '-s-')
    job_repo_path = f'{workspace_path}processing/{serialized_extended_id}'

    git_controller = GitController(f'{workspace_path}processing/input/', body['source'])
    if git_controller.checkout(body['commit'], commit=True) == False:
        raise RuntimeError(f'Job {body["job_id"]} can\'t be checkout at {body["commit"]}')

    file_dict = git_controller.gather_java([job_repo_path])
    print(f'Found {len(file_dict)} files')
    shutil.rmtree(f'{workspace_path}processing/input/')

    oreo_controller.calculate_metric(workspace_path + 'processing/')

    file_ids = file.save_file_hash(connection, file_dict, temp_path)
    print('Saved file hashes')

    with open(oreo_controller.snippet_path, 'rb') as f:
        s3 = boto3.resource('s3')
        s3.Bucket('update-helper').put_object(Key=extended_job_id, Body=f)

    file.save_file_usage(connection, body['job_id'], file_ids, temp_path)
    print('Saved snippet-files association')

    with connection.cursor() as cursor:
        get_status_query = 'SELECT * FROM `update_helper`.`status`'
        cursor.execute(get_status_query)
        statuses = dict((y, x) for x, y in cursor.fetchall())

        if os.stat(oreo_controller.snippet_path).st_size == 0:
            status = statuses['FINISHED']
        else:
            similar_project_query = '''SELECT DISTINCTROW A.snippet_id, A.snippet_file
                FROM snippet AS A JOIN snippet AS B ON A.source = B.source
                WHERE A.guava_version = %s and B.guava_version = %s'''
            cursor.execute(similar_project_query, (body['source_guava_version'], body['target_guava_version']))
            similar_snippets = cursor.fetchall()
            status = statuses['FINISHED'] if len(similar_snippets) == 0 else statuses['RUNNING']

        update_status_query = 'UPDATE `update_helper`.`job` SET job_snippet_file = %s, job_status = %s WHERE job_id = %s'
        cursor.execute(update_status_query, (extended_job_id, status, body['job_id']))
    connection.commit()

    if status == statuses['RUNNING']:
        with open(temp_path, 'w') as data:
            data_writer = csv.writer(data)
            for snippet_id, snippet_file in similar_snippets:
                data_writer.writerow([snippet_id])

        with connection.cursor() as cursor:
            load_component_query = '''LOAD DATA LOCAL INFILE %s INTO TABLE `update_helper`.`job_component`
                FIELDS TERMINATED BY ","
                LINES TERMINATED BY "\n"
                (snippet_id) SET job_id = %s, job_component_status = %s'''
            cursor.execute(load_component_query, (temp_path, body['job_id'], statuses['QUEUEING']))

            get_component_id_query = 'SELECT job_component_id, snippet_id FROM `update_helper`.`job_component` WHERE job_id = %s'
            cursor.execute(get_component_id_query, (body['job_id']))
            component_and_snippet_map = dict((snippet_id, job_component_id) for job_component_id, snippet_id in cursor.fetchall())
        connection.commit()
        os.remove(temp_path)

        message_batches = [[]]
        for snippet_id, snippet_file in similar_snippets:
            if len(message_batches[-1]) == 10:
                message_batches.append([])

            message_body = {
                'job_component_id': component_and_snippet_map[snippet_id],
                'job_snippet_file': extended_job_id,
                'snippet_file': snippet_file,
                'status': statuses['QUEUEING']
            }
            message_batches[-1].append({
                'Id': str(snippet_id),
                'MessageBody': json.dumps(message_body)
            })

        sqs = boto3.resource('sqs', region_name='ap-southeast-2')
        queue = sqs.get_queue_by_name(QueueName='update-helper_job')
        for message_batch in message_batches:
            queue.send_messages(Entries=message_batch)

    clean_up(workspace_path, temp_path, oreo_controller)

def clean_up(workspace_path, temp_path, oreo_controller):
    try:
        shutil.rmtree(workspace_path + 'processing/')
    except FileNotFoundError:
        pass

    try:
        os.remove(temp_path)
    except FileNotFoundError:
        pass

    oreo_controller.clean_up_metric()
