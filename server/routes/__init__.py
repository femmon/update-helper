from flask import Blueprint
from routes.job import job


routes = Blueprint('routes', __name__)
routes.register_blueprint(job, url_prefix='/job')
