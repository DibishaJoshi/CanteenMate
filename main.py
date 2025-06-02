from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime,timedelta
import os
import functools

from models import db, User, Category, Item, Attribute, AttributeValue ,Menu

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
    return render_template('admin/addons.html', user=user, active_page='addons')

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
        item.price = int(float(price) * 100)
        item.description = description
        item.available = available

        if image_filename:
            item.image_filename = image_filename

        db.session.commit()
        flash("Item updated successfully!", "items_success")
    else:  # New item
        new_item = Item(
            name=name,
            price=int(float(price) * 100),
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
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template("admin/admin_orders.html", user=user,active_page='admin_orders', orders=orders)
    
@app.route('/notifications')
@login_required
def get_notifications():
    # Replace with DB query in real app
    notifications = [
        {"message": "🍔 Your Order is being prepared" ,"time": datetime.now().strftime("%I:%M %p")},
        {"message": "⚠️ Your Order is canceled", "time": datetime.now().strftime("%I:%M %p")},
        {"message": "✅ Your order is delivered", "time": datetime.now().strftime("%I:%M %p")},
    ]
    return jsonify(notifications)


@app.route('/orders')
@login_required
def orders():
    user_id = session['user_id']
    user = User.query.get(user_id)

@app.route('/menu')
@login_required
def user_menu():
    # Get day from query parameter or use today's real-time day
    current_day = request.args.get('day')
    if not current_day:
        current_day = datetime.today().strftime('%A').lower()  # e.g., 'monday', 'tuesday'

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

@app.route('/transation_history')
@login_required
def transaction():
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('transaction_history.html',user=user, active_page='transaction')

@app.route('/cart')
@login_required
def cart():
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('cart.html', user=user,active_page='settings')
    
@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('profile.html', user=user,active_page='profile')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
