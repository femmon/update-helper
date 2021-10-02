import boto3
import functools
import os
from pathlib import Path
import requests
from updatehelperdatabase import job
from updatehelpersemver import sort_version


SERVER_HOST = os.environ['SERVER_HOST']


def run_job_component(workspace_path, oreo_controller, connection, body):
    # use snippet source and target guava version to find the taget snippet
    temp_txt = workspace_path + 'temp.txt'
    temp_txt2 = workspace_path + 'temp2.txt'
    temp_csv = workspace_path + 'temp.csv'
    temp_paths = [temp_txt, temp_csv, temp_txt2]
    clean_up(files=temp_paths)   

    target_project = query_target_project(connection, body['snippet_source'], body['target_guava_version'])

    s3 = boto3.client('s3')
    with open(temp_txt, 'ab') as f:
        s3.download_fileobj('update-helper', body['job_snippet_file'], f)
        s3.download_fileobj('update-helper', body['snippet_file'], f)
        s3.download_fileobj('update-helper', target_project[1], f)
    print('Downloaded snippets')
    oreo_controller.fix_clone_input(temp_txt, temp_txt2)

    if not should_run(temp_txt):
        clean_up(files=temp_paths)
        return

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

        logs = ["Log_execute_1.out","Log_execute_1.err","Log_restore_gtpm.out","Log_restore_gtpm.err","Log_backup_gtpm.out","Log_backup_gtpm.err","Log_init.out","Log_init.err","Log_cshard.out","Log_cshard.err", "Log_search.out", "Log_search.err"]
        for log in logs:
            log_path = oreo_controller.clone_detector_path + log
            if os.path.isfile(log_path):
                with open(log_path) as f:
                    print('Reading ' + log_path)
                    for line in f:
                        print(line)

        clean_up(files=temp_paths)
        print('Can\'t detect clones')
        return

    print('Dectector finished')

    result_set = extract_result_set(oreo_controller, body['snippet_source'], body['snippet_version'])
    results = job.save_component_result(
        connection,
        body['job_component_id'],
        body['job_source'],
        body['job_commit'],
        body['snippet_source'],
        body['snippet_version'],
        target_project[0],
        result_set,
        temp_csv
    )

    job.update_job_component_status(connection, body['job_component_id'], 'FINISHED', target_project[2])
    is_finished = job.check_and_update_finished_job(connection, body['job_id'])
    print(f'Saved results')

    r = requests.post(f'{SERVER_HOST}job/{body["job_id"]}', json = {
        'job_id': body['job_id'],
        'job_status': 'FINISHED' if is_finished else 'RUNNING',
        'results': [{
            'result_id': result[0],
            'original_file_path': result[1],
            'original_function_location': result[2],
            'original_snippet': result[3],
            'clone_source': body['snippet_source'],
            'clone_version': body['snippet_version'],
            'clone_file_path': result[4],
            'clone_function_location': result[5],
            'clone_snippet': result[6],
            'upgraded_version': target_project[0],
            'upgraded_file_path': result[7],
            'upgraded_function_location': result[8],
            'upgraded_snippet': result[9],
        } for result in results]
    })

    clean_up(files=temp_paths)


def clean_up(files=[]):
    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass


def query_target_project(connection, snippet_source, target_guava_version):
    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        target_project_query = '''
            SELECT S.project_version, S.snippet_file, S.snippet_id
            FROM snippet AS S
            WHERE S.source = %s and S.guava_version = %s
        '''
        cursor.execute(target_project_query, (snippet_source, target_guava_version))
        target_projects = cursor.fetchall()
        target_projects = sort_version(target_projects, key=0)
    
    return target_projects[0]


def should_run(input_path):
    total = 0
    with open(input_path) as f:
        for line in f:
            total += 1

    # Larger input takes more time to run and more storage to store intermediate result
    LIMIT = 40000
    if total > LIMIT:
        print('Input too large')
        return False
    
    return True


def extract_result_set(oreo_controller, snippet_source, snippet_version):
    snippet_file_identifier = serialize_source_version_name(snippet_source, snippet_version)

    clones = {}
    for filename in os.listdir(oreo_controller.clone_result_path):
        with open(oreo_controller.clone_result_path + filename) as f:
            for line in f:
                fragments = line.split(',')
                fragments[-1] = fragments[-1].rstrip()

                snippet_file_count = 0
                if fragments[0].startswith(snippet_file_identifier):
                    snippet_file_count += 1
                if fragments[4].startswith(snippet_file_identifier):
                    snippet_file_count += 1

                if snippet_file_count != 1:
                    continue

                function1 = fragments[:4]
                function2 = fragments[4:]
                if function2[0].startswith(snippet_file_identifier):
                    function1, function2 = function2, function1
                
                snippet_file_func = ','.join(function1[1:4])
                if snippet_file_func not in clones:
                    clones[snippet_file_func] = (set(), set())
                
                if function2[0].startswith('job'):
                    clones[snippet_file_func][0].add(','.join(function2[1:4]))
                else:
                    clones[snippet_file_func][1].add(','.join(function2[1:4]))

    result_set = []
    for snippet_file_location, matches in clones.items():
        if len(matches[0]) == 0:
            continue
        if len(matches[1]) == 0:
            continue

        result_set.append((matches[0].pop(), snippet_file_location, matches[1].pop()))

    return result_set


# TODO: duplicate from preprocess.py
def serialize_source_version_name(source, project_version):
    DASH = '--'
    SLASH = '-s-'
    return f'{source}/{project_version}'.replace('-',DASH).replace('/', SLASH)
