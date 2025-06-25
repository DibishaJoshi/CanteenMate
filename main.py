from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime,timedelta,date,time
from flask_socketio import SocketIO,join_room, leave_room


import os
import functools
import re
import requests

from models import db, User, Category, Item, Attribute, AttributeValue ,Menu, Order, OrderItem,Review, ReviewHelpful, Addon, CartItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dibisha'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(days=7)
socketio = SocketIO(app, cors_allowed_origins="*")
KHALTI_PUBLIC_KEY = "Key test_public_key_dc74e0fd57cb46cd93832aee0a507256"
KHALTI_INITIATE_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
KHALTI_SECRET_KEY = "Key test_secret_key_f59e8b7d18b4499ca40f68195a846fd9"
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

        # Check if email or password is missing
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
        
        if '@' not in email or '.' not in email:
            flash("Enter a valid Email address.",'warning')

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

# Admin and feature pages
@app.route('/admin')
@login_required
def admin():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
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
    user= User.query.get(user_id)
    return render_template('index.html',user=user,active_page='dashboard',menu_items=menu_items)

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

    flash('Addon added successfully!', 'success')
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
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('addons'))

    try:
        price = float(price_str)
    except ValueError:
        flash('Price must be a valid number.', 'danger')
        return redirect(url_for('addons'))

    # Update addon
    addon.name = name
    addon.price = price
    addon.category = category
    addon.description = description
    addon.status = status

    db.session.commit()
    flash('Addon updated successfully!', 'success')
    return redirect(url_for('addons'))


@app.route('/admin/addons/delete/<int:addon_id>', methods=['POST'])
@login_required
def delete_addon(addon_id):
    addon = Addon.query.get_or_404(addon_id)
    db.session.delete(addon)
    db.session.commit()
    flash('Addon deleted successfully.', 'success')
    return redirect(url_for('addons'))




@app.route('/admin/items')
@login_required
def items():
    user_id = session['user_id']
    user = User.query.get(user_id)
    categories = Category.query.filter_by(status=True).all()
    items = Item.query.all()  # Fetch all items from DB
    return render_template('admin/items.html', categories=categories, user=user, items=items, active_page='items')

@app.route('/admin/add-item', methods=['POST'])
def add_item():
    item_id = request.form.get('item-id')  # <-- hidden input in form
    name = request.form.get('item-name')
    category_name = request.form.get('item-category')
    price = request.form.get('item-price')
    description = request.form.get('item-description')
    available = request.form.get('item-available') == 'on'
    image = request.files.get('item-image')

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

    # Check if this is an update or new insert
    if item_id:  # Editing existing item
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

        db.session.commit()
        flash("Item updated successfully!", "items_success")
    else:  # New item
        new_item = Item(
            name=name,
            price=float(price),
            category_id=category.id,
            description=description,
            image_filename=image_filename,
            available=available
        )
        db.session.add(new_item)
        db.session.commit()
        flash("Item added successfully!", "items_success")

    return redirect(url_for('items'))

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


@app.route('/admin/orders')
@login_required
def admin_orders():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/admin_orders.html',user=user,active_page='orders', orders=orders)
    
@app.route('/admin/orders/<int:order_id>')
def admin_order_view(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_view.html',user=user, order=order)

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



@app.route('/orders/<int:order_id>/review')
@login_required
def review_order(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('orders'))

    if order.status.lower() != 'delivered':
        flash('You can only review delivered orders.', 'warning')
        return redirect(url_for('orders'))

    # Get user's own reviews
    existing_reviews = Review.query.filter_by(order_id=order_id, user_id=user_id).all()
    reviews_by_item = {r.item_id: r for r in existing_reviews}
    reviewed_item_ids = [r.item_id for r in existing_reviews]

    # Get other users' reviews for each item
    other_reviews = {}
    for item in order.items:
        reviews = (
            Review.query
            .filter(
                Review.item_id == item.item_id,
                Review.user_id != user_id
            )
            .order_by(Review.id.desc())
            .limit(3)  # Show latest 3 reviews per item
            .all()
        )
        other_reviews[item.item_id] = reviews

    return render_template(
        'review_order.html',
        user=user,
        order=order,
        reviews_by_item=reviews_by_item,
        reviewed_item_ids=reviewed_item_ids,
        other_reviews=other_reviews,
        active_page='orders'
    )
@app.route('/orders/<int:order_id>/review', methods=['POST'])
@login_required
def submit_review(order_id):
    """Process review submission"""
    user_id = session.get('user_id')
    
    # Verify order belongs to user and is delivered
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order or order.status.lower() != 'delivered':
        flash('Invalid order for review.', 'review_danger')
        return redirect(url_for('orders'))
    
    try:
        # Get form data
        item_id = request.form.get('item_id')
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('review', '').strip()
        service_rating = request.form.get('service_rating')
        delivery_rating = request.form.get('delivery_rating')
        would_recommend = request.form.get('recommend') == 'yes'
        
        # Validate required fields
        if not item_id or rating < 1 or rating > 5:
            flash('Please provide a valid rating (1-5 stars).', 'review_danger')
            return redirect(url_for('review_order', order_id=order_id))
        
        # Verify item is in the order
        order_item = OrderItem.query.filter_by(order_id=order_id, item_id=item_id).first()
        if not order_item:
            flash('Item not found in this order.', 'review_danger')
            return redirect(url_for('review_order', order_id=order_id))
        existing_reviews = Review.query.filter_by(order_id=order_id, user_id=user_id).all()
        reviews_by_item = {r.item_id: r for r in existing_reviews}
        # Check if review already exists
        existing_review = Review.query.filter_by(
            order_id=order_id, 
            user_id=user_id, 
            item_id=item_id
        ).first()
        
        if existing_review:
            flash('You have already reviewed this item.', 'review_warning')
            return redirect(url_for('review_order', order_id=order_id))
        
        # Convert optional ratings
        service_rating = int(service_rating) if service_rating and service_rating.isdigit() else None
        delivery_rating = int(delivery_rating) if delivery_rating and delivery_rating.isdigit() else None
        
        # Create new review
        new_review = Review(
            user_id=user_id,
            order_id=order_id,
            item_id=item_id,
            rating=rating,
            comment=comment if comment else None,
            service_rating=service_rating,
            delivery_rating=delivery_rating,
            would_recommend=would_recommend,
            is_verified=True  
        )
        
        db.session.add(new_review)
        db.session.commit()
        
        flash('Thank you for your review!', 'success')
        return redirect(url_for('review_order', order_id=order_id))
        
    except ValueError:
        flash('Invalid rating value. Please select 1-5 stars.', 'danger')
        return redirect(url_for('review_order', order_id=order_id))
    except Exception as e:
        db.session.rollback()
        print(f"Review submission error: {e}")
        flash('Error submitting review. Please try again.', 'danger')
        return redirect(url_for('review_order', order_id=order_id))

@app.route('/item/<int:item_id>/reviews')
def item_reviews(item_id):
    """Show all reviews for an item"""
    item = Item.query.get_or_404(item_id)
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    rating_filter = request.args.get('rating', type=int)
    sort_by = request.args.get('sort', 'newest')  # newest, oldest, highest, lowest, helpful
    
    # Build query
    reviews_query = Review.query.filter_by(item_id=item_id)
    
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
    total_reviews = Review.query.filter_by(item_id=item_id).count()
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(item_id=item_id).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else 0
    
    # Get rating distribution
    rating_distribution = {}
    for rating in range(1, 6):
        count = Review.query.filter_by(item_id=item_id, rating=rating).count()
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_distribution[rating] = {'count': count, 'percentage': round(percentage, 1)}
    
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    
    return render_template('item_reviews.html',
                         item=item,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         avg_rating=avg_rating,
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
    
    # Check if user has already voted on this review
    existing_vote = ReviewHelpful.query.filter_by(
        review_id=review_id, 
        user_id=user_id
    ).first()
    
    try:
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
    per_page = 20
    
    # Build query
    reviews_query = Review.query.join(User).join(Item)
    
    # Apply filters
    if rating_filter and 1 <= rating_filter <= 5:
        reviews_query = reviews_query.filter(Review.rating == rating_filter)
    
    if item_filter:
        reviews_query = reviews_query.filter(Review.item_id == item_filter)
    
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
    avg_rating = db.session.query(db.func.avg(Review.rating)).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else 0
    
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(5).all()
    
    # Get all items for filter dropdown
    items = Item.query.order_by(Item.name).all()
    
    return render_template('admin/admin_reviews.html',
                         user=user,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         avg_rating=avg_rating,
                         recent_reviews=recent_reviews,
                         items=items,
                         current_rating_filter=rating_filter,
                         current_item_filter=item_filter,
                         active_page='reviews')

@app.route('/admin/reviews/<int:review_id>/toggle-visibility', methods=['POST'])
@login_required
def toggle_review_visibility(review_id):
    """Toggle review visibility (admin only)"""
    if session.get('user_role') != 'admin':
        return redirect(url_for('user_dashboard'))
    
    review = Review.query.get_or_404(review_id)
    
    try:
        # Add a visibility field to Review model if needed
        # For now, we'll use a simple approach
        review.is_verified = not review.is_verified
        db.session.commit()
        
        status = "visible" if review.is_verified else "hidden"
        flash(f'Review marked as {status}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating review visibility.', 'danger')
    
    return redirect(url_for('admin_reviews'))
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
    item = Item.query.get(item_id)

    if not item:
        flash('Invalid item.', 'cart_error')
        return redirect(url_for('user_menu'))

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
            created_date=today  # ✅ Important: Set the created_date
        )
        db.session.add(new_item)

    db.session.commit()
    flash(f'Added \"{item.name}\" to cart', 'cart_success')
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


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    user_id = session['user_id']
    user = User.query.get(user_id)
    today = date.today()

    # Fetch cart items from DB for user (optionally clean old items like cart page)
    CartItem.query.filter(CartItem.user_id == user_id, CartItem.created_date != today).delete()
    db.session.commit()

    cart_items = CartItem.query.filter_by(user_id=user_id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    # Calculate subtotal
    subtotal = sum(ci.quantity * ci.item.price for ci in cart_items)
    tax = subtotal * 0.08
    service_fee = 10
    total = subtotal + tax + service_fee

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
                                   cart=cart_items,
                                   total=total,
                                   has_errors=True)

        # Prepare cart dict for process_order
        cart_dict = {}
        for ci in cart_items:
            cart_dict[ci.item_id] = {
                'id': ci.item_id,
                'name': ci.item.name,
                'price': ci.item.price,
                'quantity': ci.quantity
            }

        if process_order(user, cart_dict, request.form, total):
            # Clear cart items from DB after order
            CartItem.query.filter_by(user_id=user_id).delete()
            db.session.commit()

            flash('Order placed successfully!', 'success')
            return redirect(url_for('orders'))
        else:
            flash('Order failed. Please try again.', 'danger')
            return render_template('checkout.html',
                                   user=user,
                                   form_data=request.form,
                                   cart=cart_items,
                                   total=total,
                                   has_errors=True)

    # GET request: show form
    return render_template('checkout.html',
                           user=user,
                           form_data={},
                           cart=cart_items,
                           total=total,
                           has_errors=False)


# -------------------- FORM VALIDATION --------------------

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
    
    # Validate payment method
    if not payment:
        errors.append("Please select a payment method.")
    elif payment not in ['cash', 'card', 'khalti']:
        errors.append("Please select a valid payment method.")
    
    return errors

# -------------------- PROCESS ORDER --------------------

def process_order(user, cart, form, calculated_total):
    try:
        khalti_token = form.get('khalti_token') if form.get('payment') == 'khalti' else None
        
        # For testing: Skip Khalti verification if no secret key
        if form.get('payment') == 'khalti':
            if not khalti_token:
                print("Khalti payment selected but no token provided")
                return False
            
            # Only verify if we have a secret key
            if KHALTI_SECRET_KEY:
                if not verify_khalti_payment(khalti_token, calculated_total):
                    print("Khalti payment verification failed")
                    return False
            else:
                print("TESTING MODE: Skipping Khalti verification (no secret key)")

        order = Order(
            user_id=user.id,
            name=form['name'],
            contact=form['contact'],
            email=form['email'],
            delivery=form['delivery'],
            building=form.get('building', ''),
            floor=form.get('floor', ''),
            payment=form['payment'],
            total_amount=calculated_total,
            khalti_token=khalti_token,
            status='pending'   # Different status for testing
        )
        db.session.add(order)
        db.session.flush()

        # Add order items
        for item in cart.values():
            order_item = OrderItem(
                order_id=order.id,
                item_id=item['id'],
                name=item['name'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)

        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Order processing failed: {e}")
        return False

# -------------------- KHALTI VERIFICATION (TEST MODE) --------------------

def verify_khalti_payment(token, amount):
    if not KHALTI_SECRET_KEY:
        print("TEST MODE: Verification skipped")
        return True

    try:
        headers = {
            "Authorization": f"Key {KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "token": token,
            "amount": int(amount * 100)
        }
        response = requests.post(
            "https://khalti.com/api/v2/payment/verify/",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('amount') == int(amount * 100)
        else:
            print(f"Khalti response error: {response.text}")
            return False

    except Exception as e:
        print(f"Khalti API error: {e}")
        return False


@app.route('/khalti-verify', methods=['POST'])
def khalti_verify():
    try:
        data = request.get_json()
        print("Received for Khalti verification:", data)  # DEBUG LOG

        token = data.get('token')
        amount = data.get('amount')

        if not token or not amount:
            return jsonify(success=False, message="Token and amount required"), 400

        if not KHALTI_SECRET_KEY:
            print("TEST MODE: Simulating verification")
            return jsonify(success=True, message="Test verification success")

        # Make sure amount is float
        success = verify_khalti_payment(token, float(amount))
        if success:
            return jsonify(success=True, message="Payment verified")
        else:
            return jsonify(success=False, message="Verification failed"), 400

    except Exception as e:
        print(f"/khalti-verify error: {e}")
        return jsonify(success=False, message="Server error"), 500

    
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
    user = User.query.get(user_id)
    return render_template('transaction_history.html',user=user, active_page='transaction')

    
@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('profile.html', user=user,active_page='profile')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)