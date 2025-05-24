from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timedelta
import os
import functools

from models import db, User

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(days=7)

# Initialize database with app
db.init_app(app)

# Custom login_required decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login_signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        session['user_fullname'] = user.fullname

        if remember:
            session.permanent = True

        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login_signup.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'danger')
            return redirect(url_for('signup'))

        new_user = User(
            fullname=fullname,
            email=email,
            role=role,
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('login_signup.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def dashboard():
    role = session.get('user_role')
    user_id = session.get('user_id')
    if role == 'admin':
        user = User.query.get(user_id)  # Fetch user from DB
        return render_template('admin/admin_dashboard.html', user=user, active_page='dashboard')
    else:
        return redirect(url_for('user_dashboard'))
# Admin and feature pages
@app.route('/admin')
def admin():
   if 'user_id' in session:
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def user_dashboard():
    menu_items = [
        {
            "name": "Chicken Mo:Mo",
            "price": 150.00,
            "image": "static/img/chicken_momo.jpeg",
            "category": "momo",
            "is_popular": True,
            "category":"Dinner"
        },
        {
            "name": "Veg Chowmein",
            "price": 120.00,
            "image": "veg_chowmein.jpg",
            "category": "noodles",
            "is_popular": False,
            "category":"Dinner"
        },
        {
            "name": "Buff Burger",
            "price": 180.00,
            "image": "buff_burger.jpg",
            "category": "burger",
            "is_popular": True
        },
        {
            "name": "French Fries",
            "price": 100.00,
            "image": "french_fries.jpg",
            "category": "snacks",
            "is_popular": False
        },
        {
            "name": "Masala Tea",
            "price": 40.00,
            "image": "masala_tea.jpg",
            "category": "beverages",
            "is_popular": True
        }
    ]
    user_id = session.get('user_id')
    if 'user_id' in session:
        user= User.query.get(user_id)
        return render_template('index.html',user=user,active_page='dashboard',menu_items=menu_items)
    return render_template('login_signup.html')

@app.route('/admin/categories')
def categories():
    categories = [
        {'name': 'Beverages', 'items_count': 12, 'is_active': True},
        {'name': 'Snacks', 'items_count': 8, 'is_active': False},
        {'name': 'Main Course', 'items_count': 15, 'is_active': True},
        {'name': 'Desserts', 'items_count': 5, 'is_active': True},
        {'name': 'Frozen Items', 'items_count': 4, 'is_active': False}
    ]
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id) # Assuming you have a Category model
        return render_template('admin/categories.html', categories=categories, user=user, active_page='categories')
    else:
        return redirect(url_for('login'))
   

@app.route('/admin/attributes')
def attribute():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('admin/attribute.html', user=user, active_page='attributes')

@app.route('/admin/units')
def units():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('admin/units.html', user=user, active_page='units')

@app.route('/admin/addons')
def addons():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('admin/addons.html', user=user, active_page='addons')

@app.route('/admin/items')
def items():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('admin/items.html', user=user, active_page='items')

@app.route('/admin/menu')
def menu():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('admin/admin_menu.html', user=user,active_page='menu')
@app.route('/admin/orders')
def admin_orders():
    orders = [
        {
            "id": 101,
            "customer_name": "Aayush K.",
            "item": {
                "name": "Chicken Sandwich",
                "category": "Lunch",
                "attribute": "Grilled",
                "unit": "Plate"
            },
            "addons": ["Cheese", "Extra Mayo"],
            "quantity": 2,
            "total_price": 11.98,
            "status": "Completed"
        },
        {
            "id": 102,
            "customer_name": "Sneha T.",
            "item": {
                "name": "Pancakes",
                "category": "Breakfast",
                "attribute": "Fluffy",
                "unit": "Stack"
            },
            "addons": ["Maple Syrup"],
            "quantity": 1,
            "total_price": 5.50,
            "status": "Pending"
        }
    ]

    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template("admin/admin_orders.html", user=user, orders=orders)
    else:
        return redirect(url_for('login'))  
    
@app.route('/notifications')
def get_notifications():
    # Replace with DB query in real app
    notifications = [
        {"message": "🍔 Your Order is being prepared" ,"time": datetime.now().strftime("%I:%M %p")},
        {"message": "⚠️ Your Order is canceled", "time": datetime.now().strftime("%I:%M %p")},
        {"message": "✅ Your order is delivered", "time": datetime.now().strftime("%I:%M %p")},
    ]
    return jsonify(notifications)


@app.route('/orders')
def orders():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('orders.html',user=user, active_page='orders')
    else:
        return redirect(url_for('login'))  

@app.route('/menu')
def user_menu():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('menu.html', user=user,active_page='menu')
    else:
        return redirect(url_for('login'))

@app.route('/transation_history')
def transaction():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('transaction_history.html',user=user, active_page='transaction')
    else:
        return redirect(url_for('login'))


@app.route('/cart')
def cart():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('cart.html', user=user,active_page='settings')
    else:
        return redirect(url_for('login'))
@app.route('/profile')
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('profile.html', user=user,active_page='profile')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
