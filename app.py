
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime



app = Flask(__name__)
app.config['SECRET_KEY'] = 'our-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = '''
postgresql://mini_market_db_xjm2_user:6HDum5cB1P3IlFyqv2RcRD2TFeXCWpp
T@dpg-d2tveker433s73dq2kt0-a.singapore-postgres.render.com/mini_market_db_xjm2'''
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), default="New User")
    avatar_url = db.Column(db.String(255), default="https://api.dicebear.com/9.x/identicon/svg?seed=user")
    phone = db.Column(db.String(50), default="")
    address = db.Column(db.String(255), default="")

    products = db.relationship('Product', backref='owner', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    purchases = db.relationship('Purchase', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), default="https://placehold.co/600x400?text=Product+Image")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    qty = db.Column(db.Integer, default=1)

    product = db.relationship('Product')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')

# ----------------- Helpers -----------------

def current_user():
    uid = session.get('user_id')
    if uid is None:
        return None
    return User.query.get(uid)

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {
        'current_user': current_user()
    }

# ----------------- Auth -----------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('signup'))
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        print(user.id)
        session['user_id'] = user.id
        flash('Welcome! Account created.', 'success')
        return redirect(url_for('feed'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            next_url = request.args.get('next') or url_for('feed')
            return redirect(next_url)
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


# ----------------- Core Pages -----------------
@app.route('/')
def feed():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = Product.query.order_by(Product.created_at.desc())
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%"))
    if category:
        query = query.filter_by(category=category)
    products = query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    return render_template('feed.html', products=products, categories=categories, selected_category=category, q=q)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        title = request.form['title'].strip()
        category = request.form['category'].strip() or "General"
        description = request.form['description'].strip()
        price = float(request.form['price'])
        image_url = request.form.get('image_url', '').strip() or "https://placehold.co/600x400?text=Product+Image"
        prod = Product(title=title, category=category, description=description, price=price, image_url=image_url, owner_id=current_user().id)
        db.session.add(prod)
        db.session.commit()
        flash('Listing added!', 'success')
        return redirect(url_for('my_listings'))
    categories = ["Electronics", "Books", "Fashion", "Home", "Toys", "General"]
    return render_template('add_product.html', categories=categories)

@app.route('/my-listings')
@login_required
def my_listings():
    products = Product.query.filter_by(owner_id=current_user().id).order_by(Product.created_at.desc()).all()
    return render_template('my_listings.html', products=products)

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.owner_id != current_user().id:
        flash("You can't edit this product.", 'danger')
        return redirect(url_for('my_listings'))
    if request.method == 'POST':
        product.title = request.form['title'].strip()
        product.category = request.form['category'].strip()
        product.description = request.form['description'].strip()
        product.price = float(request.form['price'])
        product.image_url = request.form.get('image_url', '').strip() or product.image_url
        db.session.commit()
        flash('Listing updated.', 'success')
        return redirect(url_for('my_listings'))
    categories = ["Electronics", "Books", "Fashion", "Home", "Toys", "General"]
    return render_template('add_product.html', categories=categories, product=product, editing=True)

@app.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.owner_id != current_user().id:
        flash("You can't delete this product.", 'danger')
        return redirect(url_for('my_listings'))
    db.session.delete(product)
    db.session.commit()
    flash('Listing deleted.', 'info')
    return redirect(url_for('my_listings'))


# ----------------- Cart & Purchases -----------------
@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user().id).all()
    total = sum(i.qty * i.product.price for i in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:product_id>')
@login_required
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    item = CartItem.query.filter_by(user_id=current_user().id, product_id=product.id).first()
    if item:
        item.qty += 1
    else:
        item = CartItem(user_id=current_user().id, product_id=product.id, qty=1)
        db.session.add(item)
    db.session.commit()
    flash('Added to cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user().id:
        flash("You can't modify this cart.", 'danger')
        return redirect(url_for('cart'))
    db.session.delete(item)
    db.session.commit()
    flash('Removed from cart.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user().id).all()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))
    for item in items:
        for _ in range(item.qty):
            purchase = Purchase(user_id=current_user().id, product_id=item.product_id, price_at_purchase=item.product.price)
            db.session.add(purchase)
        db.session.delete(item)
    db.session.commit()
    flash('Purchase complete!', 'success')
    return redirect(url_for('purchases'))

@app.route('/purchases')
@login_required
def purchases():
    user = current_user()
    purchases = Purchase.query.filter_by(user_id=user.id).order_by(Purchase.purchased_at.desc()).all()
    return render_template('purchases.html', purchases=purchases)


# ----------------- Dashboard -----------------
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = current_user()
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.phone = request.form.get('phone', user.phone)
        user.address = request.form.get('address', user.address)
        user.avatar_url = request.form.get('avatar_url', user.avatar_url)
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('dashboard.html', user=user)


# ----------------- CLI Helper -----------------
@app.cli.command('initdb')
def initdb():
    "Initialize the database and create some random data."
    db.create_all()
    if not User.query.filter_by(email='demo@example.com').first():
        demo = User(email='demo@example.com', password_hash=generate_password_hash('password'), name='Demo User')
        db.session.add(demo)
        db.session.commit()
        p1 = Product(title='Vintage Camera', category='Electronics', description='A classic film camera.', price=149.99, owner_id=demo.id)
        p2 = Product(title='Cozy Sweater', category='Fashion', description='Warm and comfy.', price=39.99, owner_id=demo.id)
        db.session.add_all([p1, p2])
        db.session.commit()
    print("Database initialized. Run with: flask --app app run --debug")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
