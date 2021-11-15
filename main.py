import sys


sys.path.append('src')


from dotenv import load_dotenv


load_dotenv()


import logging


log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)


import os
from flask import Flask, g


app = Flask(__name__,
            static_url_path='/public',
            static_folder='public',
            template_folder='templates')
app.secret_key = os.environ['APP_SECRET_KEY']


from routes.auth import auth_request, blueprint as auth_blueprint
from routes.cache import blueprint as cache_blueprint
from routes.inventory import blueprint as inventory_blueprint
#from routes.orders import blueprint as orders_blueprint
from routes.user import blueprint as user_blueprint
import image_handler


@app.route('/', methods=['GET'])
@auth_request
def home():
      return "Hello world! It's working!"


app.register_blueprint(auth_blueprint)
app.register_blueprint(cache_blueprint)
app.register_blueprint(inventory_blueprint)
#app.register_blueprint(orders_blueprint)
app.register_blueprint(user_blueprint)


@app.context_processor
def env():
      return {
            'env': os.environ,
            'user_id': g.user_id,
            'user_email': g.user_email,
      }


@app.context_processor
def get_part_image_url():
      def _get_part_image_url(color_id: int, part_id: str):
            return image_handler.get_part_image_url(color_id, part_id)
      return dict(get_part_image_url=_get_part_image_url)


if __name__ == '__main__':
      app.run(port=5000)

