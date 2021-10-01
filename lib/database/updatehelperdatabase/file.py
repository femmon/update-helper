import csv
import os
import uuid


def save_file_hash(connection, file_dict, temp_path):
    with open(temp_path, 'w') as data:
        data_writer = csv.writer(data, lineterminator='\n')
        for real_path, hash_path in file_dict.items():
            data_writer.writerow([real_path, hash_path])

    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        temp_table_name = uuid.uuid4().hex
        create_table_query = '''
            CREATE TABLE `update_helper`.`%s` (
                `real_path` VARCHAR(511) NOT NULL,
                `hash_path` VARCHAR(255) NOT NULL,
                PRIMARY KEY (`real_path`)
            );
        '''
        cursor.execute(create_table_query, (temp_table_name))

        load_new_query = 'LOAD DATA LOCAL INFILE %s INTO TABLE `update_helper`.`%s` FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"'
        cursor.execute(load_new_query, (temp_path, temp_table_name))

        create_file_query = '''
            INSERT INTO file (real_path, hash_path) SELECT T.real_path, T.hash_path FROM `update_helper`.`%s` AS T 
            LEFT JOIN file AS F ON T.real_path = F.real_path
            WHERE F.real_path IS NULL
        '''
        cursor.execute(create_file_query, (temp_table_name))

        get_ids_query = 'SELECT F.file_id FROM `update_helper`.`%s` AS T LEFT JOIN `file` AS F ON T.real_path = F.real_path'
        cursor.execute(get_ids_query, (temp_table_name))
        id_records = cursor.fetchall()

        delete_query = 'DROP TABLE `update_helper`.`%s`'
        cursor.execute(delete_query, (temp_table_name))

    connection.commit()
    os.remove(temp_path)

    return map(lambda row: row[0], id_records)


def save_file_usage(connection, job_id, file_ids, temp_path):
    with open(temp_path, 'w') as data:
        data_writer = csv.writer(data, lineterminator='\n')
        for file_id in file_ids:
            data_writer.writerow([job_id, file_id])

    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        load_new_query = 'LOAD DATA LOCAL INFILE %s INTO TABLE `job_file_usage` FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"'
        cursor.execute(load_new_query, (temp_path))
        
    connection.commit()
    os.remove(temp_path)


def get_real_paths(connection, hash_paths, temp_path):
    with open(temp_path, 'w') as data:
        data_writer = csv.writer(data, lineterminator='\n')
        for hash_path in hash_paths:
            data_writer.writerow([hash_path])

    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        temp_table_name = uuid.uuid4().hex
        create_table_query = '''
            CREATE TABLE `update_helper`.`%s` (
                `hash_path` VARCHAR(255) NOT NULL
            );
        '''
        cursor.execute(create_table_query, (temp_table_name))
        load_new_query = '''
            LOAD DATA LOCAL INFILE %s INTO TABLE `update_helper`.`%s`
            FIELDS TERMINATED BY ","
            LINES TERMINATED BY "\n"
        '''
        cursor.execute(load_new_query, (temp_path, temp_table_name))

        get_real_path_query = '''
            SELECT DISTINCTROW T.hash_path, F.real_path
            FROM `update_helper`.`%s` AS T
            JOIN `update_helper`.`file` AS F ON T.hash_path = F.hash_path
        '''
        cursor.execute(get_real_path_query, (temp_table_name))
        file_dict = dict(cursor.fetchall())

        delete_query = 'DROP TABLE `update_helper`.`%s`'
        cursor.execute(delete_query, (temp_table_name))

    connection.commit()
    os.remove(temp_path)

    return file_dict
