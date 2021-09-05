import shutil
from updatehelpercommon import GitController


def initjob(workspace_path, oreo_controller, connection, body):
    clean_up(workspace_path, oreo_controller)

    extended_job_id = f'job/{body["job_id"]}'
    serialized_extended_id = extended_job_id.replace('/', '-s-')
    job_repo_path = f'{workspace_path}processing/{serialized_extended_id}'

    git_controller = GitController(f'{workspace_path}processing/input/', body['source'])
    if git_controller.checkout(body['commit'], commit=True) == False:
        raise RuntimeError(f'Job {body["job_id"]} can\'t be checkout at {body["commit"]}')

    file_dict = git_controller.gather_java([job_repo_path])
    shutil.rmtree(f'{workspace_path}processing/input/')

    oreo_controller.calculate_metric(workspace_path + 'processing/')
    # TODO: Check if metric is empty
    with connection.cursor() as cursor:
        get_status_query = 'SELECT * FROM `update_helper`.`status`'
        cursor.execute(get_status_query)
        statuses = dict((y, x) for x, y in cursor.fetchall())

        update_status_query = 'UPDATE `update_helper`.`job` SET job_snippet_file = %s, job_status = %s WHERE job_id = %s'
        cursor.execute(update_status_query, (extended_job_id, statuses['RUNNING'], body['job_id']))
    connection.commit()

    clean_up(workspace_path, oreo_controller)

def clean_up(workspace_path, oreo_controller):
    try:
        shutil.rmtree(workspace_path + 'processing/')
    except FileNotFoundError:
        pass

    oreo_controller.clean_up_metric()
