import csv
import os
import uuid


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


def update_job_component_status(connection, job_component_id, status):
    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        statuses = get_statuses(cursor)

        update_status_query = 'UPDATE `update_helper`.`job_component` SET job_component_status = %s WHERE job_component_id = %s'
        cursor.execute(update_status_query, (statuses[status], job_component_id))
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


def save_component_result(connection, job_component_id, clones, temp_path):
    count = 0
    with open(temp_path, 'w') as data:
        data_writer = csv.writer(data, lineterminator='\n')
        for job_function_location, snippet_function_locations in clones.items():
            job_file, job_function = extract_function_locations(job_function_location)

            for snippet_function_location in snippet_function_locations:
                snippet_file, snippet_function = extract_function_locations(snippet_function_location)
                data_writer.writerow([job_file, job_function, snippet_file, snippet_function])
                count += 1
    print(f'Clones: {count}')

    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        temp_table_name = uuid.uuid4().hex
        create_table_query = '''
            CREATE TABLE `update_helper`.`%s` (
                `job_file` VARCHAR(255) NOT NULL,
                `job_function` VARCHAR(31) NOT NULL,
                `snippet_file` VARCHAR(255) NOT NULL,
                `snippet_function` VARCHAR(31) NOT NULL
            );
        '''
        cursor.execute(create_table_query, (temp_table_name))
        load_new_query = '''
            LOAD DATA LOCAL INFILE %s INTO TABLE `update_helper`.`%s`
            FIELDS TERMINATED BY ","
            LINES TERMINATED BY "\n"
        '''
        cursor.execute(load_new_query, (temp_path, temp_table_name))

        create_result_query = '''
            INSERT INTO `update_helper`.`job_result`
            SELECT NULL, %s, F1.file_id, T.job_function, F2.file_id, T.snippet_function
            FROM `update_helper`.`%s` AS T 
            JOIN `update_helper`.`file` AS F1 ON T.job_file = F1.hash_path
            JOIN `update_helper`.`file` AS F2 ON T.snippet_file = F2.hash_path
        '''
        cursor.execute(create_result_query, (job_component_id, temp_table_name))

        get_ids_query = '''
            SELECT R.job_result_id, F1.real_path, T.job_function, F2.real_path, T.snippet_function
            FROM `update_helper`.`%s` AS T
            JOIN `update_helper`.`file` AS F1 ON T.job_file = F1.hash_path
            JOIN `update_helper`.`file` AS F2 ON T.snippet_file = F2.hash_path
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


def extract_function_locations(function_location):
    delimeter_index = function_location.index(',')
    file_path = function_location[:delimeter_index]
    function_line = function_location[delimeter_index + 1:].replace(',', '-')
    return file_path, function_line


def get_statuses(cursor):
    get_status_query = 'SELECT * FROM `update_helper`.`status`'
    cursor.execute(get_status_query)
    statuses = dict((y, x) for x, y in cursor.fetchall())
    return statuses
