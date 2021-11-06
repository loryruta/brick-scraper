from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
from db import Session
from models import User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
import inspect
from functools import wraps


blueprint = Blueprint('auth', __name__)


def set_authorization_cookie(response, user):
    payload = {
        'user_id': user.id,
        'user_email': user.email,
        'iat': datetime.now(tz=timezone.utc),
        'exp': datetime.now(tz=timezone.utc) + timedelta(hours=int(os.environ['JWT_EXPIRATION_HOURS']))
    }
    jwt_token = jwt.encode(
        payload,
        os.environ['JWT_SECRET'],
        algorithm='HS256'
    )
    response.set_cookie('token', jwt_token)
    return response


def auth_request(handler_func):
    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        jwt_token = request.cookies.get('token')
        if jwt_token:
            try:
                payload = jwt.decode(jwt_token, os.environ['JWT_SECRET'], algorithms=['HS256'])
                g.user_id = payload['user_id']
                g.user_email = payload['user_email']
                print('Authenticated user (%d): %s' % (g.user_id, g.user_email))
                return current_app.ensure_sync(handler_func)(*args, **kwargs)
            except jwt.DecodeError as e:
                print('JWT decoding failed:', e)
        return redirect(url_for('auth.login'))
    return wrapper


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        try:
            # Inserts the user in the DB
            with Session.begin() as session:
                user = User(
                    email=email,
                    password_hash=password_hash.decode('utf-8')
                )
                session.add(user)

                # OK
                response = redirect(url_for('home'))
                set_authorization_cookie(response, user)
                return response, 200

        except SQLAlchemyError:
            # The user can't be inserted
            flash("User already exists")
            return redirect(url_for('auth.register'))
    else:
        return render_template('register.html')


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        print("Logging in: (%s, %s)" % (email, "*"))

        try:
            with Session() as session:
                user = session.query(User).filter_by(email=email).first()

                # todo USER IS NULL?

                remote_password_hash = user.password_hash
                remote_password_hash_b = remote_password_hash.encode('utf-8')

                # Password verification
                if bcrypt.checkpw(password.encode(), remote_password_hash_b):
                    response = redirect('/')
                    set_authorization_cookie(response, user)
                    return response, 200
                else:
                    # Mismatching passwords
                    pass
        except SQLAlchemyError:
            # The user couldn't be found in DB
            pass

        flash("Wrong credentials")
        return redirect(url_for('auth.login'))
    else:
        return render_template('login.html')

