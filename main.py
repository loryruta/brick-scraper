import sys


sys.path.append('src')


from dotenv import load_dotenv


load_dotenv()


import os
from flask import Flask, send_from_directory


app = Flask(__name__, static_folder='/')
app.secret_key = os.environ['APP_SECRET_KEY']


from routes.auth import auth_request, blueprint as auth_blueprint
from routes.cache import blueprint as cache_blueprint
from routes.inventory import blueprint as inventory_blueprint
from models import InventoryPart, Part
import image_handler


@app.route('/', methods=['GET'])
@auth_request
def home():
      return "Hello world! It's working!"


@app.route('/storage/<path:path>')
def storage(path: str):
      return send_from_directory('storage', path)


app.register_blueprint(auth_blueprint)
app.register_blueprint(cache_blueprint)
app.register_blueprint(inventory_blueprint)


@app.template_filter()
def get_part_image_url(part: InventoryPart):
    return image_handler.get_part_image_url(part)


if __name__ == '__main__':
      app.run(port=5000)

