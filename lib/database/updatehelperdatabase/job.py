import base64
import csv
import os
import re
import requests
import uuid
from updatehelperdatabase.file import get_real_paths


def get_jobs(connection):
    with connection.cursor() as cursor:
        get_job_query = '''
            SELECT DISTINCTROW J.job_id, J.source, J.commit, S.label, R.job_result_id, F1.real_path, R.job_function, SP.source, SP.project_version, F2.real_path, R.snippet_function
            FROM `update_helper`.`job` AS J
            LEFT JOIN `update_helper`.`job_component` AS C ON J.job_id = C.job_id
            LEFT JOIN `update_helper`.`job_result` AS R ON C.job_component_id = R.job_component_id
            LEFT JOIN `update_helper`.`snippet` AS SP ON C.snippet_id = SP.snippet_id
            LEFT JOIN `update_helper`.`file` AS F1 ON R.job_file_id = F1.file_id
            LEFT JOIN `update_helper`.`file` AS F2 ON R.snippet_file_id = F2.file_id
            JOIN `update_helper`.`status` AS S ON J.job_status = S.status_id
            ORDER BY J.job_id
        '''
        cursor.execute(get_job_query)
        return cursor.fetchall()


def update_job_component_status(connection, job_component_id, status, target_snippet_id=None):
    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        statuses = get_statuses(cursor)

        update_status_query = '''
            UPDATE `update_helper`.`job_component`
            SET target_id = %s, job_component_status = %s
            WHERE job_component_id = %s
        '''
        cursor.execute(update_status_query, (target_snippet_id, statuses[status], job_component_id))
    connection.commit()


def check_and_update_finished_job(connection, job_id):
    finished = False
    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        statuses = get_statuses(cursor)

        unfinished_query = '''
            SELECT count(*) FROM `update_helper`.`job_component`
            JOIN `update_helper`.`status`
            ON `update_helper`.`job_component`.job_component_status = `update_helper`.`status`.status_id
            WHERE job_id = %s and label = 'QUEUEING';
        '''
        cursor.execute(unfinished_query, (job_id))
        unfinised_count = cursor.fetchone()[0]
        if unfinised_count == 0:
            update_status_query = 'UPDATE `update_helper`.`job` SET job_status = %s WHERE job_id = %s'
            cursor.execute(update_status_query, (statuses['FINISHED'], job_id))
            finished = True
    connection.commit()

    return finished


def save_component_result(connection, job_component_id, job_source, job_commit, snippet_source, snippet_version, target_version, result_set, temp_path):
    file_dict = get_used_files(connection, result_set, temp_path)

    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        count = 0
        with open(temp_path, 'w') as data:
            data_writer = csv.writer(data, lineterminator='\n', quoting=csv.QUOTE_ALL)
            for job_function_location, snippet_function_location, target_function_location in result_set:
                job_file, job_function = extract_function_locations(job_function_location)
                snippet_file, snippet_function = extract_function_locations(snippet_function_location)
                target_file, target_function = extract_function_locations(target_function_location)
                try:
                    job_real_snippet = get_snippet(job_source, job_commit, file_dict[job_file], job_function)
                    snippet_real_snippet = get_snippet(snippet_source, snippet_version, file_dict[snippet_file], snippet_function)
                    target_real_snippet = get_snippet(snippet_source, target_version, file_dict[target_file], target_function)
                except RuntimeError as e:
                    print(e)
                    continue

                data_writer.writerow([
                    job_file, job_function, job_real_snippet,
                    snippet_file, snippet_function, snippet_real_snippet,
                    target_file, target_function, target_real_snippet
                ])
                count += 1
        print(f'Clones: {count}')

        temp_table_name = uuid.uuid4().hex
        create_table_query = '''
            CREATE TABLE `update_helper`.`%s` (
                `job_file` VARCHAR(255) NOT NULL,
                `job_function` VARCHAR(31) NOT NULL,
                `job_real_snippet` TEXT,
                `snippet_file` VARCHAR(255) NOT NULL,
                `snippet_function` VARCHAR(31) NOT NULL,
                `snippet_real_snippet` TEXT,
                `target_file` VARCHAR(255) NOT NULL,
                `target_function` VARCHAR(31) NOT NULL,
                `target_real_snippet` TEXT
            );
        '''
        cursor.execute(create_table_query, (temp_table_name))
        load_new_query = '''
            LOAD DATA LOCAL INFILE %s INTO TABLE `update_helper`.`%s`
            FIELDS TERMINATED BY ","
            ENCLOSED BY '"'
            LINES TERMINATED BY "\n"
        '''
        cursor.execute(load_new_query, (temp_path, temp_table_name))

        # Temp table only has file hashes but job_result requires id, so join is required
        create_result_query = '''
            INSERT INTO `update_helper`.`job_result`
            SELECT
                NULL, %s,
                F1.file_id, T.job_function, T.job_real_snippet,
                F2.file_id, T.snippet_function, T.snippet_real_snippet,
                F3.file_id, T.target_function, T.target_real_snippet
            FROM `update_helper`.`%s` AS T 
            JOIN `update_helper`.`file` AS F1 ON T.job_file = F1.hash_path
            JOIN `update_helper`.`file` AS F2 ON T.snippet_file = F2.hash_path
            JOIN `update_helper`.`file` AS F3 ON T.target_file = F3.hash_path
            ON DUPLICATE KEY UPDATE job_result_id = job_result_id
        '''
        cursor.execute(create_result_query, (job_component_id, temp_table_name))

        get_ids_query = '''
            SELECT
                R.job_result_id, F1.real_path, T.job_function, T.job_real_snippet,
                F2.real_path, T.snippet_function, T.snippet_real_snippet,
                F3.real_path, T.target_function, T.target_real_snippet
            FROM `update_helper`.`%s` AS T
            JOIN `update_helper`.`file` AS F1 ON T.job_file = F1.hash_path
            JOIN `update_helper`.`file` AS F2 ON T.snippet_file = F2.hash_path
            JOIN `update_helper`.`file` AS F3 ON T.target_file = F3.hash_path
            JOIN `update_helper`.`job_result` AS R
                ON R.job_file_id = F1.file_id
                AND R.job_function = T.job_function
                AND R.snippet_file_id = F2.file_id
                AND R.snippet_function = T.snippet_function
            WHERE job_component_id = %s
        '''
        cursor.execute(get_ids_query, (temp_table_name, job_component_id))
        results = cursor.fetchall()

        delete_query = 'DROP TABLE `update_helper`.`%s`'
        cursor.execute(delete_query, (temp_table_name))

    connection.commit()
    os.remove(temp_path)

    return results


def get_used_files(connection, result_set, temp_path):
    hash_paths = []
    for job_function_location, snippet_function_location, target_function_location in result_set:
        job_file, job_function = extract_function_locations(job_function_location)
        hash_paths.append(job_file)

        snippet_file, snippet_function = extract_function_locations(snippet_function_location)
        hash_paths.append(snippet_file)

        target_file, target_function = extract_function_locations(target_function_location)
        hash_paths.append(target_file)

    return get_real_paths(connection, hash_paths, temp_path)


def extract_function_locations(function_location):
    delimeter_index = function_location.index(',')
    file_path = function_location[:delimeter_index]
    function_line = function_location[delimeter_index + 1:].replace(',', '-')
    return file_path, function_line


def get_snippet(source, ref, file_path, function_line):
    repo = extract_github_repo(source)
    job_file_content = retrieve_file_content(repo, ref, file_path)
    return extract_snippet(job_file_content, function_line)


def extract_github_repo(source):
    match = re.search('https://github.com/([^/]+/[^/]+)/?$', source)
    if match:
        return match.group(1)
    raise RuntimeError('Not from Github')


def retrieve_file_content(repo, ref, file_path):
    params = {'ref': ref}
    headers = {'Accept': 'application/vnd.github.v3+json'}
    try:
        auth = (os.environ['GITHUB_USERNAME'], os.environ['GITHUB_TOKEN'])
    except KeyError:
        auth = None

    r = requests.get(f'https://api.github.com/repos/{repo}/contents/{file_path}', params=params, headers=headers, auth=auth)
    if r.status_code == 200:
        return base64.b64decode(r.json()['content']).decode()
    elif r.status_code == 404:
        params = {'ref': 'v' + ref}
        r = requests.get(f'https://api.github.com/repos/{repo}/contents/{file_path}', params=params, headers=headers)
        if r.status_code == 200:
            return base64.b64decode(r.json()['content']).decode()

    raise RuntimeError(f'Request of file {file_path} from {repo} - {ref} returns {r.status_code}')


def extract_snippet(text, location):
    # Because location starting at 1 and including the last line
    start = int(location.split('-')[0]) - 1
    end = int(location.split('-')[1])
    return '\n'.join(text.split('\n')[start:end])


def get_statuses(cursor):
    get_status_query = 'SELECT * FROM `update_helper`.`status`'
    cursor.execute(get_status_query)
    statuses = dict((y, x) for x, y in cursor.fetchall())
    return statuses
