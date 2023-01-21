import sys


sys.path.append('src')


from dotenv import load_dotenv


load_dotenv()


import logging


log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)


import os
from flask import Flask, g, Blueprint


app = Flask(__name__,
            static_url_path='/public',
            static_folder='public',
            template_folder='templates')
app.secret_key = os.environ['APP_SECRET_KEY']


from routes.auth import auth_request, blueprint as auth_blueprint
from routes.inventory import blueprint as inventory_blueprint
from routes.orders import blueprint as orders_blueprint
from routes.user import blueprint as user_blueprint
from routes.catalog import blueprint as catalog_blueprint
from routes.partout import blueprint as partout_blueprint
from routes.settings import blueprint as settings_blueprint

import image_storage
from backends.bricklink import parse_bricklink_item_type


@app.route('/', methods=['GET'])
@auth_request
def home():
      return "Hello world! It's working!"


app.register_blueprint(auth_blueprint)
app.register_blueprint(inventory_blueprint)
app.register_blueprint(orders_blueprint)
app.register_blueprint(user_blueprint)
app.register_blueprint(catalog_blueprint)
app.register_blueprint(partout_blueprint)
app.register_blueprint(settings_blueprint)

storage_blueprint = Blueprint('storage', __name__, static_url_path='/public/storage/', static_folder='storage')
app.register_blueprint(storage_blueprint)


@app.context_processor
def env():
      globals = {}

      globals['env'] = os.environ

      if hasattr(g, 'user_id'): globals['user_id'] = g.user_id
      if hasattr(g, 'user_email'): globals['user_email'] = g.user_email

      return globals


app.jinja_env.globals.update(
      get_item_image_url=image_storage.get_item_image_url,
      parse_bricklink_item_type=parse_bricklink_item_type
)


if __name__ == '__main__':
      print(f"Listening on {os.environ['APP_HOST']}:{os.environ['APP_PORT']}...")
      app.run(host=os.environ['APP_HOST'], port=os.environ['APP_PORT'])

