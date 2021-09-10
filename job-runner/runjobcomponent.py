import boto3
import os
import requests
from updatehelperdatabase import job


SERVER_HOST = os.environ['SERVER_HOST']


def run_job_component(workspace_path, oreo_controller, connection, body):
    temp_txt = workspace_path + 'temp.txt'
    temp_csv = workspace_path + 'temp.csv'
    temp_paths = [temp_txt, temp_csv]
    clean_up(files=temp_paths)   

    s3 = boto3.client('s3')
    with open(temp_txt, 'ab') as f:
        s3.download_fileobj('update-helper', body['job_snippet_file'], f)
        s3.download_fileobj('update-helper', body['snippet_file'], f)
    print('Downloaded snippets')
    
    try:
        oreo_controller.detect_clone(temp_txt)
    except Exception:
        job.update_job_component_status(connection, body['job_component_id'], 'ERROR')
        is_finished = job.check_and_update_finished_job(connection, body['job_id'])
        r = requests.post(f'{SERVER_HOST}job/{body["job_id"]}', json = {
            'job_id': body['job_id'],
            'job_status': 'FINISHED' if is_finished else 'RUNNING',
            'results': []
        })
        print('Can\'t detect clones')
        return

    print('Dectector finished')

    clones = {}
    for filename in os.listdir(oreo_controller.clone_result_path):
        with open(oreo_controller.clone_result_path + filename) as f:
            for line in f:
                fragments = line.split(',')
                fragments[-1] = fragments[-1].rstrip()

                if fragments[0] == fragments[4]:
                    continue
                function1 = fragments[:4]
                function2 = fragments[4:]
                if function2[0].startswith('job'):
                    function1, function2 = function2, function1
                
                job_func = ','.join(function1[1:4])
                if job_func not in clones:
                    clones[job_func] = set()
                clones[job_func].add(','.join(function2[1:4]))

    job.update_job_component_status(connection, body['job_component_id'], 'FINISHED')
    is_finished = job.check_and_update_finished_job(connection, body['job_id'])
    results = job.save_component_result(connection, body['job_component_id'], clones, temp_csv)
    print(f'Saved results')

    r = requests.post(f'{SERVER_HOST}job/{body["job_id"]}', json = {
        'job_id': body['job_id'],
        'job_status': 'FINISHED' if is_finished else 'RUNNING',
        'results': [{
            'result_id': result[0],
            'origial_file_path': result[1],
            'origial_function_location': result[2],
            'clone_source': body['snippet_source'],
            'clone_version': body['snippet_version'],
            'clone_file_path': result[3],
            'clone_function_location': result[4]
        } for result in results]
    })

    clean_up(files=temp_paths)

def clean_up(files=[]):
    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass