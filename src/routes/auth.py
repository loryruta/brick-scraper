from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
from flask.helpers import get_flashed_messages
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
import json


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


def auth_request(handler_func):  # TODO rename to require_auth
    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        jwt_token = request.cookies.get('token')
        if jwt_token:
            try:
                payload = jwt.decode(jwt_token, os.environ['JWT_SECRET'], algorithms=['HS256'])

                with Session() as session:
                    user_id = payload['user_id']
                    user = session.query(User) \
                        .filter_by(id=user_id) \
                        .first()

                    if user:
                        g.user_id = user_id
                        g.user_email = payload['user_email']

                        print('Authenticated user (%d): %s' % (g.user_id, g.user_email))
                        return current_app.ensure_sync(handler_func)(*args, **kwargs)
                    else:
                        print(f"User #{user_id} does not exist.")

            except jwt.PyJWTError as e:
                print('JWT decoding failed:', e)
            
        return redirect(url_for('auth.login'))
    return wrapper


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        form_feedback = json.loads(get_flashed_messages()[0]) if get_flashed_messages() else {}
        return render_template('register.j2', form_feedback=form_feedback)

    elif request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        def send_form_feedback(form_feedback):
            flash(json.dumps(form_feedback))
            return redirect(url_for(request.endpoint))

        form_feedback = {}

        if not email:
            form_feedback['email'] = "Email is required."

        if not password:
            form_feedback['password'] = "Password is required."

        if password != confirm_password:
            form_feedback['confirm_password'] = "Confirmation password doesn't match."

        if form_feedback:
            return send_form_feedback(form_feedback)

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        try:
            # Inserts the user in the DB
            with Session.begin() as session:
                user = User(
                    email=email,
                    password_hash=password_hash.decode('utf-8') 
                )
                session.add(user)
                session.flush([user])
                session.refresh(user)

                # OK
                response = redirect(url_for('home'))
                set_authorization_cookie(response, user)
                return response

        except SQLAlchemyError as e:
            print(e)
            return send_form_feedback({ 'submit': "A user using this email already exists." })


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        form_feedback = json.loads(get_flashed_messages()[0]) if get_flashed_messages() else {}
        return render_template('login.j2', form_feedback=form_feedback)

    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        def send_form_feedback(form_feedback):
            flash(json.dumps(form_feedback))
            return redirect(url_for(request.endpoint))
        
        form_feedback = {}

        if not email:
            form_feedback['email'] = "Email is required."

        if not password:
            form_feedback['password'] = "Password is required."
        
        if form_feedback:
            send_form_feedback(form_feedback)

        with Session.begin() as session:
            user = session.query(User) \
                .filter_by(email=email) \
                .first()

            if user:
                if bcrypt.checkpw(password.encode(), user.password_hash.encode('utf-8')):
                    response = redirect(url_for('inventory.items'))
                    set_authorization_cookie(response, user)
                    return response
                else:
                    pass
            else:
                pass

            return send_form_feedback({ 'submit': "Wrong credentials." })

@blueprint.route('/logout', methods=['GET'])
def logout():
    response = redirect(url_for('auth.login'))
    response.set_cookie('token', '')
    return response
