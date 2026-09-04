# SwiftTrack System Testing & Execution Guide

This document contains all the necessary instructions to set up the environment and test the SwiftTrack platform. We provide instructions for testing via the **built-in Web UI** (easiest for visual demonstration) and via **API / Postman**.

---

## 🛠️ Prerequisites

* **Docker** and **Docker Compose** installed on your machine.
* A modern **Web Browser** (e.g., Chrome, Firefox, Safari) to access the UI.
* *(Optional)* A REST client (e.g., Postman, Insomnia) if you prefer to make raw API requests.

*Note: The entire ecosystem is fully containerized. You do not need to install Python, PostgreSQL, RabbitMQ, or any local dependencies to run the platform.*

---

## 🚀 Building & Running the System

To spin up the entire ecosystem (RabbitMQ, PostgreSQL databases, Auth Service, Order Service, Web UI, Mock Systems, and all Adapters):

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/swifttrack.git
cd swifttrack

# 2. Build and start the containers in detached mode
docker compose up -d --build
```
*Wait 15-20 seconds for the health checks to pass and RabbitMQ to fully initialize before testing.*

---

## 📸 Step-by-Step Testing via Web UI (Recommended)

The easiest way to see the asynchronous architecture in action is through the bundled frontend web portal, which natively handles JWTs and WebSockets for you.

### Scenario 1: The Happy Path (Client & Driver Workflow)
*Demonstrates event-driven choreography, WebSocket notifications, and role-based actions.*

**1. Create a Client Account:**
* Open your Web Browser and navigate to: **`http://localhost:3000`**
* Click "Register here". Select the **Client** role. Create an account (e.g., `user: client1`).
* Log in. You will see the Client Dashboard and the WebSocket indicator turning green ("Connected — live updates active").

**2. Submit an Order:**
* Go to the **+ New Order** tab.
* Enter a destination address and package description, then click Submit.
* **Watch the Notifications Tab:** You will instantly see WebSocket events stream in as the order hits the PostgreSQL DB, goes through the CMS (SOAP adapter), WMS (TCP adapter), and Route Optimization (REST adapter).

**3. Complete the Delivery as a Driver:**
* Open a *new Incognito/Private window* (or a different browser) and go to **`http://localhost:3000`**.
* Register a new account, but this time select the **Driver** role (e.g., `user: driver1`).
* Log in as the driver. You will see the Driver Dashboard.
* Paste the Order ID from your Client window into the "Order Lookup" box and click Fetch.
* Click **Deliver**, upload a dummy proof-of-delivery image/signature, and confirm.
* *(Switch back to your Client window to see the "Order Delivered" WebSocket notification pop up instantly!)*

---

### Scenario 2: Distributed Saga Rollback (Failure Path)
*Demonstrates robust distributed failure handling using the Saga pattern.*

By design, our `cms-mock` will **reject** any order if the `order_id` ends with `999`.

**Step 1: Inspect the Logs**
Open a terminal and tail the logs of the relevant services:
```bash
docker compose logs -f cms-adapter wms-adapter order-service
```

**Step 2: Force a System Failure**
Temporarily change the code in `cms-mock/app/main.py` so it fails *every* order:
```python
# Change this in cms-mock/app/main.py temporarily
success = "false"
reason = "CMS rejected order (Simulated Failure)"
```
Restart the `cms-mock` container:
```bash
docker compose restart cms-mock
```

**Step 3: Watch the Rollback via UI & Logs**
* Go back to your Client Web UI (`http://localhost:3000`) and submit a new order.
* **Observe the UI:** The WebSocket will show the order being created, but then instantly show an `order.failed` and `order.compensate` event.
* **Observe the Logs:** You will see the `cms-adapter` failing the order, followed immediately by the `wms-adapter` receiving an `order.compensate` event and safely rolling back the warehouse allocation.

---

## 💻 Alternative: Raw API Testing (Postman)

If you prefer to inspect the raw JSON requests without the UI:

1. **Register User:** Make a `POST` request to `http://localhost:8000/auth/register`
   ```json
   { "username": "johndoe", "email": "john@example.com", "password": "securepassword123", "role": "CLIENT" }
   ```
2. **Login:** Make a `POST` request to `http://localhost:8000/auth/login` to get your JWT `access_token`.
3. **Connect WebSocket:** In Postman, open a WebSocket connection to `ws://localhost:8003/ws/notifications`.
4. **Create Order:** Make a `POST` request to `http://localhost:8001/api/v1/orders`.
   * **Headers:** `Authorization: Bearer <your_access_token>`
   * **Body:** `{"description": "Gaming Laptop", "destination": "Silicon Valley"}`

---

### 🐰 Bonus: Visualizing the Message Broker
1. Open a Web Browser and go to `http://localhost:15672`.
2. Login with credentials: `swift` / `swift`.
3. Navigate to the **Exchanges** tab, click on `swifttrack.events`, and open the **Bindings** section.
*Here you can visually inspect how events are intelligently routed to their respective queues, showcasing the core of the Event-Driven Architecture.*
