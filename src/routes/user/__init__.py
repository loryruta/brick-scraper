from flask import Blueprint
from routes.user.operations import blueprint as operations


blueprint = Blueprint('user', __name__)


blueprint.register_blueprint(operations)
