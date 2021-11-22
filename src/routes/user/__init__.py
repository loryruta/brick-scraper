from flask import Blueprint
from routes.user.operations import blueprint as operations
from routes.user.settings import blueprint as settings


blueprint = Blueprint('user', __name__)


blueprint.register_blueprint(operations)
blueprint.register_blueprint(settings)
