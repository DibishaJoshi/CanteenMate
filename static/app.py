# import os
# import sqlite3
# import datetime
# from flask import Flask, render_template, request, redirect, url_for, flash, session, g
# from werkzeug.security import generate_password_hash, check_password_hash
# from functools import wraps

# # Initialize Flask application
# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'your_secret_key_here'
# app.config['DATABASE'] = os.path.join(app.instance_path, 'canteen.db')

# # Ensure the instance folder exists
# try:
#     os.makedirs(app.instance_path)
# except OSError:
#     pass

# # Database connection helper functions
# def get_db():
#     if 'db' not in g:
#         g.db = sqlite3.connect(
#             app.config['DATABASE'],
#             detect_types=sqlite3.PARSE_DECLTYPES
#         )
#         g.db.row_factory = sqlite3.Row
#     return g.db

# def close_db(e=None):
#     db = g.pop('db', None)
#     if db is not None:
#         db.close()

# # Initialize the database
# def init_db():
#     db = get_db()
#     with app.open_resource('schema.sql') as f:
#         db.executescript(f.read().decode('utf8'))
#     db.commit()

# # Click command to initialize the database
# @app.cli.command('init-db')
# def init_db_command():
#     """Clear the existing data and create new tables."""
#     init_db()
#     print('Initialized the database.')

# # Authentication decorators
# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             flash('Please log in to access this page', 'error')
#             return redirect(url_for('login'))
#         return f(*args, **kwargs)
#     return decorated_function

# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             flash('Please log in to access this page', 'error')
#             return redirect(url_for('login'))
#         if session.get('user_role') != 'admin':
#             flash('You need admin privileges to access this page', 'error')
#             return redirect(url_for('index'))
#         return f(*args, **kwargs)
#     return decorated_function

# # Register teardown function
# app.teardown_appcontext(close_db)

# # Routes
# @app.route('/')
# def index():
#     db = get_db()
#     categories = db.execute('SELECT * FROM categories').fetchall()
#     popular_items = db.execute(
#         'SELECT * FROM items ORDER BY popularity DESC LIMIT 6'
#     ).fetchall()
#     return render_template('index.html', categories=categories, popular_items=popular_items)

# @app.route('/menu')
# def menu():
#     db = get_db()
#     category_id = request.args.get('category', type=int)
    
#     if category_id:
#         items = db.execute(
#             'SELECT * FROM items WHERE category_id = ?',
#             (category_id,)
#         ).fetchall()
#         category = db.execute(
#             'SELECT name FROM categories WHERE id = ?',
#             (category_id,)
#         ).fetchone()
#         category_name = category['name'] if category else "All Items"
#     else:
#         items = db.execute('SELECT * FROM items').fetchall()
#         category_name = "All Items"
        
#     categories = db.execute('SELECT * FROM categories').fetchall()
#     return render_template('menu.html', items=items, categories=categories, current_category=category_name)

# @app.route('/cart')
# @login_required
# def cart():
#     if 'cart' not in session:
#         session['cart'] = []
    
#     cart_items = []
#     total = 0
    
#     if session['cart']:
#         db = get_db()
#         for item_id, quantity in session['cart']:
#             item = db.execute(
#                 'SELECT * FROM items WHERE id = ?',
#                 (item_id,)
#             ).fetchone()
#             if item:
#                 item_total = item['price'] * quantity
#                 cart_items.append({
#                     'id': item['id'],
#                     'name': item['name'],
#                     'price': item['price'],
#                     'quantity': quantity,
#                     'total': item_total
#                 })
#                 total += item_total
    
#     return render_template('cart.html', cart_items=cart_items, total=total)

# @app.route('/add_to_cart', methods=['POST'])
# @login_required
# def add_to_cart():
#     item_id = request.form.get('item_id', type=int)
#     quantity = request.form.get('quantity', 1, type=int)
    
#     if 'cart' not in session:
#         session['cart'] = []
    
#     # Check if item is already in cart
#     cart = session['cart']
#     for i, (cart_item_id, cart_quantity) in enumerate(cart):
#         if cart_item_id == item_id:
#             cart[i] = (item_id, cart_quantity + quantity)
#             session.modified = True
#             flash('Item quantity updated in cart', 'success')
#             return redirect(url_for('cart'))
    
#     # If not in cart, add it
#     cart.append((item_id, quantity))
#     session['cart'] = cart
#     flash('Item added to cart', 'success')
#     return redirect(url_for('menu'))

# @app.route('/update_cart', methods=['POST'])
# @login_required
# def update_cart():
#     item_id = request.form.get('item_id', type=int)
#     quantity = request.form.get('quantity', 1, type=int)
    
#     if 'cart' not in session:
#         return redirect(url_for('cart'))
    
#     cart = session['cart']
#     for i, (cart_item_id, _) in enumerate(cart):
#         if cart_item_id == item_id:
#             if quantity <= 0:
#                 cart.pop(i)
#             else:
#                 cart[i] = (item_id, quantity)
#             session.modified = True
#             break
    
#     flash('Cart updated', 'success')
#     return redirect(url_for('cart'))

# @app.route('/clear_cart')
# @login_required
# def clear_cart():
#     session['cart'] = []
#     flash('Cart cleared', 'success')
#     return redirect(url_for('cart'))

# @app.route('/checkout', methods=['GET', 'POST'])
# @login_required
# def checkout():
#     if 'cart' not in session or not session['cart']:
#         flash('Your cart is empty', 'error')
#         return redirect(url_for('cart'))
    
#     if request.method == 'POST':
#         db = get_db()
        
#         # Create order
#         db.execute(
#             'INSERT INTO orders (user_id, order_date, status, total) VALUES (?, ?, ?, ?)',
#             (
#                 session['user_id'],
#                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                 'pending',
#                 float(request.form.get('total_amount'))
#             )
#         )
        
#         order_id = db.lastrowid
        
#         # Add order items
#         for item_id, quantity in session['cart']:
#             item = db.execute(
#                 'SELECT price FROM items WHERE id = ?',
#                 (item_id,)
#             ).fetchone()
#             if item:
#                 db.execute(
#                     'INSERT INTO order_items (order_id, item_id, quantity, price) VALUES (?, ?, ?, ?)',
#                     (
#                         order_id,
#                         item_id,
#                         quantity,
#                         item['price']
#                     )
#                 )
                
#                 # Update item popularity
#                 db.execute(
#                     'UPDATE items SET popularity = popularity + ? WHERE id = ?',
#                     (quantity, item_id)
#                 )
        
#         db.commit()
        
#         # Clear cart
#         session['cart'] = []
        
#         flash('Order placed successfully!', 'success')
#         return redirect(url_for('orders'))
    
#     return render_template('checkout.html')

# @app.route('/orders')
# @login_required
# def orders():
#     db = get_db()
    
#     if session.get('user_role') == 'admin':
#         orders = db.execute(
#             '''
#             SELECT o.*, u.username
#             FROM orders o
#             JOIN users u ON o.user_id = u.id
#             ORDER BY o.order_date DESC
#             '''
#         ).fetchall()
#     else:
#         orders = db.execute(
#             'SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC',
#             (session['user_id'],)
#         ).fetchall()
    
#     order_details = {}
#     for order in orders:
#         items = db.execute(
#             '''
#             SELECT oi.*, i.name
#             FROM order_items oi
#             JOIN items i ON oi.item_id = i.id
#             WHERE oi.order_id = ?
#             ''',
#             (order['id'],)
#         ).fetchall()
#         order_details[order['id']] = items
    
#     return render_template('orders.html', orders=orders, order_details=order_details)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
        
#         db = get_db()
#         error = None
        
#         user = db.execute(
#             'SELECT * FROM users WHERE username = ?',
#             (username,)
#         ).fetchone()
        
#         if user is None:
#             error = 'Invalid username or password'
#         elif not check_password_hash(user['password'], password):
#             error = 'Invalid username or password'
        
#         if error is None:
#             session.clear()
#             session['user_id'] = user['id']
#             session['username'] = user['username']
#             session['user_role'] = user['role']
            
#             flash(f'Welcome back, {username}!', 'success')
            
#             # Redirect admin to admin dashboard
#             if user['role'] == 'admin':
#                 return redirect(url_for('admin_dashboard'))
#             return redirect(url_for('index'))
        
#         flash(error, 'error')
    
#     return render_template('auth/login.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
#         email = request.form.get('email')
        
#         db = get_db()
#         error = None
        
#         if not username:
#             error = 'Username is required'
#         elif not password:
#             error = 'Password is required'
#         elif not email:
#             error = 'Email is required'
#         elif db.execute(
#             'SELECT id FROM users WHERE username = ?',
#             (username,)
#         ).fetchone() is not None:
#             error = f'User {username} is already registered'
        
#         if error is None:
#             # First user is admin, rest are customers
#             count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
#             role = 'admin' if count == 0 else 'customer'
            
#             db.execute(
#                 'INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
#                 (username, generate_password_hash(password), email, role)
#             )
#             db.commit()
            
#             flash('Registration successful! Please log in.', 'success')
#             return redirect(url_for('login'))
        
#         flash(error, 'error')
    
#     return render_template('auth/register.html')

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash('You have been logged out', 'success')
#     return redirect(url_for('index'))

# # Admin routes
# @app.route('/admin')
# @admin_required
# def admin_dashboard():
#     db = get_db()
    
#     # Get summary statistics
#     total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
#     total_items = db.execute('SELECT COUNT(*) FROM items').fetchone()[0]
#     total_orders = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    
#     # Get recent orders
#     recent_orders = db.execute(
#         '''
#         SELECT o.*, u.username
#         FROM orders o
#         JOIN users u ON o.user_id = u.id
#         ORDER BY o.order_date DESC
#         LIMIT 5
#         '''
#     ).fetchall()
    
#     # Get popular items
#     popular_items = db.execute(
#         'SELECT * FROM items ORDER BY popularity DESC LIMIT 5'
#     ).fetchall()
    
#     return render_template(
#         'admin/dashboard.html',
#         total_users=total_users,
#         total_items=total_items,
#         total_orders=total_orders,
#         recent_orders=recent_orders,
#         popular_items=popular_items
#     )

# @app.route('/admin/categories', methods=['GET', 'POST'])
# @admin_required
# def admin_categories():
#     db = get_db()
    
#     if request.method == 'POST':
#         action = request.form.get('action')
        
#         if action == 'add':
#             name = request.form.get('name')
#             description = request.form.get('description', '')
            
#             if name:
#                 db.execute(
#                     'INSERT INTO categories (name, description) VALUES (?, ?)',
#                     (name, description)
#                 )
#                 db.commit()
#                 flash('Category added successfully', 'success')
#             else:
#                 flash('Category name is required', 'error')
                
#         elif action == 'edit':
#             category_id = request.form.get('category_id', type=int)
#             name = request.form.get('name')
#             description = request.form.get('description', '')
            
#             if category_id and name:
#                 db.execute(
#                     'UPDATE categories SET name = ?, description = ? WHERE id = ?',
#                     (name, description, category_id)
#                 )
#                 db.commit()
#                 flash('Category updated successfully', 'success')
#             else:
#                 flash('Invalid category data', 'error')
                
#         elif action == 'delete':
#             category_id = request.form.get('category_id', type=int)
            
#             if category_id:
#                 # Check if category has items
#                 items = db.execute(
#                     'SELECT COUNT(*) FROM items WHERE category_id = ?',
#                     (category_id,)
#                 ).fetchone()[0]
                
#                 if items > 0:
#                     flash('Cannot delete category with items', 'error')
#                 else:
#                     db.execute(
#                         'DELETE FROM categories WHERE id = ?',
#                         (category_id,)
#                     )
#                     db.commit()
#                     flash('Category deleted successfully', 'success')
#             else:
#                 flash('Invalid category ID', 'error')
    
#     categories = db.execute('SELECT * FROM categories').fetchall()
#     return render_template('admin/categories.html', categories=categories)

# @app.route('/admin/items', methods=['GET', 'POST'])
# @admin_required
# def admin_items():
#     db = get_db()
    
#     if request.method == 'POST':
#         action = request.form.get('action')
        
#         if action == 'add':
#             name = request.form.get('name')
#             description = request.form.get('description', '')
#             price = request.form.get('price', type=float)
#             category_id = request.form.get('category_id', type=int)
#             image_url = request.form.get('image_url', '')
            
#             if name and price and category_id:
#                 db.execute(
#                     '''
#                     INSERT INTO items (name, description, price, category_id, image_url, popularity)
#                     VALUES (?, ?, ?, ?, ?, 0)
#                     ''',
#                     (name, description, price, category_id, image_url)
#                 )
#                 db.commit()
#                 flash('Item added successfully', 'success')
#             else:
#                 flash('Name, price, and category are required', 'error')
                
#         elif action == 'edit':
#             item_id = request.form.get('item_id', type=int)
#             name = request.form.get('name')
#             description = request.form.get('description', '')
#             price = request.form.get('price', type=float)
#             category_id = request.form.get('category_id', type=int)
#             image_url = request.form.get('image_url', '')
            
#             if item_id and name and price and category_id:
#                 db.execute(
#                     '''
#                     UPDATE items
#                     SET name = ?, description = ?, price = ?, category_id = ?, image_url = ?
#                     WHERE id = ?
#                     ''',
#                     (name, description, price, category_id, image_url, item_id)
#                 )
#                 db.commit()
#                 flash('Item updated successfully', 'success')
#             else:
#                 flash('Invalid item data', 'error')
                
#         elif action == 'delete':
#             item_id = request.form.get('item_id', type=int)
            
#             if item_id:
#                 # Check if item is in any orders
#                 order_items = db.execute(
#                     'SELECT COUNT(*) FROM order_items WHERE item_id = ?',
#                     (item_id,)
#                 ).fetchone()[0]
                
#                 if order_items > 0:
#                     flash('Cannot delete item used in orders', 'error')
#                 else:
#                     db.execute(
#                         'DELETE FROM items WHERE id = ?',
#                         (item_id,)
#                     )
#                     db.commit()
#                     flash('Item deleted successfully', 'success')
#             else:
#                 flash('Invalid item ID', 'error')
    
#     items = db.execute(
#         '''
#         SELECT i.*, c.name as category_name
#         FROM items i
#         JOIN categories c ON i.category_id = c.id
#         '''
#     ).fetchall()
#     categories = db.execute('SELECT * FROM categories').fetchall()
#     return render_template('admin/items.html', items=items, categories=categories)

# @app.route('/admin/orders', methods=['GET', 'POST'])
# @admin_required
# def admin_orders():
#     db = get_db()
    
#     if request.method == 'POST':
#         action = request.form.get('action')
        
#         if action == 'update_status':
#             order_id = request.form.get('order_id', type=int)
#             status = request.form.get('status')
            
#             if order_id and status:
#                 db.execute(
#                     'UPDATE orders SET status = ? WHERE id = ?',
#                     (status, order_id)
#                 )
#                 db.commit()
#                 flash('Order status updated', 'success')
#             else:
#                 flash('Invalid order data', 'error')
    
#     orders = db.execute(
#         '''
#         SELECT o.*, u.username
#         FROM orders o
#         JOIN users u ON o.user_id = u.id
#         ORDER BY o.order_date DESC
#         '''
#     ).fetchall()
    
#     order_details = {}
#     for order in orders:
#         items = db.execute(
#             '''
#             SELECT oi.*, i.name
#             FROM order_items oi
#             JOIN items i ON oi.item_id = i.id
#             WHERE oi.order_id = ?
#             ''',
#             (order['id'],)
#         ).fetchall()
#         order_details[order['id']] = items
    
#     return render_template('admin/orders.html', orders=orders, order_details=order_details)

# @app.route('/admin/users', methods=['GET', 'POST'])
# @admin_required
# def admin_users():
#     db = get_db()
    
#     if request.method == 'POST':
#         action = request.form.get('action')
        
#         if action == 'update_role':
#             user_id = request.form.get('user_id', type=int)
#             role = request.form.get('role')
            
#             if user_id and role:
#                 # Prevent removing last admin
#                 if role != 'admin':
#                     admin_count = db.execute(
#                         "SELECT COUNT(*) FROM users WHERE role = 'admin'"
#                     ).fetchone()[0]
                    
#                     current_role = db.execute(
#                         'SELECT role FROM users WHERE id = ?',
#                         (user_id,)
#                     ).fetchone()['role']
                    
#                     if admin_count <= 1 and current_role == 'admin':
#                         flash('Cannot remove the last admin', 'error')
#                         return redirect(url_for('admin_users'))
                
#                 db.execute(
#                     'UPDATE users SET role = ? WHERE id = ?',
#                     (role, user_id)
#                 )
#                 db.commit()
#                 flash('User role updated', 'success')
#             else:
#                 flash('Invalid user data', 'error')
    
#     users = db.execute('SELECT * FROM users').fetchall()
#     return render_template('admin/users.html', users=users)

# # Run the application
# if __name__ == '__main__':
#     app.run(debug=True)
# ```
