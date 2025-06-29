# AI-Supply-Chain-Optimizer
PirateCart is an intelligent supply chain management system designed for internal company use. It combines traditional inventory and order management with modern AI forecasting, smart alerts, and supplier intelligence.

🔐 1. Authentication & Roles
Secure login/signup for admins and managers.
   -Role-based dashboard access (user sessions maintained via Flask session).
   -Stored in a secure users table with hashed passwords.
📦 2. Product Management
   -View all available products from the Products table.
   -Add new products directly via order forms (auto-generates SKU and assigns category).

🏢 3. Warehouse Management
   -Displays all warehouses from Warehouses table.
   -Each warehouse has a name, location, and capacity.

📊 4. Inventory Management
   -Inventory is stored in the Inventory table.
   -Real-time status check:
   -Healthy if quantity ≥ threshold (e.g., 1000 units).
   -Low Stock triggers automatic alerts and notifications.

🚨 5. Smart Alerts
   -Low inventory triggers:
   -Email alerts using Gmail SMTP.
   -SMS alerts using Twilio API.
   -Alerts are stored in the Alerts table and automatically removed when restocked.

🧾 6. Order Placement
   -Admins/Managers can place supply orders (form UI).
   -If a product is not found, it is automatically added to the product catalog.
   -Automatically logs orders in the Orders table.

🚚 7. Shipments Tracking
   -Every order, once placed, auto-generates a Shipment entry:
   -Randomly assigns a realistic route from pre-existing values.
   -Randomly calculates CO₂ emissions.
   -Stored in the Shipments table, linked to the order via order_id.

⭐ 8. Supplier Ratings
   -Admins can view ratings for suppliers from the SupplierRatings table.
   -Helps in decision-making for future orders.

🧮 9. AI-Powered Demand Forecasting
   -Historical data from CustomerOrders is used for forecasting via Facebook Prophet.
   -Graphs displayed using Plotly.
   -Automatically summarizes trends like:
   -Peak demand months
   -Low-demand months
   -Average monthly demand

💬 10. AI Assistant (LLaMA Integration)
   -Users can ask questions about forecasts.
   -LLaMA model (running locally) answers via natural language using:

