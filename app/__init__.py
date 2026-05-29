from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask_migrate import Migrate

from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

pymysql.install_as_MySQLdb()


db=SQLAlchemy()
loginmanager=LoginManager()


def create_app():
    app=Flask(__name__,static_folder='static')
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Dipti%4002@localhost/smart_attendance'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)
    loginmanager.init_app(app)
    loginmanager.login_view = 'route.teacher_login'
    loginmanager.login_view = 'route.student_login'
    from app.routes import route

    app.register_blueprint(route)

    with app.app_context():
      
     
      
       db.create_all()

    return app