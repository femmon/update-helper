import boto3
from flask import abort, Blueprint, jsonify, request, url_for
from flask_socketio import emit, join_room
import json
from updatehelperdatabase import job as job_model
import database
from __main__ import socketio


job = Blueprint('job', __name__)


@job.route('/', methods=['GET'])
def get_job():
    with database.connect() as connection:
        raw_jobs = job_model.get_jobs(connection)
        jobs = {}
        for raw_job in raw_jobs:
            if raw_job[0] not in jobs:
                jobs[raw_job[0]] = []
            jobs[raw_job[0]].append(raw_job)
        res = [{
            'job_id': job_id,
            'job_source': job_results[0][1],
            'job_commit': job_results[0][2],
            'job_status': job_results[0][3],
            'results': [{
                'result_id': result[4],
                'original_file_path': result[5],
                'original_function_location': result[6],
                'original_snippet': result[11],
                'clone_source': result[7],
                'clone_version': result[8],
                'clone_file_path': result[9],
                'clone_function_location': result[10],
                'clone_snippet': result[12],
                'upgraded_version': result[13],
                'upgraded_file_path': result[14],
                'upgraded_function_location': result[15],
                'upgraded_snippet': result[16]
            } for result in job_results if result[4] is not None]
        } for job_id, job_results in jobs.items()]
        return jsonify(res)


POST_JOB_ROUTE = '/'
@job.route(POST_JOB_ROUTE, methods=['POST'])
def post_job():
    try:
        source = request.json['source']
        commit = request.json['commit']
        source_guava_version = request.json['source_guava_version']
        target_guava_version = request.json['target_guava_version']
    except KeyError:
        return abort(400)

    with database.connect() as connection:
        with connection.cursor() as cursor:
            statuses = database.retrieve_statuses()
            status = statuses['INITIALIZING']
            post_job_query = 'INSERT INTO `update_helper`.`job` VALUES (NULL, %s, %s, %s, %s, NULL, %s)'
            cursor.execute(post_job_query, (source, commit, source_guava_version, target_guava_version, status))
            id = cursor.lastrowid
        connection.commit()
    
    sqs = boto3.resource('sqs', region_name='ap-southeast-2')
    queue = sqs.get_queue_by_name(QueueName='update-helper_job')
    message_body = json.dumps({
        'job_id': id,
        'source': source,
        'commit': commit,
        'source_guava_version': source_guava_version,
        'target_guava_version': target_guava_version,
        'status': status
    })
    queue.send_message(MessageBody=message_body)

    return f'{get_blueprint_mounted_route(request.url_rule.rule, POST_JOB_ROUTE)}/{id}', 201


def get_blueprint_mounted_route(request_rule, current_route):
    current_route_position = request_rule.rfind(current_route)
    return request_rule[:current_route_position]


@job.route('/<int:id>', methods=['POST'])
def post_progress(id):
    emit('progress', request.json, namespace='/', room=id)
    return '', 200


@socketio.on('register')
def register_room(data):
    join_room(int(data['job_id']))
