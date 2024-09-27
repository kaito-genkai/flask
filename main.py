from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pytz
import time

import os


app = Flask(__name__)

#後で書き換える
app.config["SECRET_KEY"] = os.urandom(24)

#ログイン管理システム
login_manager = LoginManager()
login_manager.init_app(app)

db = SQLAlchemy()

if app.debug:
    app.config["SECRET_KEY"] = os.urandom(24)
    DB_INFO = {
        "user": "postgres",
        "password": "vbnw5540",
        "host": "localhost",
        "name": "postgres",
        "port": "1234"
    }
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://{user}:{password}@{host}:{port}/{name}".format(**DB_INFO)
else:
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql+psycopg://")


app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
db.init_app(app)

migrate = Migrate(app, db)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    tokyo_timezone = pytz.timezone("Asia/Tokyo")
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(tokyo_timezone).strftime("%Y-%m-%d %H:%M:%S")
    )
    img_name = db.Column(db.String(100), nullable=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)


#現在のユーザを識別
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    posts = Post.query.order_by(Post.id).all()

    for post in posts:
        if post.img_name:
            img_path = os.path.join(app.static_folder, "img", post.img_name)
            if not os.path.exists(img_path):
                post.img_name = None
    return render_template("index.html", posts=posts)

@app.route("/admin")
@login_required
def admin():
    posts = Post.query.order_by(Post.id).all()

    for post in posts:
        if post.img_name:
            img_path = os.path.join(app.static_folder, "img", post.img_name)
            if not os.path.exists(img_path):
                post.img_name = None
    return render_template("admin.html", posts=posts)

@app.route("/<int:post_id>/readmore")
def readmore(post_id):
    post = Post.query.get(post_id)

    if post.img_name:
        img_path = os.path.join(app.static_folder, "img", post.img_name)
        if not os.path.exists(img_path):
            post.img_name = None
    return render_template("readmore.html", post=post)

@app.route("/admin/<int:post_id>/readmore")
@login_required
def readmore_admin(post_id):
    post = Post.query.get(post_id)

    if post.img_name:
        img_path = os.path.join(app.static_folder, "img", post.img_name)
        if not os.path.exists(img_path):
            post.img_name = None
    return render_template("readmore_admin.html", post=post)

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    #リクエストメソッドの判別
    if request.method == "POST":
        # リクエストで送信された情報の取得
        title = request.form.get("title")
        body = request.form.get("body")
        #画像情報の取得
        file = request.files.get("img")
        filename = None
        #画像ファイル名を保存
        if file and file.filename:
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            save_path = os.path.join(app.static_folder, "img", filename)
            file.save(save_path)
        # 情報の保存
        post = Post(title=title, body=body, img_name=filename)
        db.session.add(post)
        db.session.commit()

        return redirect("/admin")

    elif request.method == "GET":
        return render_template("create.html")

@app.route("/<int:post_id>/update", methods=["GET", "POST"])
@login_required
def update(post_id):
    post = Post.query.get(post_id)
    #リクエストメソッドの判別
    if request.method == "POST":
        # リクエストで送信された情報の取得
        post.title = request.form.get("title")
        post.body = request.form.get("body")
        # 情報の保存
        db.session.commit()
        return redirect("/admin")

    elif request.method == "GET":
        return render_template("update.html", post=post)

@app.route("/<int:post_id>/delete")
@login_required
def delete(post_id):
    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/admin")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    #リクエストメソッドの判別
    if request.method == "POST":
        # リクエストで送信された情報の取得
        username = request.form.get("username")
        password = request.form.get("password")

        # 情報の保存
        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    elif request.method == "GET":
        return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        #ユーザ名とパスワードを取得
        username = request.form.get("username")
        password = request.form.get("password")
        #ユーザ名をもとにデータベースから情報を取得
        user = User.query.filter_by(username=username).first()
        #入力パスワードとデータベースのパスワードが一致しているか確認
        if check_password_hash(user.password, password=password):
            # 一致していれば、ログインさせて管理画面ヘリダイレクトさせる
            login_user(user)
            return redirect("/admin")
        else:
            # 間違っていた場合、エラー文と共にログイン画面へリダイレクトさせる
            flash("ユーザ名またはパスワードが違います", "error")
            return redirect(url_for("login"))

    elif request.method == "GET":
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")