from main import app, db
from models import Order, Payment
from datetime import datetime
import json

def migrate_database():
    """
    Migrate existing database to include Payment table and 
    migrate existing payment data from Order table
    """
    print("=== Starting Database Migration ===")
    
    with app.app_context():
        try:
            # Create the new Payment table (and any other missing tables)
            print("Creating Payment table (and ensuring all tables exist)...")
            db.create_all()
            print("✅ Payment table created / ensured successfully")
            
            # Identify orders that do not yet have a Payment record
            print("Finding orders without associated payments...")
            existing_payment_order_ids = db.session.query(Payment.order_id).distinct()
            orders_to_migrate = Order.query.filter(~Order.id.in_(existing_payment_order_ids)).all()
            total_orders = len(orders_to_migrate)
            print(f"Found {total_orders} orders to migrate payment data for.")
            
            orders_migrated = 0
            fallback_pending = 0

            for order in orders_to_migrate:
                # Determine payment method (fallback to 'cash' if missing)
                payment_method = (order.payment or 'cash').lower()
                
                # Determine payment_status heuristically
                if payment_method in ['khalti', 'esewa']:
                    has_token = bool(order.khalti_token) if payment_method == 'khalti' else bool(order.esewa_transaction_code)
                    if has_token:
                        payment_status = 'completed'
                    else:
                        payment_status = 'pending'
                elif payment_method == 'cash':
                    if order.status and order.status.lower() in ['completed', 'paid']:
                        payment_status = 'completed'
                    else:
                        payment_status = 'pending'
                else:
                    payment_status = 'pending'

                # Amount: prefer stored total_amount, fallback to computed total_price if available
                try:
                    amount = float(order.total_amount)
                except Exception:
                    # fallback
                    amount = float(order.total_price if hasattr(order, 'total_price') else 0.0)

                # Build the new Payment record
                payment_kwargs = {
                    'order_id': order.id,
                    'payment_method': payment_method,
                    'payment_status': payment_status,
                    'amount': amount,
                    'created_at': order.created_at or datetime.utcnow(),
                }

                # Gateway-specific assignment
                if payment_method == 'khalti':
                    payment_kwargs['khalti_token'] = order.khalti_token
                    payment_kwargs['transaction_id'] = order.khalti_token  # best-effort
                elif payment_method == 'esewa':
                    payment_kwargs['esewa_transaction_uuid'] = order.esewa_transaction_code
                    payment_kwargs['transaction_id'] = order.esewa_transaction_code
                else:
                    # for cash or unknown, leave gateway-specific fields empty
                    pass

                # If marked completed, set completed_at same as order creation as best guess
                if payment_status == 'completed':
                    payment_kwargs['completed_at'] = order.created_at or datetime.utcnow()

                # Optionally store original order payment info for traceability
                gateway_resp = {
                    'original_order_payment_field': order.payment,
                    'khalti_token': order.khalti_token,
                    'esewa_transaction_code': order.esewa_transaction_code,
                    'order_status': order.status
                }
                payment_kwargs['gateway_response'] = json.dumps(gateway_resp, default=str)

                # Create and add
                payment = Payment(**payment_kwargs)
                db.session.add(payment)
                orders_migrated += 1

            db.session.commit()
            print(f"✅ Migrated {orders_migrated} order(s) into Payment records.")
            if total_orders == 0:
                print("No orders required migration.")
            print("=== Database Migration Completed ===")
        except Exception as e:
            db.session.rollback()
            print("❌ Migration failed, rolled back changes.")
            print("Error details:", str(e))
            raise  # re-raise so caller can detect failure
