from flask import Flask, render_template, url_for, flash, redirect, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ---------------------------
# DATABASE MODELS
# ---------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    cart_items = db.relationship('Cart', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_per_kg = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    thawing_instructions = db.Column(db.Text, nullable=True)
    nutritional_info = db.Column(db.Text, nullable=True)
    is_bestseller = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    cart_items = db.relationship('Cart', backref='product', lazy=True)
    
    def __repr__(self):
        return f"Product('{self.name}', '{self.category}', ₹{self.price_per_kg}/kg)"

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"Cart('User: {self.user_id}', 'Product: {self.product_id}', '{self.quantity}kg')"

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    delivery_address = db.Column(db.String(200))
    payment_method = db.Column(db.String(50), default='Cash on Delivery')
    
    def __repr__(self):
        return f"Order('{self.id}', '{self.user_id}', '₹{self.total_amount}', '{self.status}')"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------
# FORMS
# ---------------------------
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=10)])
    address = StringField('Delivery Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please login instead.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AddToCartForm(FlaskForm):
    product_id = IntegerField('Product ID', validators=[DataRequired()])
    quantity = FloatField('Quantity (kg)', validators=[DataRequired()], default=1.0)
    submit = SubmitField('Add to Cart')

# ---------------------------
# ROUTES
# ---------------------------
@app.route('/')
def home():
    products = Product.query.limit(6).all()
    featured_products = Product.query.filter_by(is_bestseller=True).limit(3).all()
    return render_template('index.html', 
                         products=products, 
                         featured_products=featured_products,
                         title='Frozen Kadai - Farm Frozen, Chef Ready')

@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    if category and category != 'all':
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    return render_template('products.html', 
                         products=products, 
                         categories=[c[0] for c in categories],
                         current_category=category,
                         title='Our Frozen Products')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category=product.category).filter(Product.id != product_id).limit(4).all()
    form = AddToCartForm()
    return render_template('product_detail.html', 
                         product=product, 
                         related_products=related_products,
                         form=form,
                         title=product.name)

@app.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1.0, type=float)
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Product added to cart successfully!', 'success')
    
    return redirect(request.referrer or url_for('products'))

@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price_per_kg * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, title='Your Cart')

@app.route('/update-cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_quantity = data.get('quantity')
    
    if new_quantity and new_quantity > 0:
        cart_item.quantity = new_quantity
        db.session.commit()
        return jsonify({'success': True})
    elif new_quantity == 0:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'success': True, 'removed': True})
    
    return jsonify({'error': 'Invalid quantity'}), 400

@app.route('/remove-from-cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('products'))
    
    total = sum(item.product.price_per_kg * item.quantity for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total, title='Checkout')

@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('products'))
    
    total = sum(item.product.price_per_kg * item.quantity for item in cart_items)
    order = Order(user_id=current_user.id, total_amount=total, status='Pending', delivery_address=current_user.address)
    db.session.add(order)
    
    for item in cart_items:
        db.session.delete(item)
    
    db.session.commit()
    flash('Order placed successfully! Our team will contact you for delivery confirmation.', 'success')
    return redirect(url_for('products'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('login.html', form=form, title='Login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html', form=form, title='Sign Up')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html', title='About Us')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Here you would typically send an email or save to database
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', title='Contact Us')

@app.route('/set-location', methods=['POST'])
def set_location():
    data = request.get_json()
    if data and 'location' in data:
        session['delivery_location'] = data['location']
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid location'}), 400

# ---------------------------
# DATABASE INITIALIZATION
# ---------------------------
def init_db():
    """Initialize database with sample products"""
    with app.app_context():
        db.create_all()
        
        if Product.query.count() == 0:
            sample_products = [
                Product(name='Frozen Whole Chicken (Farm Fresh)', 
                       description='Whole chicken, farm-frozen at peak freshness. Perfect for roasting or curries.', 
                       price_per_kg=280, 
                       category='Whole Chicken',
                       image_file='holep1.png',
                       stock_status='In Stock',
                       thawing_instructions='Refrigerator: 24 hours | Cold water: 2-3 hours (change water every 30 mins)',
                       nutritional_info='High protein, source of iron and B vitamins. Per 100g: Protein 25g, Fat 8g',
                       is_bestseller=True),
                
                Product(name='Premium Frozen Chicken Breast (Boneless)', 
                       description='Boneless, skinless chicken breast. IQF frozen for easy portion control.', 
                       price_per_kg=450, 
                       category='Chicken',
                       image_file='chicken-breast.jpg',
                       stock_status='In Stock',
                       thawing_instructions='Refrigerator: 12 hours | Quick thaw: 1 hour in cold water',
                       nutritional_info='Lean protein. Per 100g: Protein 31g, Fat 3.6g',
                       is_bestseller=True),
                
                Product(name='Chicken Nuggets (Classic Breaded)', 
                       description='Restaurant-style chicken nuggets. Made from premium chicken breast meat.', 
                       price_per_kg=550, 
                       category='Ready-to-Cook',
                       image_file='nuggets.jpg',
                       stock_status='Limited Stock',
                       thawing_instructions='Cook from frozen. No need to thaw.',
                       nutritional_info='Per 100g: Protein 15g, Fat 12g, Carbs 18g',
                       is_bestseller=False),
                
                Product(name='IQF Chicken Wings (Party Pack)', 
                       description='Individually Quick Frozen chicken wings. Perfect for frying or baking.', 
                       price_per_kg=380, 
                       category='Chicken',
                       image_file='wings.jpg',
                       stock_status='In Stock',
                       thawing_instructions='Refrigerator: 8-10 hours | Cook from frozen (add 5-7 mins to cooking time)',
                       nutritional_info='Per 100g: Protein 22g, Fat 14g',
                       is_bestseller=True),
            ]
            
            for product in sample_products:
                db.session.add(product)
            
            db.session.commit()
            print("Database initialized with sample products!")

# Add these admin routes to app.py

# Admin required decorator
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'admin':  # Simple admin check
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Dashboard
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Get statistics
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()
    
    # Get low stock products
    low_stock_products = Product.query.filter_by(stock_status='Limited Stock').all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products,
                         title='Admin Dashboard')

# Admin - Users Management
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, title='Manage Users')

# Admin - Delete User
@app.route('/admin/users/delete/<int:user_id>')
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot delete admin user!', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin_users'))

# Admin - Orders Management
@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin/orders.html', orders=orders, title='Manage Orders')

# Admin - Update Order Status
@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_order(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.id} status updated to {new_status}.', 'success')
    return redirect(url_for('admin_orders'))

# Admin - Products Management
@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products, title='Manage Products')

# Admin - Add Product
@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_product():
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price_per_kg=float(request.form['price_per_kg']),
            category=request.form['category'],
            image_file=request.form['image_file'] or 'default.jpg',
            stock_status=request.form['stock_status'],
            thawing_instructions=request.form['thawing_instructions'],
            nutritional_info=request.form['nutritional_info'],
            is_bestseller=bool(request.form.get('is_bestseller'))
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/add_product.html', title='Add Product')

# Admin - Edit Product
@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price_per_kg = float(request.form['price_per_kg'])
        product.category = request.form['category']
        product.image_file = request.form['image_file'] or product.image_file
        product.stock_status = request.form['stock_status']
        product.thawing_instructions = request.form['thawing_instructions']
        product.nutritional_info = request.form['nutritional_info']
        product.is_bestseller = bool(request.form.get('is_bestseller'))
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/edit_product.html', product=product, title='Edit Product')

# Admin - Delete Product
@app.route('/admin/products/delete/<int:product_id>')
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Admin - Settings
@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings():
    return render_template('admin/settings.html', title='Admin Settings')            

if __name__ == '__main__':
    init_db()
    app.run(debug=True)