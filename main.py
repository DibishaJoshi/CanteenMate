from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime,timedelta,date,time
from flask_socketio import SocketIO,join_room, leave_room
from sqlalchemy import func, desc, asc,and_
import recommendation
from pytz import timezone


import os
import functools
import re
import hashlib
import hmac
import base64
import json
import requests
import uuid
import traceback

from models import db, User, Category, Item, Attribute, AttributeValue ,Menu, Order, OrderItem,Review, ReviewHelpful, Addon, CartItem
from models import addon_item_association, OrderAddon, Payment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dibisha'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['KHALTI_PUBLIC_KEY'] = "test_public_key_dc74e0fd57cb46cd93832aee0a507256"

app.permanent_session_lifetime = timedelta(days=7)
socketio = SocketIO(app, cors_allowed_origins="*")

KHALTI_INITIATE_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
KHALTI_SECRET_KEY = "key live_secret_key_68791341fdd94846a146f0457ff7b455"

# eSewa ePay v2 Configuration
ESEWA_MERCHANT_CODE = "EPAYTEST"  # Use EPAYTEST for testing
ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"  # Test secret key for EPAYTEST
ESEWA_BASE_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2"  # Production URL with test credentials


# Initialize database with app
db.init_app(app)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/recommendations')
@login_required
def recommendations_page():
    user = User.query.get(session['user_id'])

    user_item_matrix, _ = recommendation.build_user_item_matrix()
    if user_item_matrix is None:
        return "<h3>No order data available for recommendations.</h3>"

    model, k = recommendation.train_knn(user_item_matrix)
    items = recommendation.recommend_items_for_user(user, user_item_matrix, model, n_neighbors=k)

    return render_template('recommendations.html', items=items)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login_signup.html',show_form='login')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Email and password are required.', 'warning')
            return redirect(url_for('login'))
        if '@' not in email or '.' not in email:
            flash("Enter a valid Email address.",'warning')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return redirect(url_for('login'))

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
    return render_template('login_signup.html', show_form='login')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check required fields
        if not fullname or not email or not password or not confirm_password:
            flash('All fields are required.', 'warning')
            return redirect(url_for('signup'))
        
        if '@' not in email and '.' not in email:
            flash("Enter a valid Email address.",'warning')
            return redirect(url_for('signup'))

        # Password validations
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already exists.', 'danger')
            return redirect(url_for('signup'))

        # Always assign role = 'user'
        new_user = User(
            fullname=fullname,
            email=email,
            role='user',
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('login_signup.html', show_form='signup')


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
        user = User.query.get(user_id) 
        total_items = Item.query.count()
        total_customers = User.query.filter(User.role != 'admin').count()
        today = date.today()

        # Create datetime range for today (00:00:00 to 23:59:59.999999)
        start_datetime = datetime.combine(today, time.min)
        end_datetime = datetime.combine(today, time.max)

        todays_orders = Order.query.filter(
            Order.created_at >= start_datetime,
            Order.created_at <= end_datetime
        ).all()

        todays_orders_count = len(todays_orders)  # <-- Add this line

        todays_revenue = sum(order.total_amount for order in todays_orders)

        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

        popular_items = db.session.query(
            OrderItem.item_id,
            OrderItem.name,
            db.func.count(OrderItem.item_id).label('count')
        ).group_by(OrderItem.item_id).order_by(db.desc('count')).limit(5).all()

        order_status_counts = db.session.query(
            Order.status, db.func.count(Order.id)
        ).group_by(Order.status).all()

        return render_template('admin/admin_dashboard.html',
                               user=user,
                               active_page='dashboard',
                               total_items=total_items,
                               total_customers=total_customers,
                               todays_orders_count=todays_orders_count,
                               todays_revenue=todays_revenue,
                               recent_orders=recent_orders,
                               popular_items=popular_items,
                               order_status_counts=dict(order_status_counts))
    else:
        return redirect(url_for('user_dashboard'))

@app.route('/admin')
@login_required
def admin():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def user_dashboard():
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return redirect(url_for('login'))
    
    user_item_matrix, df = recommendation.build_user_item_matrix()
    
    recommendation_context = recommendation.get_user_order_history_explanation(user_id)
    
    if user_item_matrix is None or user_item_matrix.empty:
        menu_recommendations = recommendation.get_fallback_recommendations_with_explanations()
        recommendation_type = "popular"
    else:
        model, k = recommendation.train_knn(user_item_matrix)
        
        if model is None or k == 0:
            menu_recommendations = recommendation.get_fallback_recommendations_with_explanations()
            recommendation_type = "popular"
        else:
            menu_recommendations = recommendation.recommend_items_for_user_with_explanations(
                user_id, 
                user_item_matrix, 
                model, 
                n_neighbors=k,
                top_n=5
            )
            if not menu_recommendations:
                menu_recommendations = recommendation.get_fallback_recommendations_with_explanations()
                recommendation_type = "popular"
            else:
                recommendation_type = "personalized"
    
    menu_items = [rec['item'] for rec in menu_recommendations]
    
    customers = []  
    cart_items = []  
    categories = Category.query.all()
    return render_template('index.html', 
                         menu_items=menu_items,
                         menu_recommendations=menu_recommendations,  # Full recommendation data with explanations
                         recommendation_context=recommendation_context,
                         recommendation_type=recommendation_type,
                         user=user,
                         customers=customers,
                         cart_items=cart_items,
                         active_page="dashboard", categories=categories)

@app.route('/admin/categories')
@login_required
def categories():
    categories = Category.query.all()
    user = User.query.get(session['user_id'])
    return render_template('admin/categories.html', categories=categories, user=user, active_page='categories')
@app.route('/admin/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    status_str = request.form.get('status', 'inactive')
    status = True if status_str == 'active' else False

    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('categories'))

    new_category = Category(name=name, status=status)
    db.session.add(new_category)
    db.session.commit()

    flash('Category added successfully!', 'success')
    return redirect(url_for('categories'))

@app.route('/admin/categories/edit/<int:id>', methods=['POST'])
def edit_category(id):
    category = Category.query.get_or_404(id)
    category.name = request.form['name']
    category.status = request.form['status'] == 'active'
    db.session.commit()

    return redirect(url_for('categories'))


# def categories():
#     categories = [
#         {'name': 'Beverages', 'items_count': 12, 'is_active': True},
#         {'name': 'Snacks', 'items_count': 8, 'is_active': False},
#         {'name': 'Main Course', 'items_count': 15, 'is_active': True},
#         {'name': 'Desserts', 'items_count': 5, 'is_active': True},
#         {'name': 'Frozen Items', 'items_count': 4, 'is_active': False}
#     ]
#     if 'user_id' in session:
#         user_id = session['user_id']
#         user = User.query.get(user_id) # Assuming you have a Category model
#         return render_template('admin/categories.html', categories=categories, user=user, active_page='categories')
#     else:
#         return redirect(url_for('login'))
   

@app.route('/admin/attributes')
@login_required
def attribute():
    user_id = session['user_id']
    user = User.query.get(user_id)
    attributes = Attribute.query.all()
    return render_template('admin/attribute.html',attributes=attributes, user=user, active_page='attributes')
@app.route('/admin/attributes', methods=['GET', 'POST'])
@login_required
def manage_attributes():
    user_id = session['user_id']
    user = User.query.get(user_id)
    attributes = Attribute.query.all()

    if request.method == 'POST':
        attribute_id = request.form.get('attribute_id')
        name = request.form.get('attribute_name')
        status = True if request.form.get('status') == 'active' else False
        value_names = request.form.getlist('value_name[]')
        price_adjustments = request.form.getlist('price_adjustment[]')

        if not name:
            flash("Attribute name is required.", "attribute_error")
            return redirect(url_for('manage_attributes'))

        if attribute_id:
            # Update existing attribute
            attribute = Attribute.query.get(attribute_id)
            if attribute:
                attribute.name = name
                attribute.status = status

                # Delete old values
                AttributeValue.query.filter_by(attribute_id=attribute.id).delete()

                # Add new values
                for vname, padj in zip(value_names, price_adjustments):
                    if vname.strip():
                        try:
                            padj_float = float(padj)
                        except ValueError:
                            padj_float = 0.0
                        db.session.add(AttributeValue(
                            value=vname.strip(),
                            price_adjustment=padj_float,
                            attribute_id=attribute.id
                        ))

                db.session.commit()  # ✅ Commit only once after adding new values
                flash('Attribute updated successfully', 'attribute_success')
                return redirect(url_for('attribute'))
        else:
            # Create new attribute
            new_attr = Attribute(name=name, status=status)
            db.session.add(new_attr)
            db.session.flush()  # Get new_attr.id without full commit

            for vname, padj in zip(value_names, price_adjustments):
                if vname.strip():
                    try:
                        padj_float = float(padj)
                    except ValueError:
                        padj_float = 0.0
                    db.session.add(AttributeValue(
                        value=vname.strip(),
                        price_adjustment=padj_float,
                        attribute_id=new_attr.id
                    ))

            db.session.commit()
            flash('Attribute added successfully', 'attribute_success')
            return redirect(url_for('attribute'))

    return render_template('admin/attribute.html', attributes=attributes, user=user, active_page='attributes')

@app.route('/admin/units')
@login_required
def units():
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('admin/units.html', user=user, active_page='units')

@app.route('/admin/addons')
@login_required
def addons():
    user_id = session['user_id']
    user = User.query.get(user_id)
    addons = Addon.query.all()
    return render_template('admin/addons.html', user=user, addons=addons, active_page='addons')


@app.route('/admin/addons/add', methods=['POST'])
@login_required
def add_addon():
    name = request.form.get('addonName')
    price = request.form.get('addonPrice')
    category = request.form.get('addonCategory')
    description = request.form.get('addonDescription')
    status = request.form.get('status', 'active') == 'active'

    if not name or not price or not category:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('addons'))

    new_addon = Addon(
        name=name,
        price=float(price),
        category=category,
        description=description,
        status=status
    )
    db.session.add(new_addon)
    db.session.commit()

    flash('Addon added successfully!', 'addon_success')
    return redirect(url_for('addons'))

@app.route('/admin/addons/edit/<int:addon_id>', methods=['POST'])
@login_required
def edit_addon(addon_id):
    addon = Addon.query.get_or_404(addon_id)

    name = request.form.get('addonName')
    price_str = request.form.get('addonPrice')
    category = request.form.get('addonCategory')
    description = request.form.get('addonDescription')
    status = request.form.get('status', 'active') == 'active'

    # Basic validation
    if not name or not price_str or not category:
        flash('Please fill in all required fields.', 'addon_danger')
        return redirect(url_for('addons'))

    try:
        price = float(price_str)
    except ValueError:
        flash('Price must be a valid number.', 'addon_danger')
        return redirect(url_for('addons'))

    # Update addon
    addon.name = name
    addon.price = price
    addon.category = category
    addon.description = description
    addon.status = status

    db.session.commit()
    flash('Addon updated successfully!', 'addon_success')
    return redirect(url_for('addons'))


@app.route('/admin/addons/delete/<int:addon_id>', methods=['POST'])
@login_required
def delete_addon(addon_id):
    addon = Addon.query.get_or_404(addon_id)
    db.session.delete(addon)
    db.session.commit()
    flash('Addon deleted successfully.', 'addon_success')
    return redirect(url_for('addons'))




@app.route('/admin/items')
@login_required
def items():
    user_id = session['user_id']
    user = User.query.get(user_id)
    categories = Category.query.filter_by(status=True).all()
    addons = Addon.query.filter_by(status=True).all()
    items = Item.query.all() 
    return render_template('admin/items.html', categories=categories, user=user, items=items, active_page='items',addons=addons)

@app.route('/admin/add-item', methods=['POST'])
@login_required
def add_item():
    item_id = request.form.get('item-id')  
    name = request.form.get('item-name')
    category_name = request.form.get('item-category')
    price = request.form.get('item-price')
    description = request.form.get('item-description')
    available = request.form.get('item-available') == 'on'
    image = request.files.get('item-image')
    addon_ids = request.form.getlist('item-addons')

    if not name or not category_name or not price:
        flash("Please fill in all required fields.", "items_danger")
        return redirect(url_for('items'))

    category = Category.query.filter_by(name=category_name).first()
    if not category:
        flash("Invalid category selected.", "items_danger")
        return redirect(url_for('items'))

    image_filename = None
    if image and '.' in image.filename:
        ext = image.filename.rsplit('.', 1)[1].lower()
        if ext in {'png', 'jpg', 'jpeg', 'gif'}:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.root_path, 'static/uploads/items', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
            image_filename = filename

    # Load selected Addons as objects
    selected_addons = []
    if addon_ids:
        selected_addons = Addon.query.filter(Addon.id.in_(addon_ids)).all()

    if item_id:
        # Edit existing item
        item = Item.query.get(int(item_id))
        if not item:
            flash("Item not found.", "items_danger")
            return redirect(url_for('items'))

        item.name = name
        item.category_id = category.id
        item.price = float(price)
        item.description = description
        item.available = available

        if image_filename:
            item.image_filename = image_filename

        # Update addons association
        item.addons = selected_addons

        db.session.commit()
        flash("Item updated successfully!", "items_success")

    else:
        # Add new item
        new_item = Item(
            name=name,
            price=float(price),
            category_id=category.id,
            description=description,
            available=available,
            image_filename=image_filename,
            addons=selected_addons
        )
        db.session.add(new_item)
        db.session.commit()
        flash("Item added successfully!", "items_success")

    return redirect(url_for('items'))
# @app.route('/update_cart_addons', methods=['POST'])
# @login_required
# def update_cart_addons():
#     cart_id = request.form.get('cart_id')
#     selected_addon_ids = request.form.getlist('addon_ids')
    
#     # Update cart with selected addons
#     # Store addon selections in session or database
    
#     return redirect(url_for('cart'))

@app.route('/admin/menu')
@login_required
def menu():
    user_id = session['user_id']
    user = User.query.get(user_id)

    categories = Category.query.filter_by(status=True).all()
    available_items = Item.query.filter_by(available=True).all()
    current_day = request.args.get('day', 'monday')

    menu_items = {}
    for category in categories:
        menu_items[category.name] = []

    menu_entries = Menu.query.filter_by(day=current_day).all()
    for entry in menu_entries:
        if entry.category.name not in menu_items:
            menu_items[entry.category.name] = []
        menu_items[entry.category.name].append(entry.item)

    return render_template('admin/admin_menu.html', 
                           user=user, 
                           active_page='menu',
                           categories=categories,
                           available_items=available_items,
                           menu_items=menu_items,
                           current_day=current_day)

@app.route('/admin/menu/add_items', methods=['POST'])
@login_required
def add_menu_items():
    """Add selected items to menu for specific day and category"""
    try:
        day = request.form.get('day', 'monday')
        category_name = request.form.get('category')
        selected_items = request.form.getlist('selected_items')
        
        if not category_name or not selected_items:
            flash('Please select a category and at least one item.', 'menu_danger')
            return redirect(url_for('menu'))
        
        # Get category
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            flash('Invalid category selected.', 'menu_danger')
            return redirect(url_for('menu'))
        
        # Add items to menu (if using Menu model)
        added_count = 0
        for item_id in selected_items:
            item = Item.query.get(item_id)
            if item:
                # Check if item already exists in menu for this day/category
                existing = Menu.query.filter_by(day=day, category_id=category.id, item_id=item.id).first()
                if not existing:
                    new_menu_item = Menu(day=day, category_id=category.id, item_id=item.id)
                    db.session.add(new_menu_item)
                    added_count += 1
                # added_count += 1
        
        db.session.commit()
        
        if added_count > 0:
            flash(f'Successfully added {added_count} items to {category_name} menu for {day.title()}.', 'menu_success')
        else:
            flash('No new items were added. Items may already exist in the menu.', 'menu_warning')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while adding items to menu.', 'menu_danger')
    
    return redirect(url_for('menu') + f'?day={day}')

@app.route('/admin/menu/remove_item', methods=['POST'])
@login_required
def remove_menu_item():
    """Remove an item from the menu"""
    try:
        day = request.form.get('day', 'monday')
        item_id = request.form.get('item_id')
        category_id = request.form.get('category_id')
        
        if not item_id or not category_id:
            flash('Invalid item or category.', 'menu_danger')
            return redirect(url_for('menu'))
        
        # Remove item from menu (if using Menu model)
        menu_item = Menu.query.filter_by(day=day, category_id=category_id, item_id=item_id).first()
        if menu_item:
            db.session.delete(menu_item)
            db.session.commit()
            flash('Item removed from menu successfully.', 'menu_success')
        else:
            flash('Item not found in menu.', 'menu_warning')
        
        
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while removing item from menu.', 'menu_danger')
    
    return redirect(url_for('menu') + f'?day={day}')

@app.route('/admin/menu/search')
@login_required
def search_menu():
    """Search menu items"""
    search_query = request.args.get('q', '').strip()
    day = request.args.get('day', 'monday')
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    categories = Category.query.filter_by(status=True).all()
    available_items = Item.query.filter_by(available=True).all()
    
    menu_items = {}
    
    if search_query:
        # Search in menu items
        # If using Menu model:
        search_results = db.session.query(Menu).join(Item).filter(
            Menu.day == day,
            Item.name.ilike(f'%{search_query}%')
        ).all()
        
        # For demo, search in all items
        # search_results = Item.query.filter(
        #     Item.name.ilike(f'%{search_query}%'),
        #     Item.available == True
        # ).all()
        
        # Group by category
        for menu_entry in search_results:
            item = menu_entry.item
            category_name = item.category.name if item.category else 'Other'
            if category_name not in menu_items:
                menu_items[category_name] = []
            menu_items[category_name].append(item)

    else:
        # Return all menu items for the day
        return redirect(url_for('menu') + f'?day={day}')
    
    return render_template('admin/admin_menu.html', 
                         user=user, 
                         active_page='menu',
                         categories=categories,
                         available_items=available_items,
                         menu_items=menu_items,
                         current_day=day,
                         search_query=search_query)

@app.route('/admin/menu/copy_day', methods=['POST'])
@login_required
def copy_menu_day():
    """Copy menu from one day to another"""
    try:
        source_day = request.form.get('source_day')
        target_day = request.form.get('target_day')
        
        if not source_day or not target_day:
            flash('Please select both source and target days.', 'menu_danger')
            return redirect(url_for('menu'))
        
        if source_day == target_day:
            flash('Source and target days cannot be the same.', 'menu_warning')
            return redirect(url_for('menu'))
        
        # Copy menu items (if using Menu model)
        source_items = Menu.query.filter_by(day=source_day).all()
        copied_count = 0
        
        for source_item in source_items:
            # Check if item already exists for target day
            existing = Menu.query.filter_by(
                day=target_day, 
                category_id=source_item.category_id, 
                item_id=source_item.item_id
            ).first()
            
            if not existing:
                new_menu_item = Menu(
                    day=target_day,
                    category_id=source_item.category_id,
                    item_id=source_item.item_id
                )
                db.session.add(new_menu_item)
                copied_count += 1
        
        db.session.commit()
        
        # For demo
        # copied_count = 5
        
        if copied_count > 0:
            flash(f'Successfully copied {copied_count} items from {source_day.title()} to {target_day.title()}.', 'menu_success')
        else:
            flash(f'No new items to copy. {target_day.title()} may already have all items from {source_day.title()}.', 'menu_warning')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while copying menu.', 'menu_danger')
    
    return redirect(url_for('menu') + f'?day={target_day}')

@app.route('/admin/menu/clear_day', methods=['POST'])
@login_required
def clear_menu_day():
    """Clear all menu items for a specific day"""
    try:
        day = request.form.get('day')
        
        if not day:
            flash('Please specify a day to clear.', 'menu_danger')
            return redirect(url_for('menu'))
        
        # Clear menu items for the day (if using Menu model)
        deleted_count = Menu.query.filter_by(day=day).count()
        Menu.query.filter_by(day=day).delete()
        db.session.commit()
        
        # For demo
        # deleted_count = 8
        
        flash(f'Successfully cleared {deleted_count} items from {day.title()} menu.', 'menu_success')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while clearing menu.', 'menu_danger')
    
    return redirect(url_for('menu') + f'?day={day}')

@app.route('/admin/menu/toggle_category', methods=['POST'])
@login_required
def toggle_menu_category():
    """Toggle visibility of a category in menu"""
    try:
        category_id = request.form.get('category_id')
        day = request.form.get('day', 'monday')
        action = request.form.get('action')  # 'show' or 'hide'
        
        category = Category.query.get(category_id)
        if not category:
            flash('Category not found.', 'menu_danger')
            return redirect(url_for('menu'))
        
        if action == 'hide':
            # Remove all items of this category from the day's menu
            Menu.query.filter_by(day=day, category_id=category_id).delete()
            db.session.commit()
            flash(f'{category.name} items removed from {day.title()} menu.', 'menu_success')
        elif action == 'show':
            # Add all items of this category to the day's menu
            category_items = Item.query.filter_by(category_id=category_id, available=True).all()
            added_count = 0
            for item in category_items:
                existing = Menu.query.filter_by(day=day, category_id=category_id, item_id=item.id).first()
                if not existing:
                    new_menu_item = Menu(day=day, category_id=category_id, item_id=item.id)
                    db.session.add(new_menu_item)
                    added_count += 1
            db.session.commit()
            flash(f'{category.name} items added to {day.title()} menu.', 'menu_success')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating menu category.', 'menu_danger')
    
    return redirect(url_for('menu') + f'?day={day}')

# Helper function to get menu statistics
def get_menu_statistics():
    """Get menu statistics for dashboard"""
    try:
        # If using Menu model:
        total_menu_items = Menu.query.count()
        items_by_day = db.session.query(Menu.day, db.func.count(Menu.id)).group_by(Menu.day).all()
        popular_categories = db.session.query(Category.name, db.func.count(Menu.id)).join(Menu).group_by(Category.name).order_by(db.func.count(Menu.id).desc()).limit(5).all()
        
        # For demo purposes
        # stats = {
        #     'total_menu_items': 45,
        #     'items_by_day': {
        #         'monday': 8,
        #         'tuesday': 7,
        #         'wednesday': 6,
        #         'thursday': 8,
        #         'friday': 7,
        #         'saturday': 5,
        #         'sunday': 4
        #     },
        #     'popular_categories': [
        #         ('Dinner', 15),
        #         ('Lunch', 12),
        #         ('Breakfast', 10),
        #         ('Snacks', 5),
        #         ('Beverages', 3)
        #     ]
        # }
        
        # return stats
    except Exception as e:
        return None
@app.context_processor
def inject_new_orders_count():
    count = Order.query.filter_by(status='pending').count()
    print(count)
    return dict(new_orders_count=count)

@app.route('/admin/orders')
@login_required
def admin_orders():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/admin_orders.html',user=user,active_page='admin_orders', orders=orders)
    
@app.route('/admin/orders/<int:order_id>')
def admin_order_view(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_view.html',user=user,active_page='admin_orders', order=order)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print(f'Client {request.sid} connected')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client {request.sid} disconnected')

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    if room:
        join_room(room)
        print(f'Client {request.sid} joined room {room}')

@socketio.on('leave')
def handle_leave(data):
    room = data.get('room')
    if room:
        leave_room(room)
        print(f'Client {request.sid} left room {room}')

@app.route('/admin/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    status_messages = {
        'pending': "🕒 Your order has been placed and is awaiting processing.",
        'processing': "👨🍳 Your order is currently being prepared.",
        'ready': "🔔 Your order is ready for pickup!",
        'shipped': "🚚 Your order is out for delivery.",
        'delivered': "✅ Your order has been delivered. Enjoy your meal!",
        'cancelled': "❌ Your order was cancelled. Contact support for details."
    }

    valid_statuses = ['Pending', 'Processing', 'Ready', 'Shipped', 'Delivered', 'Cancelled']

    if new_status in valid_statuses:
        old_status = order.status
        order.status = new_status
        db.session.commit()

        flash('Order status updated successfully.', 'status_success')

        # Prepare notification message
        # Normalize new_status to lowercase to match keys in status_messages
        status_key = new_status.lower()
        message = status_messages.get(status_key, f"Order #{order.id} status updated to {new_status}")

        # Add review request if status is delivered
        if status_key == 'delivered':
            message += " Please provide us a review."

        # Emit notification to user
        try:
            user_room = f"user_{order.user_id}"
            notification_data = {
                'order_id': order.id,
                'status': new_status,
                'message': message
            }

            print(f"Emitting notification to room {user_room}: {notification_data}")

            socketio.emit(
                'order_status_update',
                notification_data,
                room=user_room
            )

        except Exception as e:
            print(f"Error emitting notification: {e}")
    else:
        flash('Invalid status selected.', 'status_danger')

    return redirect(url_for('admin_order_view', order_id=order.id))

@app.route('/admin/orders/<int:order_id>/invoice')
@login_required
def admin_order_invoice(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    order = Order.query.get_or_404(order_id)
    customer = User.query.get(order.user_id)
    
    nepal_tz = timezone('Asia/Kathmandu')
    printed_at = datetime.now(nepal_tz)
    return render_template('admin/order_invoice.html', user=user,active_page='admin_orders',printed_at=printed_at, order=order, customer=customer)

@app.route('/order/<int:order_id>/review')
@login_required
def review_order(order_id):
    """Display review page for an order"""
    user_id = session.get('user_id')
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    
    # Get items that have been reviewed
    reviewed_items = db.session.query(Review.item_id).filter_by(
        order_id=order_id, 
        user_id=user_id
    ).all()
    reviewed_item_ids = [item.item_id for item in reviewed_items]
    
    # Get user's reviews for this order
    user_reviews = Review.query.filter_by(
        order_id=order_id, 
        user_id=user_id
    ).all()
    reviews_by_item = {review.item_id: review for review in user_reviews}
    
    # Get other users' reviews for items in this order
    other_reviews = {}
    for item in order.items:
        other_user_reviews = Review.query.filter(
            Review.item_id == item.item_id,
            Review.user_id != user_id,
            Review.is_verified == True
        ).order_by(Review.created_at.desc()).limit(5).all()
        other_reviews[item.item_id] = other_user_reviews
    
    user = User.query.get(user_id)
    
    return render_template('review_order.html',
                         order=order,
                         reviewed_item_ids=reviewed_item_ids,
                         reviews_by_item=reviews_by_item,
                         other_reviews=other_reviews,
                         user=user)

@app.route('/order/<int:order_id>/submit_review', methods=['POST'])
@login_required
def submit_review(order_id):
    """Submit a review for an item"""
    user_id = session.get('user_id')
    
    # Verify order belongs to user
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    
    try:
        item_id = int(request.form.get('item_id'))
        rating = int(request.form.get('rating'))
        service_rating = request.form.get('service_rating')
        delivery_rating = request.form.get('delivery_rating')
        comment = request.form.get('review', '').strip()
        would_recommend = request.form.get('recommend') == 'yes'
        
        # Validate required fields
        if not rating or rating < 1 or rating > 5:
            flash('Please provide a valid item rating (1-5 stars).', 'review_danger')
            return redirect(url_for('review_order', order_id=order_id))
        
        if not comment:
            flash('Please provide a review comment.', 'review_danger')
            return redirect(url_for('review_order', order_id=order_id))
        
        # Validate item belongs to order
        order_item = OrderItem.query.filter_by(
            order_id=order_id, 
            item_id=item_id
        ).first()
        if not order_item:
            flash('Invalid item for this order.', 'review_danger')
            return redirect(url_for('review_order', order_id=order_id))
        
        # Check if review already exists
        existing_review = Review.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            order_id=order_id
        ).first()
        
        if existing_review:
            # Update existing review
            existing_review.rating = rating
            existing_review.service_rating = int(service_rating) if service_rating else None
            existing_review.delivery_rating = int(delivery_rating) if delivery_rating else None
            existing_review.comment = comment
            existing_review.would_recommend = would_recommend
            existing_review.updated_at = datetime.utcnow()
            
            flash('Your review has been updated successfully!', 'review_success')
        else:
            # Create new review
            new_review = Review(
                user_id=user_id,
                item_id=item_id,
                order_id=order_id,
                rating=rating,
                service_rating=int(service_rating) if service_rating else None,
                delivery_rating=int(delivery_rating) if delivery_rating else None,
                comment=comment,
                would_recommend=would_recommend
            )
            db.session.add(new_review)
            
            flash('Thank you for your review!', 'review_success')
        
        db.session.commit()
        
    except ValueError as e:
        flash('Invalid rating values provided.', 'review_danger')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while submitting your review. Please try again.', 'review_danger')
    
    return redirect(url_for('review_order', order_id=order_id))

@app.route('/item/<int:item_id>/reviews')
def item_reviews(item_id):
    """Show all reviews for an item with filtering and pagination"""
    item = Item.query.get_or_404(item_id)
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    rating_filter = request.args.get('rating', type=int)
    sort_by = request.args.get('sort', 'newest')
    
    # Build query
    reviews_query = Review.query.filter_by(item_id=item_id, is_verified=True)
    
    # Apply rating filter
    if rating_filter and 1 <= rating_filter <= 5:
        reviews_query = reviews_query.filter_by(rating=rating_filter)
    
    # Apply sorting
    if sort_by == 'oldest':
        reviews_query = reviews_query.order_by(Review.created_at.asc())
    elif sort_by == 'highest':
        reviews_query = reviews_query.order_by(Review.rating.desc())
    elif sort_by == 'lowest':
        reviews_query = reviews_query.order_by(Review.rating.asc())
    elif sort_by == 'helpful':
        reviews_query = reviews_query.order_by(Review.helpful_count.desc())
    else:  # newest (default)
        reviews_query = reviews_query.order_by(Review.created_at.desc())
    
    # Paginate
    reviews = reviews_query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get review statistics
    total_reviews = Review.query.filter_by(item_id=item_id, is_verified=True).count()
    avg_rating = db.session.query(func.avg(Review.rating)).filter_by(
        item_id=item_id, is_verified=True
    ).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else 0
    
    # Get rating distribution
    rating_distribution = {}
    for rating in range(1, 6):
        count = Review.query.filter_by(
            item_id=item_id, 
            rating=rating, 
            is_verified=True
        ).count()
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_distribution[rating] = {
            'count': count, 
            'percentage': round(percentage, 1)
        }
    
    # Get average ratings for other aspects
    avg_service_rating = db.session.query(func.avg(Review.service_rating)).filter_by(
        item_id=item_id, is_verified=True
    ).scalar()
    avg_delivery_rating = db.session.query(func.avg(Review.delivery_rating)).filter_by(
        item_id=item_id, is_verified=True
    ).scalar()
    
    avg_service_rating = round(avg_service_rating, 1) if avg_service_rating else 0
    avg_delivery_rating = round(avg_delivery_rating, 1) if avg_delivery_rating else 0
    
    # Get recommendation percentage
    recommend_count = Review.query.filter_by(
        item_id=item_id, 
        would_recommend=True, 
        is_verified=True
    ).count()
    recommend_percentage = (recommend_count / total_reviews * 100) if total_reviews > 0 else 0
    
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    
    return render_template('item_reviews.html',
                         item=item,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         avg_rating=avg_rating,
                         avg_service_rating=avg_service_rating,
                         avg_delivery_rating=avg_delivery_rating,
                         recommend_percentage=round(recommend_percentage, 1),
                         rating_distribution=rating_distribution,
                         current_rating_filter=rating_filter,
                         current_sort=sort_by,
                         user=user)

@app.route('/review/<int:review_id>/helpful', methods=['POST'])
@login_required
def mark_review_helpful(review_id):
    """Mark a review as helpful or not helpful"""
    user_id = session.get('user_id')
    is_helpful = request.form.get('helpful') == 'true'
    
    review = Review.query.get_or_404(review_id)
    
    # Users can't vote on their own reviews
    if review.user_id == user_id:
        return jsonify({
            'success': False,
            'message': 'You cannot vote on your own review.'
        }), 400
    
    try:
        # Check if user has already voted on this review
        existing_vote = ReviewHelpful.query.filter_by(
            review_id=review_id, 
            user_id=user_id
        ).first()
        
        if existing_vote:
            # Update existing vote
            existing_vote.is_helpful = is_helpful
        else:
            # Create new vote
            new_vote = ReviewHelpful(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful
            )
            db.session.add(new_vote)
        
        # Update helpful count on review
        helpful_count = ReviewHelpful.query.filter_by(
            review_id=review_id, 
            is_helpful=True
        ).count()
        review.helpful_count = helpful_count
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'helpful_count': helpful_count,
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Error processing your feedback.'
        }), 500

@app.route('/reorder/<int:order_id>')
@login_required
def reorder(order_id):
    """Reorder items from a previous order"""
    user_id = session.get('user_id')
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    
    # Add items to cart (implement your cart logic here)
    # For now, redirect to menu or cart page
    flash('Items have been added to your cart!', 'success')
    return redirect(url_for('user_menu'))

# ===================== ADMIN ROUTES =====================

@app.route('/admin/reviews')
@login_required
def admin_reviews():
    """Admin page to manage reviews"""
    if session.get('user_role') != 'admin':
        return redirect(url_for('user_dashboard'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    rating_filter = request.args.get('rating', type=int)
    item_filter = request.args.get('item', type=int)
    verification_filter = request.args.get('verified')
    per_page = 10
    
    # Build query
    reviews_query = Review.query.join(User).join(Item)
    
    # Apply filters
    if rating_filter and 1 <= rating_filter <= 5:
        reviews_query = reviews_query.filter(Review.rating == rating_filter)
    
    if item_filter:
        reviews_query = reviews_query.filter(Review.item_id == item_filter)
        
    if verification_filter == 'verified':
        reviews_query = reviews_query.filter(Review.is_verified == True)
    elif verification_filter == 'unverified':
        reviews_query = reviews_query.filter(Review.is_verified == False)
    
    # Order by newest first
    reviews_query = reviews_query.order_by(Review.created_at.desc())
    
    # Paginate
    reviews = reviews_query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get stats for dashboard
    total_reviews = Review.query.count()
    avg_rating = db.session.query(func.avg(Review.rating)).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else 0
    
    # Get recent reviews
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(5).all()
    
    # Get unverified reviews count
    unverified_count = Review.query.filter_by(is_verified=False).count()
    
    # Get all items for filter dropdown
    items = Item.query.order_by(Item.name).all()
    
    return render_template('admin/admin_reviews.html',
                         user=user,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         avg_rating=avg_rating,
                         recent_reviews=recent_reviews,
                         unverified_count=unverified_count,
                         items=items,
                         current_rating_filter=rating_filter,
                         current_item_filter=item_filter,
                         current_verification_filter=verification_filter,
                         active_page='reviews')

@app.route('/admin/reviews/<int:review_id>/toggle-visibility', methods=['POST'])
@login_required
def toggle_review_visibility(review_id):
    """Toggle review visibility (admin only)"""
    if session.get('user_role') != 'admin':
        return redirect(url_for('user_dashboard'))
    
    review = Review.query.get_or_404(review_id)
    
    try:
        review.is_verified = not review.is_verified
        db.session.commit()
        
        status = "verified" if review.is_verified else "hidden"
        flash(f'Review has been {status}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating review visibility.', 'danger')
    
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    """Delete a review (admin only)"""
    if session.get('user_role') != 'admin':
        return redirect(url_for('user_dashboard'))
    
    review = Review.query.get_or_404(review_id)
    
    try:
        # Delete associated helpful votes first
        ReviewHelpful.query.filter_by(review_id=review_id).delete()
        
        # Delete the review
        db.session.delete(review)
        db.session.commit()
        
        flash('Review has been deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting review.', 'danger')
    
    return redirect(url_for('admin_reviews'))

# ===================== HELPER FUNCTIONS =====================

def get_item_average_rating(item_id):
    """Get average rating for an item"""
    avg_rating = db.session.query(func.avg(Review.rating)).filter_by(
        item_id=item_id, is_verified=True
    ).scalar()
    return round(avg_rating, 1) if avg_rating else 0

def get_item_review_count(item_id):
    """Get total review count for an item"""
    return Review.query.filter_by(item_id=item_id, is_verified=True).count()

def get_user_review_for_item(user_id, item_id):
    """Check if user has already reviewed an item"""
    return Review.query.filter_by(
        user_id=user_id, 
        item_id=item_id
    ).first()

# @app.route('/notifications')
# @login_required
# def get_notifications():
#     # Replace with DB query in real app
#     notifications = [
#         {"message": "🍔 Your Order is being prepared" ,"time": datetime.now().strftime("%I:%M %p")},
#         {"message": "⚠️ Your Order is canceled", "time": datetime.now().strftime("%I:%M %p")},
#         {"message": "✅ Your order is delivered", "time": datetime.now().strftime("%I:%M %p")},
#     ]
#     return jsonify(notifications)


@app.route('/menu')
@login_required
def user_menu():
    current_day = request.args.get('day')
    if not current_day:
        current_day = datetime.today().strftime('%A').lower()  

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    categories = Category.query.filter_by(status=True).all()
    menu_items = {}

    for category in categories:
        menu_items[category.name] = []

    menu_entries = Menu.query.filter_by(day=current_day).all()
    for entry in menu_entries:
        if entry.category.name not in menu_items:
            menu_items[entry.category.name] = []
        menu_items[entry.category.name].append(entry.item)

    return render_template('menu.html',
                           user=user,
                           menu_items=menu_items,
                           current_day=current_day,
                           categories=categories,
                           active_page='menu')
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    user_id = session['user_id']
    item_id = request.form.get('item_id')
    source = request.form.get('source')  # Get source page info
    item = Item.query.get(item_id)

    if not item:
        flash('Invalid item.', 'cart_error')
        return redirect(url_for(source))  # fallback redirect to source

    today = date.today()

    # ✅ Delete all cart items older than today
    CartItem.query.filter(CartItem.user_id == user_id, CartItem.created_date != today).delete()
    db.session.commit()

    # Check if item already in cart today
    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item.id, created_date=today).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        new_item = CartItem(
            user_id=user_id,
            item_id=item.id,
            quantity=1,
            created_at=datetime.utcnow(),
            created_date=today
        )
        db.session.add(new_item)

    db.session.commit()
    flash(f'Added "{item.name}" to cart', 'cart_success')

    # ✅ Redirect back to the page where the request came from
    if source == 'dashboard':
        return redirect(url_for('dashboard'))
    return redirect(url_for('user_menu'))


@app.route('/cart')
@login_required
def cart():
    user_id = session['user_id']
    user = User.query.get(user_id)
    today = date.today()

    CartItem.query.filter(CartItem.user_id == user_id, CartItem.created_date != today).delete()
    db.session.commit()

    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    total = sum(item.quantity * item.item.price for item in cart_items)

    return render_template('cart.html', user=user, cart_items=cart_items, total=total, active_page='cart')


@app.route('/update_cart_quantity', methods=['POST'])
@login_required
def update_cart_quantity():
    user_id = session['user_id']
    item_id = request.form.get('item_id')
    action = request.form.get('action')  # increase or decrease

    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not cart_item:
        flash('Item not found in cart.', 'cart_error')
        return redirect(url_for('cart'))

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart.', 'cart_success')
            return redirect(url_for('cart'))

    db.session.commit()
    flash('Cart updated.', 'cart_success')
    return redirect(url_for('cart'))


@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    user_id = session['user_id']
    item_id = request.form.get('item_id')

    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'items_success')
    else:
        flash('Item not found in cart.', 'items_error')

    return redirect(url_for('cart'))
@app.route('/cart/recommendations')
@login_required
def cart_recommendations():
    """Get recommendations based on current cart items"""
    user_id = session['user_id']
    
    # Get current cart items
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    
    if not cart_items:
        return jsonify({'recommendations': []})
    
    try:
        # Build user-item matrix
        user_item_matrix, df = recommendation.build_user_item_matrix()
        
        if user_item_matrix is None:
            # Fallback to popular items
            recommendations = recommendation.get_fallback_recommendations_with_explanations(top_n=4)
        else:
            # Train KNN model
            model, k = recommendation.train_knn(user_item_matrix, n_neighbors=5)
            
            if model is None:
                recommendations = recommendation.get_fallback_recommendations_with_explanations(top_n=4)
            else:
                # Get collaborative filtering recommendations
                recommendations = recommendation.recommend_items_for_user_with_explanations(
                    user_id, user_item_matrix, model, n_neighbors=5, top_n=4
                )
                
                # If no collaborative recommendations, use fallback
                if not recommendations:
                    recommendations = recommendation.get_fallback_recommendations_with_explanations(top_n=4)
        
        # Filter out items already in cart
        cart_item_ids = {item.item_id for item in cart_items}
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec['item'].id not in cart_item_ids
        ]
        
        # Convert to JSON-serializable format
        recommendations_data = []
        for rec in filtered_recommendations[:4]:  # Limit to 4 items
            recommendations_data.append({
                'id': rec['item'].id,
                'name': rec['item'].name,
                'price': float(rec['item'].price),
                'image_filename': rec['item'].image_filename,
                'explanation': rec['explanation'],
                'explanation_type': rec['explanation_type'],
                'description': getattr(rec['item'], 'description', ''),
                'category': rec['item'].category.name if hasattr(rec['item'], 'category') and rec['item'].category else '',
                'popularity_score': rec.get('popularity_score', 0),
                'order_count': rec.get('order_count', 0)
            })

            print("DEBUG raw recommendations:", [rec['item'].id for rec in recommendations])
            print("DEBUG cart items:", cart_item_ids)
        
        return jsonify({'recommendations': recommendations_data})
        
    except Exception as e:
        print(f"Error getting cart recommendations: {e}")
        return jsonify({'recommendations': []})


@app.route('/cart/add_recommended', methods=['POST'])
@login_required
def add_recommended_to_cart():
    """Add a recommended item to cart via AJAX"""
    user_id = session['user_id']
    item_id = request.json.get('item_id')
    quantity = request.json.get('quantity', 1)
    
    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID required'})
    
    try:
        # Check if item exists and is available today
        item = Item.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'})
        
        # Check if item is available today
        today = datetime.now().strftime('%A').lower()
        menu_item = Menu.query.filter_by(item_id=item_id, day=today).first()
        if not menu_item:
            return jsonify({'success': False, 'message': 'Item not available today'})
        
        # Check if item already in cart
        existing_cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()
        
        if existing_cart_item:
            existing_cart_item.quantity += quantity
        else:
            cart_item = CartItem(
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                created_date=date.today()
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        
        # Get updated cart count
        cart_count = CartItem.query.filter_by(user_id=user_id).count()
        
        return jsonify({
            'success': True, 
            'message': f'{item.name} added to cart!',
            'cart_count': cart_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error adding item to cart'})

@app.route('/update_cart_addons', methods=['POST'])
@login_required
def update_cart_addons():
    user_id = session['user_id']
    cart_id = request.form.get('cart_id')
    addon_ids = request.form.getlist('addon_ids')
    
    # Convert addon_ids to integers
    addon_ids = [int(aid) for aid in addon_ids if aid.isdigit()]
    
    # Store selected addons in session for this cart item
    if 'cart_addons' not in session:
        session['cart_addons'] = {}
    
    session['cart_addons'][cart_id] = addon_ids
    session.modified = True
    
    flash('Add-ons updated successfully!', 'cart_success')
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    user_id = session['user_id']
    user = User.query.get(user_id)
    today = date.today()

    # Clean up stale cart items
    CartItem.query.filter(
        CartItem.user_id == user_id,
        CartItem.created_date != today
    ).delete()
    db.session.commit()

    cart_items = CartItem.query.filter_by(user_id=user_id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    cart_addons = session.get('cart_addons', {})

    checkout_items = []
    for cart_item in cart_items:
        item_data = {
            'id': cart_item.item_id,
            'name': cart_item.item.name,
            'price': cart_item.item.price,
            'quantity': cart_item.quantity,
            'cart_id': str(cart_item.id),
            'selected_addons': []
        }

        selected_addon_ids = cart_addons.get(str(cart_item.id), [])

        if selected_addon_ids:
            selected_addons = (
                db.session.query(Addon)
                .join(addon_item_association, Addon.id == addon_item_association.c.addon_id)
                .filter(
                    addon_item_association.c.item_id == cart_item.item_id,
                    Addon.id.in_(selected_addon_ids),
                    Addon.status == True
                )
                .all()
            )

            for addon in selected_addons:
                item_data['selected_addons'].append({
                    'id': addon.id,
                    'name': addon.name,
                    'price': addon.price,
                    'description': addon.description,
                    'category': addon.category
                })

        checkout_items.append(item_data)

    subtotal = sum(item['quantity'] * item['price'] for item in checkout_items)
    addon_total = sum(
        addon['price'] * item['quantity']
        for item in checkout_items
        for addon in item['selected_addons']
    )
    
    total_before_tax = subtotal + addon_total
    tax = 0
    service_fee = 10
    total = total_before_tax + tax + service_fee

    if request.method == 'POST':
        errors = validate_checkout_form(request.form)
        form_total = float(request.form.get('total_amount', 0))

        if abs(form_total - total) > 0.01:
            errors.append("Invalid total amount.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('checkout.html',
                                   user=user,
                                   form_data=request.form,
                                   cart=checkout_items,
                                   subtotal=subtotal,
                                   addon_total=addon_total,
                                   tax=tax,
                                   service_fee=service_fee,
                                   total=total,
                                   has_errors=True)

        # Handle different payment methods
        payment_method = request.form.get('payment')
        
        if payment_method == 'esewa':
            return process_esewa_payment(user, checkout_items, request.form, total)
        elif payment_method == 'khalti':
            # For Khalti, the payment is handled on frontend first, then verified
            khalti_token = request.form.get('khalti_token')
            if not khalti_token:
                flash('Khalti payment token missing. Please try again.', 'danger')
                return render_template('checkout.html',
                                       user=user,
                                       form_data=request.form,
                                       cart=checkout_items,
                                       subtotal=subtotal,
                                       addon_total=addon_total,
                                       tax=tax,
                                       service_fee=service_fee,
                                       total=total,
                                       has_errors=True)

        # Process the order (works for all payment methods now)
        cart_dict = {
            item['id']: {
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'selected_addons': item['selected_addons']
            }
            for item in checkout_items
        }

        if process_order_with_payment(user, cart_dict, request.form, total):
            CartItem.query.filter_by(user_id=user_id).delete()
            db.session.commit()

            if 'cart_addons' in session:
                del session['cart_addons']
                session.modified = True

            flash('Order placed successfully!', 'order_success')
            return redirect(url_for('orders'))
        else:
            flash('Order failed. Please try again.', 'danger')
            return render_template('checkout.html',
                                   user=user,
                                   form_data=request.form,
                                   cart=checkout_items,
                                   subtotal=subtotal,
                                   addon_total=addon_total,
                                   tax=tax,
                                   service_fee=service_fee,
                                   total=total,
                                   has_errors=True)

    return render_template('checkout.html',
                           user=user,
                           form_data={},
                           cart=checkout_items,
                           subtotal=subtotal,
                           addon_total=addon_total,
                           tax=tax,
                           service_fee=service_fee,
                           total=total,
                           has_errors=False,
                           active_page="cart", khalti_public_key=app.config['KHALTI_PUBLIC_KEY'])

def process_order_with_payment(user, cart, form_data, total_amount):
    """Enhanced order processing with separate payment tracking"""
    try:
        print(f"=== Processing Order with Payment ===")
        print(f"User ID: {user.id}")
        print(f"Payment Method: {form_data.get('payment')}")
        print(f"Total Amount: {total_amount}")
        
        # Validate form data
        required_fields = ['name', 'contact', 'email', 'delivery', 'payment']
        for field in required_fields:
            if not form_data.get(field):
                print(f"❌ Missing required field: {field}")
                return False
        
        payment_method = form_data.get('payment')
        nepal_tz = timezone('Asia/Kathmandu')
        created_at = datetime.now(nepal_tz)
        
        # Create order (without payment-specific fields)
        order_data = {
            'user_id': user.id,
            'name': form_data['name'],
            'contact': form_data['contact'],
            'email': form_data['email'],
            'delivery': form_data['delivery'],
            'building': form_data.get('building', ''),
            'floor': form_data.get('floor', ''),
            'payment': payment_method,  # Keep for backward compatibility
            'total_amount': total_amount,
            'status': 'pending',
            'created_at': created_at
        }
        
        order = Order(**order_data)
        db.session.add(order)
        db.session.flush()
        print(f"✅ Order created with ID: {order.id}")

        # Only create payment record if NOT cash
        if payment_method.lower() != 'cash':
            payment_status = 'pending'
            payment_data = {
                'order_id': order.id,
                'payment_method': payment_method,
                'payment_status': payment_status,
                'amount': total_amount,
                'created_at': created_at
            }
            
            # Add payment method specific data
            if payment_method == 'khalti':
                khalti_token = form_data.get('khalti_token')
                if khalti_token:
                    payment_data['khalti_token'] = khalti_token
                    payment_data['payment_status'] = 'completed'  # Already verified
                    payment_data['completed_at'] = created_at
                    payment_data['transaction_id'] = khalti_token
            
            elif payment_method == 'esewa':
                esewa_code = form_data.get('esewa_transaction_code')
                if esewa_code:
                    payment_data['transaction_id'] = esewa_code
                    payment_data['esewa_transaction_uuid'] = form_data.get('transaction_uuid', '')
                    payment_data['esewa_product_code'] = ESEWA_MERCHANT_CODE
                    payment_data['payment_status'] = 'completed'  # Already verified
                    payment_data['completed_at'] = created_at
            
            payment = Payment(**payment_data)
            db.session.add(payment)
            db.session.flush()
            print(f"💰 Payment record created with ID: {payment.id}")
        else:
            print("💵 Cash payment — skipping Payment table entry")

        # Add order items and addons
        items_added = 0
        addons_added = 0
        
        for item in cart.values():
            print(f"Adding item: {item['name']} (ID: {item['id']}) x {item['quantity']}")
            
            order_item = OrderItem(
                order_id=order.id,
                item_id=item['id'],
                name=item['name'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            db.session.flush()
            items_added += 1
            
            # Add selected addons for this order item
            if 'selected_addons' in item and item['selected_addons']:
                for addon_data in item['selected_addons']:
                    print(f"  Adding addon: {addon_data['name']} (+Rs. {addon_data['price']})")
                    
                    order_addon = OrderAddon(
                        order_item_id=order_item.id,
                        addon_id=addon_data['id'],
                        name=addon_data['name'],
                        price=addon_data['price'],
                        category=addon_data.get('category', ''),
                        description=addon_data.get('description', '')
                    )
                    db.session.add(order_addon)
                    addons_added += 1

        print(f"Added {items_added} items and {addons_added} addons")
        
        db.session.commit()
        print("Order committed successfully")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f" Order processing failed: {e}")
        traceback.print_exc()
        return False


# Enhanced Khalti verification
def verify_khalti_payment(token, amount):
    """Verify Khalti payment with proper error handling"""
    try:
        print(f"=== Verifying Khalti Payment ===")
        print(f"Token: {token[:20]}..." if token else "No token")
        print(f"Amount: Rs. {amount}")
        
        if not KHALTI_SECRET_KEY:
            print("⚠️ TEST MODE: Khalti secret key not set, accepting payment")
            return True
        
        if not token:
            print("❌ No Khalti token provided")
            return False
            
        headers = {
            "Authorization": f"Key {KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        # Convert amount to paisa (multiply by 100)
        amount_paisa = int(float(amount) * 100)
        
        payload = {
            "token": token,
            "amount": amount_paisa
        }
        
        print(f"Verifying with Khalti API...")
        print(f"Payload: {payload}")
        
        response = requests.post(
            "https://khalti.com/api/v2/payment/verify/",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Khalti API Response Status: {response.status_code}")
        print(f"Khalti API Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Parsed response: {data}")
            
            # Verify amount matches
            returned_amount = data.get('amount', 0)
            if returned_amount == amount_paisa:
                print("✅ Khalti payment verification successful")
                return True
            else:
                print(f"❌ Amount mismatch: expected {amount_paisa}, got {returned_amount}")
                return False
        else:
            print(f"❌ Khalti verification failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Khalti verification error: {e}")
        traceback.print_exc()
        return False

@app.route('/khalti-verify', methods=['POST','GET'])
def khalti_verify():
    """Enhanced Khalti verification endpoint"""
    try:
        print("=== Khalti Verification Request ===")
        data = request.get_json()
        
        if not data:
            print("❌ No JSON data received")
            return jsonify(success=False, message="No data received"), 400
        
        print(f"Received data: {data}")
        
        token = data.get('token')
        amount = data.get('amount')
        
        if not token:
            print("❌ No token provided")
            return jsonify(success=False, message="Khalti token is required"), 400
            
        if not amount:
            print("❌ No amount provided")
            return jsonify(success=False, message="Amount is required"), 400
        
        try:
            amount = float(amount)
            if amount <= 0:
                print(f"❌ Invalid amount: {amount}")
                return jsonify(success=False, message="Invalid amount"), 400
        except (ValueError, TypeError):
            print(f"❌ Invalid amount format: {amount}")
            return jsonify(success=False, message="Invalid amount format"), 400
        
        # Verify with Khalti
        if verify_khalti_payment(token, amount):
            print("✅ Khalti verification successful")
            return jsonify(
                success=True, 
                message="Payment verified successfully",
                verified_amount=amount,
                token=token[:20] + "..."  # Partial token for logging
            )
        else:
            print("❌ Khalti verification failed")
            return jsonify(success=False, message="Payment verification failed"), 400
            
    except Exception as e:
        print(f"❌ Khalti verification endpoint error: {e}")
        traceback.print_exc()
        return jsonify(success=False, message="Server error occurred"), 500

def generate_esewa_signature(message, secret_key):
    """Generate HMAC-SHA256 signature for eSewa"""
    try:
        print(f"Generating signature for message: {message}")
        
        # Convert message to string if it's a dict
        if isinstance(message, dict):
            message = json.dumps(message, separators=(',', ':'), sort_keys=True)
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 encode the signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        print(f"Generated signature: {signature_b64[:20]}...")
        return signature_b64
        
    except Exception as e:
        print(f"Signature generation error: {e}")
        traceback.print_exc()
        return None

def process_esewa_payment(user, cart_items, form_data, total_amount):
    """Process eSewa payment using ePay v2 API"""
    try:
        print(f"=== Starting eSewa Payment Process ===")
        print(f"User ID: {user.id}")
        print(f"Total Amount: {total_amount}")
        print(f"Cart Items Count: {len(cart_items)}")
        
        # Validate inputs
        if not user:
            print("ERROR: No user provided")
            flash('User session error. Please try again.', 'danger')
            return redirect(url_for('checkout'))
            
        if not cart_items:
            print("ERROR: No cart items provided")
            flash('Cart is empty. Please add items first.', 'danger')
            return redirect(url_for('checkout'))
            
        if total_amount <= 0:
            print("ERROR: Invalid total amount")
            flash('Invalid order amount. Please try again.', 'danger')
            return redirect(url_for('checkout'))
        
        # Generate unique transaction ID
        transaction_uuid = str(uuid.uuid4())
        print(f"Generated transaction UUID: {transaction_uuid}")
        
        # Store order data in session for later processing
        session_data = {
            'user_id': user.id,
            'cart_items': cart_items,
            'form_data': dict(form_data),
            'total_amount': total_amount,
            'transaction_uuid': transaction_uuid,
            'timestamp': datetime.now().isoformat()
        }
        
        session['pending_esewa_order'] = session_data
        session.modified = True
        print("Stored order data in session")
        
        # Get base URL for callbacks
        base_url = request.url_root.rstrip('/')
        success_url = f"{base_url}/esewa/success"
        failure_url = f"{base_url}/esewa/failure"
        
        print(f"Success URL: {success_url}")
        print(f"Failure URL: {failure_url}")
        
        # Prepare eSewa payment request
        payment_data = {
            "amount": str(total_amount),
            "failure_url": failure_url,
            "product_delivery_charge": "0",
            "product_service_charge": "0", 
            "product_code": ESEWA_MERCHANT_CODE,
            "signature": "",  # Will be filled after signature generation
            "signed_field_names": "total_amount,transaction_uuid,product_code",
            "success_url": success_url,
            "tax_amount": "0",
            "total_amount": str(total_amount),
            "transaction_uuid": transaction_uuid
        }
        
        print(f"Payment data prepared: {payment_data}")
        
        # Create message for signature
        signed_fields = payment_data["signed_field_names"].split(",")
        message_parts = []
        for field in signed_fields:
            if field in payment_data:
                message_parts.append(f"{field}={payment_data[field]}")
        
        message = ",".join(message_parts)
        print(f"Message for signature: {message}")
        
        signature = generate_esewa_signature(message, ESEWA_SECRET_KEY)
        
        if not signature:
            print("ERROR: Failed to generate signature")
            flash('Payment processing failed. Please try again.', 'danger')
            return redirect(url_for('checkout'))
        
        payment_data["signature"] = signature
        print("Signature added to payment data")
        
        # Return form data for frontend submission
        print("=== eSewa Payment Process Completed Successfully ===")
        return render_template('esewa_redirect.html', payment_data=payment_data)
        
    except Exception as e:
        print(f"eSewa payment processing error: {e}")
        traceback.print_exc()
        flash('Payment processing failed. Please try again.', 'danger')
        return redirect(url_for('checkout'))

@app.route('/esewa/success')
def esewa_success():
    """Handle eSewa payment success callback"""
    try:
        print("=== eSewa Success Callback Received ===")
        print(f"Request args: {dict(request.args)}")
        
        data_encoded = request.args.get('data')
        
        if data_encoded:
            try:
                # Base64 decode
                data_json = base64.b64decode(data_encoded).decode('utf-8')
                data = json.loads(data_json)
                print(f"Decoded data: {data}")
                
                transaction_code = data.get('transaction_code')
                transaction_uuid = data.get('transaction_uuid')
                total_amount = data.get('total_amount')
            except Exception as e:
                print(f"Error decoding data parameter: {e}")
                flash('Invalid payment response from eSewa.', 'danger')
                return redirect(url_for('checkout'))
        else:
            # Get parameters from eSewa v2
            transaction_code = request.args.get('transaction_code')
            transaction_uuid = request.args.get('transaction_uuid') 
            total_amount = request.args.get('total_amount')
        
        print(f"Transaction Code: {transaction_code}")
        print(f"Transaction UUID: {transaction_uuid}")
        print(f"Total Amount: {total_amount}")
        
        if not all([transaction_code, transaction_uuid, total_amount]):
            print("ERROR: Missing required parameters from eSewa callback")
            missing = []
            if not transaction_code: missing.append('transaction_code')
            if not transaction_uuid: missing.append('transaction_uuid')
            if not total_amount: missing.append('total_amount')
            print(f"Missing parameters: {missing}")
            flash('Invalid payment response from eSewa. Missing parameters.', 'danger')
            return redirect(url_for('checkout'))
        
        # Get pending order from session
        pending_order = session.get('pending_esewa_order')
        if not pending_order:
            print("ERROR: No pending eSewa order found in session")
            print(f"Session keys: {list(session.keys())}")
            flash('Order session expired. Please try again.', 'danger')
            return redirect(url_for('checkout'))
            
        print(f"Found pending order for UUID: {pending_order.get('transaction_uuid')}")
        
        if pending_order['transaction_uuid'] != transaction_uuid:
            print(f"ERROR: Transaction UUID mismatch")
            print(f"Expected: {pending_order['transaction_uuid']}")
            print(f"Received: {transaction_uuid}")
            flash('Order session mismatch. Please try again.', 'danger')
            return redirect(url_for('checkout'))
        
        # Verify amount matches
        expected_amount = pending_order['total_amount']
        received_amount = float(total_amount)
        if abs(expected_amount - received_amount) > 0.01:
            print(f"ERROR: Amount mismatch")
            print(f"Expected: {expected_amount}")
            print(f"Received: {received_amount}")
            flash('Payment amount mismatch. Please contact support.', 'danger')
            return redirect(url_for('checkout'))
        
        print("=== Starting Payment Verification ===")
        # Verify payment with eSewa v2
        if verify_esewa_v2_payment(transaction_code, transaction_uuid, total_amount):
            print("✅ eSewa payment verification successful")
            
            # Create the order
            user = User.query.get(pending_order['user_id'])
            if not user:
                print(f"ERROR: User not found: {pending_order['user_id']}")
                flash('User session error. Please try again.', 'danger')
                return redirect(url_for('checkout'))
            
            print(f"Processing order for user: {user.id}")
            
            cart_dict = {
                item['id']: {
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': item['quantity'],
                    'selected_addons': item['selected_addons']
                }
                for item in pending_order['cart_items']
            }
            
            print(f"Cart dictionary created with {len(cart_dict)} items")
            
            # Add eSewa transaction code to form data
            form_data = pending_order['form_data'].copy()
            form_data['esewa_transaction_code'] = transaction_code
            
            print("=== Processing Order ===")
            if process_order_with_payment(user, cart_dict, form_data, pending_order['total_amount']):
                print("✅ Order processed successfully")
                
                # Clear cart and session
                try:
                    deleted_count = CartItem.query.filter_by(user_id=user.id).delete()
                    db.session.commit()
                    print(f"Deleted {deleted_count} cart items")
                    
                    if 'cart_addons' in session:
                        del session['cart_addons']
                        print("Cleared cart_addons from session")
                    if 'pending_esewa_order' in session:
                        del session['pending_esewa_order']
                        print("Cleared pending_esewa_order from session")
                    session.modified = True
                    
                    flash('Order placed successfully with eSewa payment!', 'order_success')
                    return redirect(url_for('orders'))
                    
                except Exception as e:
                    print(f"ERROR: Failed to clear cart/session: {e}")
                    # Order was created successfully, so still redirect to orders
                    flash('Order placed successfully! (Note: Cart cleanup had issues)', 'order_success')
                    return redirect(url_for('orders'))
            else:
                print("❌ Order processing failed")
                flash('Order processing failed after payment. Please contact support with transaction code: ' + transaction_code, 'danger')
                return redirect(url_for('checkout'))
        else:
            print("❌ eSewa payment verification failed")
            flash('Payment verification failed. Please try again.', 'danger')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        print(f"eSewa success handling error: {e}")
        traceback.print_exc()
        flash('Payment processing error. Please contact support.', 'danger')
        return redirect(url_for('checkout'))

@app.route('/esewa/failure')
def esewa_failure():
    """Handle eSewa payment failure callback"""
    try:
        print("=== eSewa Payment Failure Callback ===")
        print(f"Request args: {dict(request.args)}")
        
        # Get failure reason if provided
        failure_reason = request.args.get('failure_reason', 'Unknown')
        print(f"Failure reason: {failure_reason}")
        
        flash(f'Payment was cancelled or failed: {failure_reason}. Please try again.', 'warning')
        
        # Clean up session
        if 'pending_esewa_order' in session:
            del session['pending_esewa_order']
            session.modified = True
            print("Cleaned up pending eSewa order from session")
        
        return redirect(url_for('checkout'))
        
    except Exception as e:
        print(f"eSewa failure handling error: {e}")
        traceback.print_exc()
        flash('Payment processing error. Please try again.', 'warning')
        return redirect(url_for('checkout'))

def verify_esewa_v2_payment(transaction_code, transaction_uuid, total_amount):
    """Verify eSewa v2 payment using the lookup API"""
    try:
        print(f"=== Starting Payment Verification ===")
        print(f"Transaction Code: {transaction_code}")
        print(f"Transaction UUID: {transaction_uuid}")
        print(f"Total Amount: {total_amount}")
        print(f"Merchant Code: {ESEWA_MERCHANT_CODE}")
        
        # For test environment with EPAYTEST, do basic validation
        if ESEWA_MERCHANT_CODE == "EPAYTEST":
            print("🧪 TEST MODE: Performing basic validation")
            
            # Check if all required parameters are present and valid
            if not transaction_code or not transaction_uuid or not total_amount:
                print("❌ Missing required parameters")
                return False
            
            try:
                amount_float = float(total_amount)
                if amount_float <= 0:
                    print(f"❌ Invalid amount: {amount_float}")
                    return False
                    
                # Check UUID format
                uuid.UUID(transaction_uuid)  # This will raise ValueError if invalid
                
                print("✅ Basic validation passed - accepting payment in test mode")
                return True
                
            except (ValueError, TypeError) as e:
                print(f"❌ Validation failed: {e}")
                return False
        
        # Production verification (when using real merchant code)
        print("🔍 PRODUCTION MODE: Performing API verification")
        
        verification_data = {
            "product_code": ESEWA_MERCHANT_CODE,
            "transaction_uuid": transaction_uuid,
            "total_amount": total_amount
        }
        
        print(f"Verification data: {verification_data}")
        
        # Generate signature for verification
        message = f"transaction_uuid={transaction_uuid},product_code={ESEWA_MERCHANT_CODE}"
        signature = generate_esewa_signature(message, ESEWA_SECRET_KEY)
        
        if not signature:
            print("❌ Failed to generate verification signature")
            return False
        
        # Make verification request
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {signature}'
        }
        
        verification_url = f"{ESEWA_BASE_URL}/form"
        print(f"Making verification request to: {verification_url}")
        print(f"Headers: {headers}")
        
        response = requests.post(
            verification_url,
            json=verification_data,
            headers=headers,
            timeout=30
        )
        
        print(f"Verification response status: {response.status_code}")
        print(f"Verification response headers: {dict(response.headers)}")
        print(f"Verification response body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Parsed response: {result}")
                
                # Check if transaction is successful
                is_verified = (
                    result.get('status') == 'COMPLETE' and
                    result.get('transaction_uuid') == transaction_uuid and
                    abs(float(result.get('total_amount', 0)) - float(total_amount)) < 0.01
                )
                
                print(f"Verification result: {is_verified}")
                if not is_verified:
                    print(f"Verification failed - Status: {result.get('status')}, UUID match: {result.get('transaction_uuid') == transaction_uuid}, Amount match: {abs(float(result.get('total_amount', 0)) - float(total_amount)) < 0.01}")
                
                return is_verified
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                return False
        else:
            print(f"❌ eSewa verification failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ eSewa verification error: {e}")
        traceback.print_exc()
        return False

# def process_order(user, cart, form, calculated_total):
#     """Process order with enhanced debugging"""
#     try:
#         print(f"=== Processing Order ===")
#         print(f"User ID: {user.id}")
#         print(f"Payment Method: {form.get('payment')}")
#         print(f"Calculated Total: {calculated_total}")
#         print(f"Cart Items: {len(cart)}")
        
#         khalti_token = form.get('khalti_token') if form.get('payment') == 'khalti' else None
#         esewa_transaction_code = form.get('esewa_transaction_code') if form.get('payment') == 'esewa' else None
        
#         print(f"Khalti Token: {'Present' if khalti_token else 'None'}")
#         print(f"eSewa Transaction Code: {esewa_transaction_code}")
        
#         # Validate form data
#         required_fields = ['name', 'contact', 'email', 'delivery', 'payment']
#         for field in required_fields:
#             if not form.get(field):
#                 print(f"❌ Missing required field: {field}")
#                 return False
        
#         print("✅ Form validation passed")
#         nepal_tz = timezone('Asia/Kathmandu')
#         created_at = datetime.now(nepal_tz)
#         # Create order
#         order_data = {
#             'user_id': user.id,
#             'name': form['name'],
#             'contact': form['contact'],
#             'email': form['email'],
#             'delivery': form['delivery'],
#             'building': form.get('building', ''),
#             'floor': form.get('floor', ''),
#             'payment': form['payment'],
#             'total_amount': calculated_total,
#             'khalti_token': khalti_token,
#             'esewa_transaction_code': esewa_transaction_code,
#             'status': 'pending',
#             'created_at': created_at
#         }
        
#         print(f"Creating order with data: {order_data}")
        
#         order = Order(**order_data)
#         db.session.add(order)
#         db.session.flush()
        
#         print(f"✅ Order created with ID: {order.id}")

#         # Add order items with their addons
#         items_added = 0
#         addons_added = 0
        
#         for item in cart.values():
#             print(f"Adding item: {item['name']} (ID: {item['id']}) x {item['quantity']}")
            
#             order_item = OrderItem(
#                 order_id=order.id,
#                 item_id=item['id'],
#                 name=item['name'],
#                 quantity=item['quantity'],
#                 price=item['price']
#             )
#             db.session.add(order_item)
#             db.session.flush()
#             items_added += 1
            
#             # Add selected addons for this order item
#             if 'selected_addons' in item and item['selected_addons']:
#                 for addon_data in item['selected_addons']:
#                     print(f"  Adding addon: {addon_data['name']} (+Rs. {addon_data['price']})")
                    
#                     order_addon = OrderAddon(
#                         order_item_id=order_item.id,
#                         addon_id=addon_data['id'],
#                         name=addon_data['name'],
#                         price=addon_data['price'],
#                         category=addon_data.get('category', ''),
#                         description=addon_data.get('description', '')
#                     )
#                     db.session.add(order_addon)
#                     addons_added += 1

#         print(f"✅ Added {items_added} items and {addons_added} addons")
        
#         db.session.commit()
#         print("✅ Order committed successfully to database")
#         return True
        
#     except Exception as e:
#         db.session.rollback()
#         print(f"❌ Order processing failed: {e}")
#         traceback.print_exc()
#         return False

# -------------------- UPDATED FORM VALIDATION --------------------

def validate_checkout_form(form):
    print("Cart contents:", session.get('cart'))
    errors = []
    
    # Get and validate form fields
    name = form.get('name', '').strip()
    contact = form.get('contact', '').strip()
    email = form.get('email', '').strip()
    delivery = form.get('delivery', 'pickup').strip()
    building = form.get('building', '').strip()
    floor = form.get('floor', '').strip()
    payment = form.get('payment', '').strip()

    # Validate required fields
    if not name:
        errors.append("Full Name is required.")
    
    if not contact:
        errors.append("Contact Number is required.")
    elif not re.match(r'^\+?\d{7,15}$', contact):
        errors.append("Valid Contact Number required (7-15 digits).")
    
    if not email:
        errors.append("Email is required.")
    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append("Valid Email address is required.")
    
    # Validate delivery method
    if delivery not in ['pickup', 'home']:
        errors.append("Please select a valid delivery method.")
    
    # Validate delivery address if home delivery
    if delivery == 'home':
        if not building:
            errors.append("Building/Block is required for home delivery.")
        if not floor:
            errors.append("Floor/Room No. is required for home delivery.")
    
    # Validate payment method (now includes esewa)
    if not payment:
        errors.append("Please select a payment method.")
    elif payment not in ['cash', 'card', 'khalti', 'esewa']:
        errors.append("Please select a valid payment method.")
    
    return errors

# -------------------- UPDATED PROCESS ORDER --------------------
# def process_order(user, cart, form, calculated_total):
#     try:
#         khalti_token = form.get('khalti_token') if form.get('payment') == 'khalti' else None
#         esewa_ref_id = form.get('esewa_ref_id') if form.get('payment') == 'esewa' else None
        
#         # For testing: Skip Khalti verification if no secret key
#         if form.get('payment') == 'khalti':
#             if not khalti_token:
#                 print("Khalti payment selected but no token provided")
#                 return False
            
#             # Only verify if we have a secret key
#             if KHALTI_SECRET_KEY:
#                 if not verify_khalti_payment(khalti_token, calculated_total):
#                     print("Khalti payment verification failed")
#                     return False
#             else:
#                 print("TESTING MODE: Skipping Khalti verification (no secret key)")

#         order = Order(
#             user_id=user.id,
#             name=form['name'],
#             contact=form['contact'],
#             email=form['email'],
#             delivery=form['delivery'],
#             building=form.get('building', ''),
#             floor=form.get('floor', ''),
#             payment=form['payment'],
#             total_amount=calculated_total,
#             khalti_token=khalti_token,
#             esewa_ref_id=esewa_ref_id,  # Add eSewa reference ID
#             status='pending'
#         )
#         db.session.add(order)
#         db.session.flush()

#         # Add order items with their addons
#         for item in cart.values():
#             order_item = OrderItem(
#                 order_id=order.id,
#                 item_id=item['id'],
#                 name=item['name'],
#                 quantity=item['quantity'],
#                 price=item['price']
#             )
#             db.session.add(order_item)
#             db.session.flush()
            
#             # Add selected addons for this order item
#             if 'selected_addons' in item and item['selected_addons']:
#                 for addon_data in item['selected_addons']:
#                     order_addon = OrderAddon(
#                         order_item_id=order_item.id,
#                         addon_id=addon_data['id'],
#                         name=addon_data['name'],
#                         price=addon_data['price'],
#                         category=addon_data.get('category', ''),
#                         description=addon_data.get('description', '')
#                     )
#                     db.session.add(order_addon)

#         db.session.commit()
#         return True
        
#     except Exception as e:
#         db.session.rollback()
#         print(f"Order processing failed: {e}")
#         return False``

# Keep existing Khalti verification functions unchanged




# -------------------- FORM VALIDATION --------------------

# def validate_checkout_form(form):
#     print("Cart contents:", session.get('cart'))
#     errors = []
    
#     # Get and validate form fields
#     name = form.get('name', '').strip()
#     contact = form.get('contact', '').strip()
#     email = form.get('email', '').strip()
#     delivery = form.get('delivery', 'pickup').strip()
#     building = form.get('building', '').strip()
#     floor = form.get('floor', '').strip()
#     payment = form.get('payment', '').strip().lower()

#     # Validate required fields
#     if not name:
#         errors.append("Full Name is required.")
    
#     if not contact:
#         errors.append("Contact Number is required.")
#     elif not re.match(r'^\+?\d{7,15}$', contact):
#         errors.append("Valid Contact Number required (7-15 digits).")
    
#     if not email:
#         errors.append("Email is required.")
#     elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
#         errors.append("Valid Email address is required.")
    
#     # Validate delivery method
#     if delivery not in ['pickup', 'home']:
#         errors.append("Please select a valid delivery method.")
    
#     # Validate delivery address if home delivery
#     if delivery == 'home':
#         if not building:
#             errors.append("Building/Block is required for home delivery.")
#         if not floor:
#             errors.append("Floor/Room No. is required for home delivery.")
    
#     # Validate payment method
#     if not payment:
#         errors.append("Please select a payment method.")
#     elif payment not in ['cash', 'card', 'khalti']:
#         errors.append("Please select a valid payment method.")
    
#     return errors

# -------------------- PROCESS ORDER --------------------
# def process_order(user, cart, form, calculated_total):
#     try:
#         khalti_token = form.get('khalti_token') if form.get('payment') == 'khalti' else None
        
#         # For testing: Skip Khalti verification if no secret key
#         if form.get('payment') == 'khalti':
#             if not khalti_token:
#                 print("Khalti payment selected but no token provided")
#                 return False
            
#             # Only verify if we have a secret key
#             if KHALTI_SECRET_KEY:
#                 if not verify_khalti_payment(khalti_token, calculated_total):
#                     print("Khalti payment verification failed")
#                     return False
#             else:
#                 print("TESTING MODE: Skipping Khalti verification (no secret key)")

#         order = Order(
#             user_id=user.id,
#             name=form['name'],
#             contact=form['contact'],
#             email=form['email'],
#             delivery=form['delivery'],
#             building=form.get('building', ''),
#             floor=form.get('floor', ''),
#             payment=form['payment'],
#             total_amount=calculated_total,
#             khalti_token=khalti_token,
#             status='pending'   # Different status for testing
#         )
#         db.session.add(order)
#         db.session.flush()

#         # Add order items with their addons
#         for item in cart.values():
#             order_item = OrderItem(
#                 order_id=order.id,
#                 item_id=item['id'],
#                 name=item['name'],
#                 quantity=item['quantity'],
#                 price=item['price']
#             )
#             db.session.add(order_item)
#             db.session.flush()  # Flush to get the order_item.id
            
#             # Add selected addons for this order item
#             if 'selected_addons' in item and item['selected_addons']:
#                 for addon_data in item['selected_addons']:
#                     order_addon = OrderAddon(
#                         order_item_id=order_item.id,
#                         addon_id=addon_data['id'],
#                         name=addon_data['name'],
#                         price=addon_data['price'],
#                         category=addon_data.get('category', ''),
#                         description=addon_data.get('description', '')
#                     )
#                     db.session.add(order_addon)

#         db.session.commit()
#         return True
        
#     except Exception as e:
#         db.session.rollback()
#         print(f"Order processing failed: {e}")
#         return False
# # -------------------- KHALTI VERIFICATION (TEST MODE) --------------------

# def verify_khalti_payment(token, amount):
#     if not KHALTI_SECRET_KEY:
#         print("TEST MODE: Verification skipped")
#         return True

#     try:
#         headers = {
#             "Authorization": f"Key {KHALTI_SECRET_KEY}",
#             "Content-Type": "application/json"
#         }
#         payload = {
#             "token": token,
#             "amount": int(amount * 100)
#         }
#         response = requests.post(
#             "https://khalti.com/api/v2/payment/verify/",
#             headers=headers,
#             json=payload,
#             timeout=10
#         )

#         if response.status_code == 200:
#             data = response.json()
#             return data.get('amount') == int(amount * 100)
#         else:
#             print(f"Khalti response error: {response.text}")
#             return False

#     except Exception as e:
#         print(f"Khalti API error: {e}")
#         return False


# @app.route('/khalti-verify', methods=['POST'])
# def khalti_verify():
#     try:
#         data = request.get_json()
#         print("Received for Khalti verification:", data)  # DEBUG LOG

#         token = data.get('token')
#         amount = data.get('amount')

#         if not token or not amount:
#             return jsonify(success=False, message="Token and amount required"), 400

#         if not KHALTI_SECRET_KEY:
#             print("TEST MODE: Simulating verification")
#             return jsonify(success=True, message="Test verification success")

#         # Make sure amount is float
#         success = verify_khalti_payment(token, float(amount))
#         if success:
#             return jsonify(success=True, message="Payment verified")
#         else:
#             return jsonify(success=False, message="Verification failed"), 400

#     except Exception as e:
#         print(f"/khalti-verify error: {e}")
#         return jsonify(success=False, message="Server error"), 500

    
@app.route('/orders')
@login_required
def orders():
    user_id = session['user_id']
    user = User.query.get(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()
    return render_template('orders.html', user=user, orders=orders, active_page='orders')

@app.route('/transation_history')
@login_required
def transaction():
    user_id = session['user_id']
    
    # Join Payment with Order to ensure user-based filtering
    payments = (
        db.session.query(Payment)
        .join(Order)
        .filter(Order.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    
    return render_template(
        'transaction_history.html',
        user=User.query.get(user_id),
        payments=payments,
        active_page='transaction'
    )

    

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        phone = request.form.get('phone')

        # Validate email uniqueness
        email_exists = User.query.filter(and_(User.email == email, User.id != user.id)).first()
        if email_exists:
            flash('Email is already used by another user.', 'profile_danger')
            return redirect(url_for('profile'))

        # Validate phone uniqueness (if phone provided)
        if phone:
            phone_exists = User.query.filter(and_(User.phone == phone, User.id != user.id)).first()
            if phone_exists:
                flash('Phone number is already used by another user.', 'profile_danger')
                return redirect(url_for('profile'))

        # Update user info
        user.fullname = fullname
        user.email = email
        user.phone = phone

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'profile_success')
        except Exception as e:
            db.session.rollback()
            flash('Something went wrong while saving changes.', 'profile_danger')

        return redirect(url_for('profile'))

    # Calculate total orders count
    total_orders = Order.query.filter_by(user_id=user.id).count()

   
    total_points = db.session.query(
        db.func.coalesce(db.func.sum(Order.total_amount), 0)
    ).filter(Order.user_id == user.id).scalar()
    points = int(total_points // 100)


    # Calculate months since user joined
    months_since_joined = (datetime.utcnow().year - user.created_at.year) * 12 + (datetime.utcnow().month - user.created_at.month)
    if months_since_joined < 0:
        months_since_joined = 0

    return render_template(
        'profile.html', 
        user=user, 
        total_orders=total_orders,
        total_points=points,
        months_since_joined=months_since_joined,
        active_page='profile'
    )


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # ✅ Block admins here
            if user.role == 'admin':
                flash("Email not found", "danger")
            else:
                session['reset_user_id'] = user.id
                flash("Email found. Please reset your password.", "success")
                return redirect(url_for('reset_password'))
        else:
            flash("Email not found!", "danger")
    return render_template('forgot_password.html')
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    user_id = session.get('reset_user_id')
    if not user_id:
        flash("Session expired. Please try again.", "warning")
        return redirect(url_for('forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash("Invalid user!", "danger")
        return redirect(url_for('forgot_password'))

    

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            session.pop('reset_user_id', None)
            flash("Password reset successful! Please log in.", "success")
            return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)