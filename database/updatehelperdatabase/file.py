import csv
import os
import uuid


def save_file_hash(connection, file_dict, temp_path):
    with open(temp_path, 'w') as data:
        data_writer = csv.writer(data)
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
