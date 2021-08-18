import argparse
import boto3
import csv
import datetime
import fetchprojects
from gitcontroller import GitController
import json
from oreocontroller import OreoController
import os
from pathlib import Path
import pymysql
import shutil
import sys
import logging


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
WORKSPACE_NAME = 'workspace'
WORKSPACE_PATH = SCRIPT_PATH + WORKSPACE_NAME + '/'
TEMP_PATH = WORKSPACE_PATH + 'temp.csv'

DASH = '--'
SLASH = '-s-'

PROJECT_SEPERATOR = '===============================================\n==============================================='
VERSION_SEPERATOR = '-----------------------------'

HOST = os.environ['MYSQL_HOST']
PORT = int(os.environ['MYSQL_PORT'])
USER = os.environ['MYSQL_USER']
PASSWORD = os.environ['MYSQL_PASSWORD']
DATABASE = os.environ['MYSQL_DATABASE']

Path(WORKSPACE_PATH).mkdir(exist_ok=True)

progress_log = logging.getLogger('progress_log')
progress_log_file = 'preprocess.out'
progress_handler = logging.FileHandler(f'{WORKSPACE_PATH}{progress_log_file}')
progress_log.addHandler(progress_handler)
progress_log.setLevel(logging.DEBUG)

error_log = logging.getLogger('error_log')
error_log_file = 'preprocess.err'
error_handler = logging.FileHandler(f'{WORKSPACE_PATH}{error_log_file}')
error_log.addHandler(error_handler)
error_log.setLevel(logging.DEBUG)


def log_progress(message):
    progress_log.info(message)
    print(message)


def log_error(message):
    error_log.warning(message)
    print(message)


def main(connection, s3, from_project, from_version):
    start_information = f' from {from_project} at {from_version}' if from_project is not None else ''
    log_progress(f'\n\nRunning at {str(datetime.datetime.now())}{start_information}')
    oreo_path = os.path.normpath(os.path.join(SCRIPT_PATH, '../oreo-artifact')
    oreo_controller = OreoController() + '/')

    log_progress('Cleaning up')
    clean_up(oreo_controller)

    with open(SCRIPT_PATH + 'projects.txt') as f:
        for line in f:
            project = json.loads(line)
            if from_project is not None:
                if project['name'] != from_project:
                    log_progress('Skipped project ' + project['name'])
                    continue
                else:
                    from_project = None

            project_folder_name = project['source'].rsplit('/', 1)[-1]
            project_folder_path = f'{WORKSPACE_PATH}{project_folder_name}'
            source = project['source'] + '.git'

            print(f'Cloning "{project["name"]}" from {source}')
            try:
                git_controller = GitController(project_folder_path, source)
                log_progress(f'Cloned {project["name"]}')
            except RuntimeError as e:
                log_error(str(e))
                print(PROJECT_SEPERATOR)
                continue
            
            create_project_database(connection, project['name'], project['source'])

            for project_version in project['versions']:
                if from_version is not None:
                    if project_version != from_version:
                        log_progress('Skipped version ' + project_version)
                        continue
                    else:
                        from_version = None

                guava_version = find_guava_version(project['name'], project_version)
                if guava_version is None:
                    # TODO: consider changing this to progress instead of error
                    log_error(f'{project["name"]} at version {project_version} doesn\'t use Guava')
                    print(VERSION_SEPERATOR)
                    continue
                log_progress(f'{project["name"]} at version {project_version} uses Guava {guava_version}')

                if git_controller.checkout(project_version):
                    log_progress(f'Checked out {project["name"]} at version {project_version}')
                else:
                    # TODO: consider changing this to progress instead of error
                    log_error(f'Couldn\'t check out {project["name"]} at version {project_version}')
                    print(VERSION_SEPERATOR)
                    continue

                print('Processing')
                serialized_folder_name = serialize_project_version_name(project['name'], project_version)
                file_dict = git_controller.gather_java(f'{WORKSPACE_PATH}processing/{serialized_folder_name}')
                print(f'Found {len(file_dict)} files')
                save_file_hash(connection, project['name'], project_version, file_dict)
                log_progress('Extracted java files')

                try:
                    oreo_controller.calculate_metric(f'{WORKSPACE_PATH}processing')
                except RuntimeError as e:
                    log_error(str(e))
                    return
                log_progress('Generated metrics')

                save_version(connection, s3, project["name"], project_version, guava_version, oreo_controller.snippet_path)

                oreo_controller.clean_up_metric()
                shutil.rmtree(f'{WORKSPACE_PATH}processing')
                print(VERSION_SEPERATOR)

            if from_version is not None:
                raise ValueError(f'There is no version {from_version} in the chosen project')
            print(PROJECT_SEPERATOR)
            
            # Remove processed repo
            shutil.rmtree(f'{WORKSPACE_PATH}{project_folder_name}')

        if from_project is not None:
            raise ValueError(f'There is no project {from_project}')


def clean_up(oreo_controller):
    try:
        os.remove(TEMP_PATH)
    except FileNotFoundError:
        pass

    for name in os.listdir(WORKSPACE_PATH):
        if name == progress_log_file or name == error_log_file:
            continue
        shutil.rmtree(f'{WORKSPACE_PATH}{name}')

    oreo_controller.clean_up_metric()


def serialize_project_version_name(project_name, project_version):
    # There is no slash inside versions of the dataset
    # It should be fine to extract version back
    return f'{serialize_name(project_name)}{SLASH}{project_version}'


# The initial name is a path, which contains '/' 
def serialize_name(name):
    return name.replace('-',DASH).replace('/', SLASH)


def find_guava_version(project_name, project_version):
    # TODO: catch this then log_error?
    version_info = fetchprojects.query_libraries_io('/api/' + project_name + '/' + project_version + '/dependencies')
    for dependency in version_info['dependencies']:
        if dependency['name'] == 'com.google.guava:guava':
            return dependency['requirements']


# Database
def create_project_database(connection, name, source):
    with connection.cursor() as cursor:
        sql = "INSERT INTO `project` VALUES (%s, %s)"
        try:
            cursor.execute(sql, (name, source))
        except pymysql.err.IntegrityError as e:
            # Ignore duplicate entry
            duplicate_message = 'Duplicate entry \'' + name + '\' for key \'project.PRIMARY\''
            if e.args[0] == 1062 and e.args[1] == duplicate_message:
                pass
            else:
                raise e
    connection.commit()


def save_file_hash(connection, project_name, project_version, file_dict):
    with open(TEMP_PATH, 'w') as data:
        data_writer = csv.writer(data)
        for real_path, hash_path in file_dict.items():
            data_writer.writerow([project_name, project_version, real_path, hash_path])

    with connection.cursor() as cursor:
        # Remove existing data because LOAD DATA LOCAL will ignore duplicate keys
        delete_existing_query = 'DELETE FROM `file` WHERE project_name=%s AND project_version=%s'
        cursor.execute(delete_existing_query, (project_name, project_version))

        load_new_query = 'LOAD DATA LOCAL INFILE %s INTO TABLE `file` FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"'
        cursor.execute(load_new_query, (TEMP_PATH))
        
    connection.commit()
    os.remove(TEMP_PATH)


def save_version(connection, s3, project_name, project_version, guava_version, snippet_path):
    with connection.cursor() as cursor:
        # Create a new record
        sql = "INSERT INTO `snippet` VALUES (%s, %s, %s, %s)"
        new_file_name = serialize_project_version_name(project_name, project_version)
        cursor.execute(sql, (project_name, project_version, guava_version, new_file_name))
    connection.commit()

    with open(snippet_path, 'rb') as f:
        s3.Bucket('update-helper').put_object(Key=new_file_name, Body=f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use the file "projects.txt" produced by "fetchprojects.py" to scrape GitHub and save the processed code to databases.\nThe argument values are taken from "projects.py"')
    parser.add_argument('--from-project', '-p', help='start processing from this project')
    parser.add_argument('--from-version', '-v', help='start processing from this version')
    args = parser.parse_args()
    from_project = args.from_project
    from_version = args.from_version
    if (from_project and not from_version) or (not from_project and from_version):
        print('--from-project and --from-version need to be both set or empty')
        sys.exit()

    with pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, local_infile=True) as connection:
        s3 = boto3.resource('s3')
        main(connection, s3, from_project, from_version)
