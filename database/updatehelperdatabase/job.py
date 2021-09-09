def update_job_component_status(connection, job_component_id, status):
    with connection.cursor() as cursor:
        statuses = get_statuses(cursor)

        update_status_query = 'UPDATE `update_helper`.`job_component` SET job_component_status = %s WHERE job_component_id = %s'
        cursor.execute(update_status_query, (statuses[status], job_component_id))
    connection.commit()

def check_and_update_finished_job(connection, job_id):
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
    connection.commit()

def get_statuses(cursor):
    get_status_query = 'SELECT * FROM `update_helper`.`status`'
    cursor.execute(get_status_query)
    statuses = dict((y, x) for x, y in cursor.fetchall())
    return statuses
