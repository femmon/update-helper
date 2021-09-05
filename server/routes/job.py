import boto3
from flask import abort, Blueprint, jsonify, request, url_for
import json
import database


job = Blueprint('job', __name__)


@job.route('/', methods=['GET'])
def get_job():
    with database.connect() as connection:
        with connection.cursor() as cursor:
            get_job_query = 'SELECT * FROM `update_helper`.`job`'
            cursor.execute(get_job_query)
            return jsonify(cursor.fetchall())


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
