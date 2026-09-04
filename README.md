# Express Platform - Unified Backend API & WebSocket Server
## High-performance RESTful API and Real-Time WebSocket Server for Flutter Mobile Apps (Customer & Vendor) and Web CRM Portal

---

## 🚀 Key Features

- **JWT Authentication & RBAC**: Supports Customers, Vendors, and Super Admins / Staff with bcrypt password hashing and Bearer tokens.
- **Category-Based 2% Commission Billing Engine**: Dynamic category commission calculation with automatic vendor wallet deductions and ledger audits.
- **Location & Geofencing System**: Division ➔ District ➔ Upazila ➔ Area hierarchical tree and GPS reverse-geocoding (Haversine distance).
- **Marketplace & Demand Intelligence**: Customer vendor discovery, catalog search, and unfulfilled demand stream alerts.
- **Real-Time Voice Call & In-Call Order Session (CTI)**: Live cart synchronization (`call:cart_sync`) and call signaling via WebSockets (`/ws`).
- **Web CRM 360° Management**: Analytics KPIs, Demand Heatmaps, Vendor 360, Customer 360, Support Tickets, and Payout Approvals.

---

## 🛠 Tech Stack

- **Framework**: FastAPI (Python 3.9+)
- **Database ORM**: SQLAlchemy (Compatible with SQLite and PostgreSQL)
- **Validation**: Pydantic v2
- **Authentication**: PyJWT + Bcrypt
- **Real-Time**: WebSockets (FastAPI / Starlette)
- **ASGI Server**: Uvicorn

---

## ⚙️ Quick Start Guide

### 1. Clone the repository
```bash
git clone https://github.com/musadev147/express_backend.git
cd express_backend/express_crm_backend
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the server
```bash
python run.py
```

The server will be available at:
- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **WebSocket Gateway**: `ws://localhost:8000/ws`

---

## 🔑 Pre-seeded Demo Credentials

| Role | Phone | Password | Details |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `01900000000` | `admin123` | Full CRM Admin Access |
| **Merchant / Vendor** | `01711111111` | `password123` | Rahman Electronics (Kaliganj Bazar, 2% Category) |
| **Customer** | `01812220000` | `password123` | Tareq Hasan (Kaliganj Bazar) |

---

## 🧪 Running Automated Tests

```bash
cd express_crm_backend
source venv/bin/activate
python test_backend_full.py
```
