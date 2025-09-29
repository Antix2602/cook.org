from flask import Flask, request, redirect, url_for, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import DictLoader
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os, random

app = Flask(__name__)
app.config['484h484bdc4wbdsk84345'] = os.environ.get('SECRET_KEY','dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MODELE
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    recipes = db.relationship('Recipe', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    def set_password(self,password): self.password_hash=generate_password_hash(password)
    def check_password(self,password): return check_password_hash(self.password_hash,password)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    instructions = db.Column(db.Text)
    prep_time = db.Column(db.String(50))
    cuisine = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ingredients = db.relationship('Ingredient', backref='recipe', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='recipe', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary='recipe_tags', backref=db.backref('recipes', lazy='dynamic'))

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    name = db.Column(db.String(200))
    amount = db.Column(db.String(100))

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class RecipeTags(db.Model):
    __tablename__ = 'recipe_tags'
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)
    text = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

# SZABLONY
templates = {
'base.html':"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cook.org</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800">
<nav class="bg-white shadow">
<div class="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
<a href="{{ url_for('index') }}" class="font-bold text-xl">Cook.org</a>
<div class="space-x-4">
<a href="{{ url_for('recipes') }}">Recipes</a>
{% if current_user.is_authenticated %}
<a href="{{ url_for('add_recipe') }}" class="ml-2 px-3 py-1 bg-green-500 text-white rounded">Add recipe</a>
<span class="ml-4">Hello, {{ current_user.username }}</span>
<a href="{{ url_for('logout') }}" class="ml-3 text-sm text-red-600">Logout</a>
{% else %}
<a href="{{ url_for('login') }}" class="ml-2">Login</a>
<a href="{{ url_for('register') }}" class="ml-2">Register</a>
{% endif %}
</div>
</div>
</nav>
<div class="max-w-5xl mx-auto px-4 py-8">{% block content %}{% endblock %}</div>
</body>
</html>
""",
'index.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-3xl font-bold mb-4">Popular Recipes</h1>
<div class="grid sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
{% for r in popular %}
<a href="{{ url_for('view_recipe', recipe_id=r.id) }}" class="p-4 bg-white rounded shadow flex flex-col hover:shadow-lg transition">
<h3 class="font-semibold">{{ r.name }}</h3>
<p class="text-sm text-gray-500">{{ r.prep_time }} • Cuisine: {{ r.cuisine }}</p>
</a>
{% endfor %}
</div>
{% endblock %}
""",
'recipes.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-2xl font-bold mb-4">Recipes</h1>
<form method="get" class="mb-4 flex flex-col sm:flex-row gap-2">
<input name="q" value="{{ request.args.get('q','') }}" placeholder="Search" class="p-2 border rounded flex-1">
<button class="px-4 py-2 bg-blue-600 text-white rounded">Search</button>
</form>
<div class="grid sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
{% for r in recipes %}
<a href="{{ url_for('view_recipe', recipe_id=r.id) }}" class="p-4 bg-white rounded shadow flex flex-col hover:shadow-lg transition">
<h3 class="font-semibold">{{ r.name }}</h3>
<p class="text-sm text-gray-500">{{ r.prep_time }} • Cuisine: {{ r.cuisine }}</p>
</a>
{% endfor %}
</div>
{% endblock %}
""",
'view_recipe.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-2xl font-bold mb-2">{{ recipe.name }}</h1>
<p class="text-sm text-gray-500 mb-4">{{ recipe.prep_time }} • Cuisine: {{ recipe.cuisine }} • {{ recipe.tags|map(attribute='name')|join(', ') }}</p>
<h2 class="font-semibold">Ingredients:</h2>
<ul class="list-disc list-inside mb-4">
{% for i in recipe.ingredients %}<li>{{ i.amount }} {{ i.name }}</li>{% endfor %}
</ul>
<a href="{{ url_for('download_shopping_list', recipe_id=recipe.id) }}" class="mb-4 inline-block px-3 py-1 bg-purple-600 text-white rounded">Download Shopping List (PDF)</a>
<h2 class="font-semibold">Instructions:</h2>
<p class="mb-4">{{ recipe.instructions|replace('\n','<br>')|safe }}</p>
{% if current_user.is_authenticated %}
<h3 class="font-semibold">Add comment:</h3>
<form method="post" class="mb-4 flex flex-col gap-2">
<input type="number" name="rating" min="1" max="5" placeholder="Rating 1-5" class="p-1 border rounded" required>
<textarea name="text" placeholder="Comment" class="p-1 border rounded" required></textarea>
<button class="px-3 py-1 bg-green-500 text-white rounded">Add Comment</button>
</form>
{% endif %}
<h3 class="font-semibold">Comments:</h3>
<ul>
{% for c in recipe.comments %}
<li>{{ c.author.username }} rated {{ c.rating }}: {{ c.text }}</li>
{% endfor %}
</ul>
{% endblock %}
""",
'add_recipe.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-2xl font-bold mb-4">Add Recipe</h1>
{% if error %}<p class="text-red-600">{{ error }}</p>{% endif %}
<form method="post" class="flex flex-col gap-2">
<input name="name" placeholder="Recipe name" class="p-2 border rounded w-full" required>
<input name="prep_time" placeholder="Prep time" class="p-2 border rounded w-full" required>
<input name="cuisine" placeholder="Cuisine" class="p-2 border rounded w-full" required>
<input name="tags" placeholder="Tags comma separated" class="p-2 border rounded w-full">
<textarea name="instructions" placeholder="Instructions" class="p-2 border rounded w-full" required></textarea>
<input name="ingredients" placeholder="Ingredients comma separated (amount name)" class="p-2 border rounded w-full" required>
<button class="px-3 py-1 bg-blue-600 text-white rounded">Add</button>
</form>
{% endblock %}
""",
'login.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-2xl font-bold mb-4">Login</h1>
{% if error %}<p class="text-red-600">{{ error }}</p>{% endif %}
<form method="post" class="flex flex-col gap-2">
<input name="username" placeholder="Username" class="p-2 border rounded" required>
<input type="password" name="password" placeholder="Password" class="p-2 border rounded" required>
<button class="px-3 py-1 bg-blue-600 text-white rounded">Login</button>
</form>
{% endblock %}
""",
'register.html':"""
{% extends "base.html" %}
{% block content %}
<h1 class="text-2xl font-bold mb-4">Register</h1>
{% if error %}<p class="text-red-600">{{ error }}</p>{% endif %}
<form method="post" class="flex flex-col gap-2">
<input name="username" placeholder="Username" class="p-2 border rounded" required>
<input name="email" placeholder="Email" class="p-2 border rounded" required>
<input type="password" name="password" placeholder="Password" class="p-2 border rounded" required>
<button class="px-3 py-1 bg-green-500 text-white rounded">Register</button>
</form>
{% endblock %}
"""
}

app.jinja_loader = DictLoader(templates)

# SEED 50 PRZEPISÓW Z NAZWAMI I POCHODZENIEM
def seed_data_full():
    if Recipe.query.first(): return
    user = User(username='chef', email='chef@cook.org')
    user.set_password('password')
    db.session.add(user)

    cuisines_list = ['Italian','Mexican','Indian','Thai','French','American','Mediterranean']
    recipe_names = [
        "Lemon Risotto","Chicken Tacos","Spaghetti Carbonara","Paneer Butter Masala","Pad Thai",
        "Beef Bourguignon","Chocolate Cake","Caesar Salad","Shakshuka","Guacamole","French Onion Soup",
        "Tom Yum Soup","Falafel Wrap","Mango Lassi","Pancakes","Fish Tacos","Vegetable Curry","Minestrone",
        "Creme Brulee","Chicken Parmesan","Biryani","Spring Rolls","Brownies","Pizza Margherita","Fettuccine Alfredo",
        "Gazpacho","Tiramisu","Samosa","Ratatouille","Clam Chowder","Stuffed Peppers","Pasta Primavera","Gnocchi",
        "Chili Con Carne","Bruschetta","Eggplant Parmesan","Moussaka","Butter Chicken","Apple Pie","Fajitas",
        "Lasagna","Tomato Soup","Pesto Pasta","Ceviche","Quiche Lorraine","Coconut Curry","Baklava","Pad See Ew","Carrot Cake","Chicken Curry"
    ]
    tags_list = ['Quick','Vegan','Dessert','Spicy']

    ingredients_list = [
        ('1–2','eggs'),
        ('1 cup','all-purpose flour'),
        ('1 cup','sugar'),
        ('1 teaspoon','salt'),
        ('1 cup','milk'),
        ('1 tablespoon','olive oil'),
        ('200 g','chicken breast'),
        ('1','onion, chopped'),
        ('2–3','cloves garlic, minced'),
        ('1 teaspoon','black pepper'),
        ('100 g','cheddar cheese, grated'),
        ('1 cup','rice'),
        ('200 g','spaghetti'),
        ('1 tablespoon','butter'),
        ('1','lemon, juiced')
    ]

    instructions_list = [
        "Prepare all ingredients.\nMix them together.\nCook according to recipe.\nServe hot.",
        "Chop vegetables.\nSaute in oil.\nAdd spices and cook.\nServe warm.",
        "Boil water.\nAdd main ingredients.\nSimmer for 15 minutes.\nGarnish and serve.",
        "Preheat oven.\nCombine ingredients.\nBake for 30 minutes.\nEnjoy hot."
    ]

    for i in range(50):
        rname = recipe_names[i]
        cuisine = random.choice(cuisines_list)
        r = Recipe(
            name=rname,
            instructions=random.choice(instructions_list),
            prep_time=f"{random.randint(10,90)} mins",
            author=user,
            cuisine=cuisine
        )
        num_ings = random.randint(3,6)
        chosen = random.sample(ingredients_list, num_ings)
        for amt,name in chosen:
            r.ingredients.append(Ingredient(name=name, amount=amt))
        num_tags = random.randint(1,2)
        for t in random.sample(tags_list,num_tags):
            tg = Tag.query.filter_by(name=t).first() or Tag(name=t)
            r.tags.append(tg)
            db.session.add(tg)
        db.session.add(r)
    db.session.commit()

# ROUTES
@app.route('/')
def index():
    popular = Recipe.query.limit(6).all()
    return render_template_string(templates['index.html'], popular=popular)

@app.route('/recipes')
def recipes():
    q=request.args.get('q','')
    tag=request.args.get('tag','')
    query=Recipe.query
    if q:
        query=query.filter(Recipe.name.ilike(f'%{q}%'))
    if tag:
        query=query.join(Recipe.tags).filter(Tag.name.ilike(f'%{tag}%'))
    results=query.all()
    return render_template_string(templates['recipes.html'], recipes=results)

@app.route('/recipe/<int:recipe_id>', methods=['GET','POST'])
def view_recipe(recipe_id):
    r=Recipe.query.get_or_404(recipe_id)
    if request.method=='POST' and current_user.is_authenticated:
        rating=int(request.form.get('rating',1))
        text=request.form.get('text','')
        c=Comment(recipe=r,author=current_user,rating=rating,text=text)
        db.session.add(c); db.session.commit()
    return render_template_string(templates['view_recipe.html'], recipe=r)

@app.route('/add', methods=['GET','POST'])
@login_required
def add_recipe():
    error=''
    if request.method=='POST':
        name=request.form.get('name','').strip()
        prep=request.form.get('prep_time','').strip()
        cuisine=request.form.get('cuisine','').strip()
        instr=request.form.get('instructions','').strip()
        tags=request.form.get('tags','').split(',')
        ings=request.form.get('ingredients','').split(',')
        if not all([name,prep,cuisine,instr,ings[0]]):
            error='Please fill out all fields'
            return render_template_string(templates['add_recipe.html'], error=error)
        r=Recipe(name=name,prep_time=prep,instructions=instr,author=current_user,cuisine=cuisine)
        for t in tags:
            t=t.strip()
            if not t: continue
            tg=Tag.query.filter_by(name=t).first() or Tag(name=t)
            r.tags.append(tg); db.session.add(tg)
        for i in ings:
            i=i.strip()
            if not i: continue
            parts=i.split(' ',1)
            amt,name=parts if len(parts)>1 else ('',parts[0])
            r.ingredients.append(Ingredient(name=name,amount=amt))
        db.session.add(r); db.session.commit()
        return redirect(url_for('view_recipe',recipe_id=r.id))
    return render_template_string(templates['add_recipe.html'], error=error)

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and u.check_password(request.form['password']):
            login_user(u)
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'
    return render_template_string(templates['login.html'], error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET','POST'])
def register():
    error=''
    if request.method=='POST':
        username=request.form.get('username','').strip()
        email=request.form.get('email','').strip()
        password=request.form.get('password','').strip()
        if not all([username,email,password]):
            error='Please fill out all fields'
            return render_template_string(templates['register.html'],error=error)
        if User.query.filter_by(username=username).first():
            error='Username already exists'
            return render_template_string(templates['register.html'],error=error)
        u=User(username=username,email=email)
        u.set_password(password)
        db.session.add(u); db.session.commit()
        login_user(u)
        return redirect(url_for('index'))
    return render_template_string(templates['register.html'],error=error)

@app.route('/download/<int:recipe_id>')
@login_required
def download_shopping_list(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Shopping List for {r.name}")
    y = 730
    for ing in r.ingredients:
        c.drawString(50, y, f"- {ing.amount} {ing.name}")
        y -= 20
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 750
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{r.name}_shopping_list.pdf", mimetype='application/pdf')

# INICJALIZACJA BAZY I SEED
with app.app_context():
    db.create_all()
    seed_data_full()

if __name__ == '__main__':
    app.run(debug=True)









