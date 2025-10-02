from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)

# Sekret i baza z Render ENV
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "supersecret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# MODELE
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ROUTES
@app.route("/")
def index():
    recipes = Recipe.query.all()
    return render_template_string(TEMPLATES["index"], recipes=recipes)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            flash("Please fill out all fields!", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("User already exists!", "danger")
            return redirect(url_for("register"))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template_string(TEMPLATES["register"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid login!", "danger")
    return render_template_string(TEMPLATES["login"])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_recipe():
    if request.method == "POST":
        name = request.form["name"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]

        if not name or not ingredients or not instructions:
            flash("Please fill out all fields!", "danger")
            return redirect(url_for("add_recipe"))

        recipe = Recipe(name=name, ingredients=ingredients, instructions=instructions, user_id=current_user.id)
        db.session.add(recipe)
        db.session.commit()
        flash("Recipe added successfully!", "success")
        return redirect(url_for("index"))

    return render_template_string(TEMPLATES["add_recipe"])

# SZABLONY
TEMPLATES = {
    "base": """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>CookBook</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
            <div class="container">
                <a class="navbar-brand" href="{{ url_for('index') }}">CookBook</a>
                <div>
                    {% if current_user.is_authenticated %}
                        <a class="btn btn-outline-light btn-sm" href="{{ url_for('add_recipe') }}">Add Recipe</a>
                        <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Logout</a>
                    {% else %}
                        <a class="btn btn-outline-light btn-sm" href="{{ url_for('login') }}">Login</a>
                        <a class="btn btn-outline-light btn-sm" href="{{ url_for('register') }}">Register</a>
                    {% endif %}
                </div>
            </div>
        </nav>
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, msg in messages %}
                  <div class="alert alert-{{ category }}">{{ msg }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            {% block content %}{% endblock %}
        </div>
    </body>
    </html>
    """,

    "index": """
    {% extends 'base' %}
    {% block content %}
    <h2 class="mb-3">All Recipes</h2>
    <div class="row">
        {% for r in recipes %}
        <div class="col-md-6">
            <div class="card mb-3 shadow-sm">
                <div class="card-body">
                    <h5>{{ r.name }}</h5>
                    <p><b>Ingredients:</b> {{ r.ingredients }}</p>
                    <p><b>Instructions:</b> {{ r.instructions }}</p>
                </div>
            </div>
        </div>
        {% else %}
        <p>No recipes yet.</p>
        {% endfor %}
    </div>
    {% endblock %}
    """,

    "register": """
    {% extends 'base' %}
    {% block content %}
    <h2>Register</h2>
    <form method="post">
        <input class="form-control mb-2" name="username" placeholder="Username" required>
        <input class="form-control mb-2" name="password" type="password" placeholder="Password" required>
        <button class="btn btn-primary">Register</button>
    </form>
    {% endblock %}
    """,

    "login": """
    {% extends 'base' %}
    {% block content %}
    <h2>Login</h2>
    <form method="post">
        <input class="form-control mb-2" name="username" placeholder="Username" required>
        <input class="form-control mb-2" name="password" type="password" placeholder="Password" required>
        <button class="btn btn-success">Login</button>
    </form>
    {% endblock %}
    """,

    "add_recipe": """
    {% extends 'base' %}
    {% block content %}
    <h2>Add Recipe</h2>
    <form method="post">
        <input class="form-control mb-2" name="name" placeholder="Recipe name" required>
        <textarea class="form-control mb-2" name="ingredients" placeholder="Ingredients" required></textarea>
        <textarea class="form-control mb-2" name="instructions" placeholder="Instructions" required></textarea>
        <button class="btn btn-primary">Add</button>
    </form>
    {% endblock %}
    """
}

# RUN (Render)
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)












