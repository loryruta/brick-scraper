from dotenv import load_dotenv


load_dotenv()


import os
from flask import Flask
from routes.auth import auth_request, blueprint as auth_blueprint
from routes.cache import blueprint as cache_blueprint
from routes.inventory import blueprint as inventory_blueprint


app = Flask(__name__)
app.secret_key = os.environ['APP_SECRET_KEY']


@app.route('/', methods=['GET'])
@auth_request
def home():
      return "Hello world! It's working!"


app.register_blueprint(auth_blueprint)
app.register_blueprint(cache_blueprint)
app.register_blueprint(inventory_blueprint)


if __name__ == '__main__':
      app.run(port=5000)
