import fetchprojects
import glob
import json
import os
from pathlib import Path
import pexpect
import pymysql
import shutil
import subprocess
import time
import logging


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
WORKSPACE_NAME = 'workspace'
WORKSPACE_PATH = SCRIPT_PATH + WORKSPACE_NAME + '/'
OREO_PATH = os.path.normpath(os.path.join(SCRIPT_PATH, '../oreo-artifact/oreo/python_scripts')) + '/'
DASH = '--'
SLASH = '-s'

PROJECT_SEPERATOR = '===============================================\n==============================================='
VERSION_SEPERATOR = '-----------------------------'

HOST = os.environ['MYSQL_HOST']
PORT = int(os.environ['MYSQL_PORT'])
USER = os.environ['MYSQL_USER']
PASSWORD = os.environ['MYSQL_PASSWORD']
DATABASE = os.environ['MYSQL_DATABASE']

Path(WORKSPACE_PATH).mkdir(exist_ok=True)

progress_log = logging.getLogger('progress_log')
progress_handler = logging.FileHandler(f'{WORKSPACE_PATH}preprocess.out')
progress_log.addHandler(progress_handler)
progress_log.setLevel(logging.DEBUG)

error_log = logging.getLogger('error_log')
error_handler = logging.FileHandler(f'{WORKSPACE_PATH}preprocess.err')
error_log.addHandler(error_handler)
error_log.setLevel(logging.DEBUG)


def log_progress(message):
    progress_log.info(message)
    print(message)


def log_error(message):
    error_log.warning(message)
    print(message)


def main(connection):
    with open(SCRIPT_PATH + 'projects.txt') as f:
        for line in f:
            project = json.loads(line)
            project_folder_name = project['source'].rsplit('/', 1)[-1]
            source = project['source'] + '.git'

            print(f'Cloning "{project["name"]}" from {source}')
            try:
                git_clone(source)
                log_progress(f'Cloned {project["name"]}')
            except RuntimeError as e:
                log_error(str(e))
                print(PROJECT_SEPERATOR)
                continue
            
            create_project_database(connection, project['name'], project['source'])

            for project_version in project['versions']:
                guava_version = find_guava_version(project['name'], project_version)
                if guava_version is None:
                    # TODO: consider changing this to progress instead of error
                    log_error(f'{project["name"]} at version {project_version} doesn\'t use Guava')
                    print(VERSION_SEPERATOR)
                    continue
                log_progress(f'{project["name"]} at version {project_version} uses Guava {guava_version}')

                if checkout_git_version(f'{WORKSPACE_PATH}{project_folder_name}', project_version):
                    log_progress(f'Checked out {project["name"]} at version {project_version}')
                else:
                    # TODO: consider changing this to progress instead of error
                    log_error(f'Couldn\'t check out {project["name"]} at version {project_version}')
                    print(VERSION_SEPERATOR)
                    continue

                print('Processing')
                process(
                    f'{SCRIPT_PATH}{WORKSPACE_NAME}/{project_folder_name}',
                    f'{WORKSPACE_NAME}/processing/{project["name"].replace("-",DASH).replace("/", SLASH)}{SLASH}{project_version}'
                )
                log_progress('Extracted java files')

                calculate_metric()
                log_progress('Generated metrics')
                    
                with open(OREO_PATH + '1_metric_output/mlcc_input.file') as f:
                    with connection.cursor() as cursor:
                        # Create a new record
                        sql = "INSERT INTO `snippet` VALUES (%s, %s, %s, %s)"
                        cursor.execute(sql, (project['name'], project_version, guava_version, f.read()))
                    connection.commit()

                shutil.rmtree(f'{WORKSPACE_PATH}processing')
                print(VERSION_SEPERATOR)

            print(PROJECT_SEPERATOR)
            
            # Remove processed repo
            shutil.rmtree(f'{WORKSPACE_PATH}{project_folder_name}')


def git_clone(source):
    clone_output = pexpect.run(
        'git clone ' + source,
        # Enter credential when asked. This should stop the clone because of unauthorization
        events={
            "Username for 'https://github.com':": "Username\n",
            "Password for 'https://Username@github.com':": "Password\n"
        },
        cwd=WORKSPACE_PATH,
        timeout=None
    ).decode()
    last_output_line = pexpect_output_last_line(clone_output)

    if last_output_line.startswith('fatal:'):
        raise RuntimeError(f'Can\'t clone {source} ("{last_output_line}")')
    elif last_output_line.endswith('done.'):
        # Success
        pass
    else:
        raise RuntimeError(f'Can\'t clone {source} for unknown reason ("{last_output_line}")')


def pexpect_output_last_line(pexpect_output):
    pexpect_output = [line for line in pexpect_output.split('\r\n') if line != '']
    return pexpect_output[-1]
    

# Folder needs to be an absolute path
def process(folder, new_name):
    new_folder = SCRIPT_PATH + new_name
    Path(new_folder).mkdir(parents=True)

    files = glob.glob(folder + '/**/*.java', recursive=True)
    for raw_path in files:
        new_file_name = raw_path[len(folder) + 1:].replace('-',DASH).replace('/', SLASH)
        shutil.copy(raw_path, new_folder + '/' + new_file_name)

    print(f'Found {len(files)} files')


def find_guava_version(project_name, project_version):
    # TODO: catch this then log_error?
    version_info = fetchprojects.query_libraries_io('/api/' + project_name + '/' + project_version + '/dependencies')
    for dependency in version_info['dependencies']:
        if dependency['name'] == 'com.google.guava:guava':
            return dependency['requirements']


def checkout_git_version(repo, version):
    checkout_output = pexpect.run(
        f'git checkout tags/{version}',
        cwd=repo,
        timeout=None
    ).decode()

    checkout_output_last_line = pexpect_output_last_line(checkout_output)
    failed_clone_message = f'error: pathspec \'tags/{version}\' did not match any file(s) known to git.'
    is_success = checkout_output_last_line.startswith('HEAD is now at ')
    if checkout_output_last_line == failed_clone_message or not is_success:
        version = 'v' + version
        print('Checkout again using tag ' + version)
        checkout_output = pexpect.run(
            f'git checkout tags/{version}',
            cwd=repo,
            timeout=None
        ).decode()

        checkout_output_last_line = pexpect_output_last_line(checkout_output)
        failed_clone_message = f'error: pathspec \'tags/{version}\' did not match any file(s) known to git.'
        is_success = checkout_output_last_line.startswith('HEAD is now at ')
        if checkout_output_last_line == failed_clone_message or not is_success:
            return False

    return True


def calculate_metric():
    subprocess.Popen(
        ['python3', 'metricCalculationWorkManager.py', '1', 'd', f'{WORKSPACE_PATH}processing'],
        cwd = OREO_PATH
    )

    while True:
        time.sleep(10)
        with open(OREO_PATH + 'metric.out') as f:
            for line in f:
                pass
            if line == 'done!\n':
                break


# Database
def create_project_database(connection, name, source):
    with connection.cursor() as cursor:
        sql = "INSERT INTO `project` VALUES (%s, %s)"
        cursor.execute(sql, (name, source))
    connection.commit()


if __name__ == '__main__':
    with pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE) as connection:
        main(connection)
