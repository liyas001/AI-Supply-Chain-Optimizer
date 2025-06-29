import os
import smtplib
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from llama_cpp import Llama
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from twilio.rest import Client
from alert_service import send_email
from config.db import get_connection
from services import forecast_model
from services.forecast_model import generate_forecast_plot
from llama_handler import ask_local_ai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")
llama = Llama(
    model_path = r"C:\Users\liyas\PycharmProjects\PythonProject1\models\llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=35
)
# Email sending function
def send_email(to_email, subject, message):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
def send_alert_email_to_admins(subject, message):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT email, phone_number FROM users WHERE role = 'admin'")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    for admin in admins:
        receiver_email = admin['email']
        send_email(receiver_email, subject, message)

        if admin.get('phone_number'):
            send_sms(admin['phone_number'], message)

def send_sms(to_number, message):
    TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=to_number
        )
        print(f"SMS sent to {to_number}")
    except Exception as e:
        print(f"Failed to send SMS to {to_number}: {e}")

# Alert Trigger Example
@app.route('/trigger_alert')
def trigger_alert():
    subject = "🚨 Alert: Inventory Issue"
    message = "Low inventory detected in warehouse. Please check the system for more details."
    send_alert_email_to_admins(subject, message)
    flash("Alert email sent to all admins.")
    return redirect(url_for('alerts'))
@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user'] = {
                'user_id': user['user_id'],
                'username': user['username'],
                'role': user['role']
            }
            return redirect(url_for('dashboard'))
        flash("Invalid username or password.")
        return redirect(url_for('login'))

    return render_template('login.html')

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone_number = request.form['phone']
        email = request.form['email']
        role = request.form['role']

        if role not in ['admin', 'manager']:
            flash("Invalid role selected.")
            return redirect(url_for('signup'))

        password_hash = generate_password_hash(password)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash("Username already exists.")
            conn.close()
            return redirect(url_for('signup'))

        cursor.execute("""
            INSERT INTO users (username, password_hash, role, phone_number, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, password_hash, role, phone_number, email))

        conn.commit()
        conn.close()
        flash("Sign up successful. Please log in.")
        return redirect(url_for('login'))

    return render_template('signup.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('user'))

# Products
@app.route('/products')
def products():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Products")
    products_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("products.html", products=products_data, user=session.get('user'))

# Warehouses
@app.route('/warehouses')
def warehouses():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Warehouses")
    warehouses_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("warehouses.html", warehouses=warehouses_data, user=session.get('user'))

# Inventory
@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    THRESHOLD = 1000
    cursor.execute(f"""
        SELECT 
            p.name AS product, 
            w.name AS warehouse, 
            i.quantity,
            CASE 
                WHEN i.quantity < {THRESHOLD} THEN 'Low Stock' 
                ELSE 'Healthy' 
            END AS status
        FROM Inventory i
        JOIN Products p ON i.product_id = p.product_id
        JOIN Warehouses w ON i.warehouse_id = w.warehouse_id
    """)
    inventory_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("inventory.html", inventory=inventory_data, user=session.get('user'))

# Suppliers
@app.route('/suppliers')
def suppliers():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Suppliers")
    suppliers_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("suppliers.html", suppliers=suppliers_data, user=session.get('user'))

# Orders
@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT o.order_id, p.name AS product_name, s.name AS supplier_name,
               w.name AS warehouse_name, o.quantity, o.order_date
        FROM Orders o
        JOIN Products p ON o.product_id = p.product_id
        JOIN Suppliers s ON o.supplier_id = s.supplier_id
        JOIN Warehouses w ON o.warehouse_id = w.warehouse_id
    """)
    orders_data = cursor.fetchall()

    # Fetch suppliers and warehouses for form dropdowns
    cursor.execute("SELECT supplier_id, name FROM Suppliers")
    suppliers = cursor.fetchall()
    cursor.execute("SELECT warehouse_id, name FROM Warehouses")
    warehouses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('orders.html', orders=orders_data,
                           suppliers=suppliers, warehouses=warehouses,
                           user=session.get('user'))
@app.route('/add_order', methods=['POST'])
def add_order():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    product_name = request.form['product_name']
    supplier_id = request.form['supplier_id']
    warehouse_id = request.form['warehouse_id']
    quantity = int(request.form['quantity'])

    # 1. Check if product already exists
    cursor.execute("SELECT product_id FROM Products WHERE name = %s", (product_name,))
    product = cursor.fetchone()

    if product:
        product_id = product['product_id']
    else:
        # Automatically assign category and SKU
        auto_category = "General"  # or use logic like product_name.split()[0]
        import time
        auto_sku = f"SKU-{int(time.time())}"  # unique SKU using timestamp

        # Insert product
        cursor.execute("""
            INSERT INTO Products (name, category, sku)
            VALUES (%s, %s, %s)
        """, (product_name, auto_category, auto_sku))
        product_id = cursor.lastrowid

    # 2. Insert order
    cursor.execute("""
        INSERT INTO Orders (product_id, supplier_id, warehouse_id, quantity, order_date)
        VALUES (%s, %s, %s, %s, CURDATE())
    """, (product_id, supplier_id, warehouse_id, quantity))
    cursor.execute("SELECT LAST_INSERT_ID() AS order_id")
    new_order_id = cursor.fetchone()['order_id']

    # 4. Pick a random existing route from the Shipments table
    cursor.execute("SELECT DISTINCT route FROM Shipments")
    available_routes = cursor.fetchall()

    if available_routes:
        import random
        auto_route = random.choice([r['route'] for r in available_routes])
    else:
        auto_route = "Default Route"  # Fallback if no routes exist

    # 5. Generate random CO2 emission
    import random
    auto_co2 = round(random.uniform(0.5, 5.0), 2)

    # 6. Insert into Shipments table
    cursor.execute("""
                   INSERT INTO Shipments (order_id, route, co2_emission, warehouse_id)
                   VALUES (%s, %s, %s, %s)
                   """, (new_order_id, auto_route, auto_co2, warehouse_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Order added successfully.")
    return redirect(url_for('orders'))


@app.route('/mark_delivered/<int:order_id>', methods=['POST'])
def mark_delivered(order_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch order details
    cursor.execute("""
        SELECT product_id, quantity, warehouse_id
        FROM Orders
        WHERE order_id = %s
    """, (order_id,))
    order = cursor.fetchone()

    if not order:
        conn.close()
        flash("Order not found.")
        return redirect(url_for('orders'))

    product_id = order['product_id']
    quantity = order['quantity']
    warehouse_id = order['warehouse_id']

    # 2. Check if inventory already exists
    cursor.execute("""
        SELECT * FROM Inventory
        WHERE product_id = %s AND warehouse_id = %s
    """, (product_id, warehouse_id))
    inventory = cursor.fetchone()

    if inventory:
        new_quantity = inventory['quantity'] + quantity
        cursor.execute("""
            UPDATE Inventory
            SET quantity = %s
            WHERE inventory_id = %s
        """, (new_quantity, inventory['inventory_id']))
    else:
        new_quantity = quantity
        cursor.execute("""
            INSERT INTO Inventory (product_id, warehouse_id, quantity)
            VALUES (%s, %s, %s)
        """, (product_id, warehouse_id, quantity))

    # 3. Delete alert if quantity now exceeds threshold (e.g. 1000)
    threshold = 1000
    if new_quantity >= threshold:
        cursor.execute("""
            DELETE FROM Alerts
            WHERE product_id = %s AND warehouse_id = %s
        """, (product_id, warehouse_id))

    # 4. Delete order
    cursor.execute("DELETE FROM Orders WHERE order_id = %s", (order_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Order marked as delivered. Inventory updated and alerts checked.")
    return redirect(url_for('orders'))

# Shipments
@app.route('/shipments')
def shipments():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.shipment_id, s.order_id, s.co2_emission, s.route, w.name AS warehouse
        FROM Shipments s
        JOIN Warehouses w ON s.warehouse_id = w.warehouse_id
    """)
    shipment_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("shipments.html", shipments=shipment_data, user=session.get('user'))

# Supplier Ratings
@app.route('/supplier_ratings')
def supplier_ratings():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sr.*, s.name AS supplier_name
        FROM SupplierRatings sr
        JOIN Suppliers s ON sr.supplier_id = s.supplier_id
    """)
    ratings_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("ratings.html", ratings=ratings_data, user=session.get('user'))

# Forecast
@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    if 'user' not in session:
        return redirect(url_for('login'))
    plot_html = None
    forecast_data = []
    forecast_summary = ""
    error = None

    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
        plot_html, error, forecast_data, forecast_summary = generate_forecast_plot(from_date, to_date)

    return render_template("forecasts.html",
                           plot_url=plot_html,
                           forecasts=forecast_data,
                           forecast_summary=forecast_summary,
                           error=error,
                           user=session.get('user'))

@app.route("/ask_forecast_ai", methods=["POST"])
def ask_forecast_ai():
    data = request.get_json()
    question = data.get("question", "")
    summary = data.get("summary", "")
    try:
        full_prompt = f"{summary}\nUser question: {question}"
        answer = ask_local_ai(full_prompt)
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})
def ask_local_ai(question):
    print("Calling LLaMA model...")
    response = llama.create_chat_completion(
        messages=[{"role": "user", "content": question}]
    )
    print("LLaMA response received.")
    return response['choices'][0]['message']['content']
# Alerts
@app.route('/alerts')
def alerts():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.alert_id, a.type, a.message, a.date, 
               p.name AS product_name, 
               w.name AS warehouse_name
        FROM Alerts a
        JOIN Products p ON a.product_id = p.product_id
        JOIN Warehouses w ON a.warehouse_id = w.warehouse_id
    """)
    alerts_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("alerts.html", alerts=alerts_data, user=session.get('user'))

# Customer Orders
@app.route('/customerorders')
def customer_orders():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
                   SELECT 
                       co.customer_order_id AS order_id,
                       c.customer_name,
                       p.name AS product_name,
                       w.name AS warehouse_name,
                       co.location,
                       co.quantity,
                       co.order_date
                   FROM customerorders co
                   JOIN customers c ON co.customer_id = c.customer_id
                   JOIN products p ON co.product_id = p.product_id
                   JOIN warehouses w ON co.warehouse_id = w.warehouse_id;
    """)
    customer_orders_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("customerorders.html", orders=customer_orders_data, user=session.get('user'))

if __name__ == '__main__':
    app.run(debug=True)
