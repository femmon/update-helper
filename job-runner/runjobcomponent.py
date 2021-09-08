import boto3
import os


def run_job_component(workspace_path, oreo_controller, connection, body):
    temp_path = workspace_path + 'temp.txt'
    clean_up(files=[temp_path])   

    s3 = boto3.client('s3')
    with open(temp_path, 'ab') as f:
        s3.download_fileobj('update-helper', body['job_snippet_file'], f)
        s3.download_fileobj('update-helper', body['snippet_file'], f)
    print('Downloaded snippets')
    
    try:
        oreo_controller.detect_clone(temp_path)
    except:
        print('Can\'t detect clones')
        return

    print('Dectector finished')

    clones = {}
    for filename in os.listdir(oreo_controller.clone_result_path):
        with open(oreo_controller.clone_result_path + filename) as f:
            for line in f:
                fragments = line.split(',')
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

    print(clones)
    clean_up(files=[temp_path])

def clean_up(files=[]):
    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass