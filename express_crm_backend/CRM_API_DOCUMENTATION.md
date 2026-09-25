# 🖥️ Express Platform - Web CRM 360° API Documentation
> Complete Developer & Integration Guide for Web CRM Admin Portal (Super Admin, Area Manager, CRM Operator, and Finance Staff)

---

## 📑 Table of Contents
1. [Overview & Authentication](#1-overview--authentication)
2. [CRM Analytics & Demand Heatmap](#2-crm-analytics--demand-heatmap)
3. [Category & 2% Commission Management](#3-category--2-commission-management)
4. [Vendor 360° Management & KYC](#4-vendor-360-management--kyc)
5. [Customer 360° Management](#5-customer-360-management)
6. [Support Tickets & Dispute Resolution](#6-support-tickets--dispute-resolution)
7. [Finance, Payouts & Commission Audit](#7-finance-payouts--commission-audit)
8. [Platform Invoices & Orders Management](#8-platform-invoices--orders-management)
9. [Voice Call Logs & CTI Sessions](#9-voice-call-logs--cti-sessions)
10. [Marketplace Demand Stream](#10-marketplace-demand-stream)
11. [Master Location & Geofencing Management](#11-master-location--geofencing-management)
12. [CRM Staff Management](#12-crm-staff-management)

---

## 1. Overview & Authentication

### Base URLs
* **Local Development**: `http://localhost:8000/api/v1`
* **Production URL**: `https://your-app-name.onrender.com/api/v1`

### Standard Response Envelope
All CRM endpoints return a standardized JSON envelope:
```json
{
  "success": true,
  "statusCode": 200,
  "message": "Operation description",
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8
  },
  "errors": null
}
```

### Authentication Header
Every CRM endpoint requires a Bearer JWT Token in the request headers:
```http
Authorization: Bearer <YOUR_ACCESS_TOKEN>
```

### Pre-seeded Super Admin Login
* **Endpoint**: `POST /auth/login`
* **Request Body**:
  ```json
  {
    "phone": "01900000000",
    "password": "admin123"
  }
  ```
* **Supported CRM Staff Roles**: `super_admin`, `area_manager`, `crm_operator`, `finance`

---

## 2. CRM Analytics & Demand Heatmap

### 2.1 Get CRM Overview Analytics
Fetches high-level executive dashboard metrics: Gross Merchandise Value (GMV), 2% Commission Earnings, Vendor & Customer Counts.

* **Endpoint**: `GET /crm/analytics/overview`
* **Access**: `super_admin`, `area_manager`, `crm_operator`, `finance`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": {
      "totalGMV": 6800.00,
      "monthlyRevenue": 136.00,
      "activeVendors": 12,
      "totalCustomers": 145,
      "totalInvoices": 38,
      "activeCallSessions": 2,
      "unfulfilledSearchDemands": 9
    }
  }
  ```

---

### 2.2 Get Demand Heatmap
Returns geographic clustering of unmet customer searches for inventory planning.

* **Endpoint**: `GET /crm/analytics/demand-heatmap`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": [
      {
        "upazila": "Kaliganj",
        "area": "Kaliganj Bazar",
        "searchCount": 42,
        "topQuery": "iPhone 16 Pro Max Silicone Cover"
      }
    ]
  }
  ```

---

## 3. Category & 2% Commission Management

### 3.1 Get All Categories
* **Endpoint**: `GET /crm/categories`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": [
      {
        "id": 1,
        "name": "Electronics",
        "slug": "electronics",
        "commissionRate": 2.00,
        "iconUrl": "https://img.icons8.com/color/96/electronics.png",
        "isActive": true,
        "totalProducts": 45,
        "totalRevenueEarned": 1420.50
      }
    ]
  }
  ```

---

### 3.2 Create New Category
* **Endpoint**: `POST /crm/categories`
* **Request Body**:
  ```json
  {
    "name": "Fashion & Clothing",
    "slug": "fashion-clothing",
    "commissionRate": 2.00,
    "iconUrl": "https://img.icons8.com/color/96/clothes.png",
    "isActive": true
  }
  ```

---

### 3.3 Update Category Details
* **Endpoint**: `PUT /crm/categories/{id}`
* **Request Body**:
  ```json
  {
    "name": "Fashion & Lifestyle",
    "commissionRate": 2.25,
    "isActive": true
  }
  ```

---

### 3.4 Update Only Commission Rate
* **Endpoint**: `PATCH /crm/categories/{id}/commission`
* **Request Body**:
  ```json
  {
    "commissionRate": 2.50,
    "reason": "Quarterly rate adjustment"
  }
  ```

---

### 3.5 Delete Category
* **Endpoint**: `DELETE /crm/categories/{id}`

---

## 4. Vendor 360° Management & KYC

### 4.1 List Vendors with Search & Filtering
* **Endpoint**: `GET /crm/vendors`
* **Query Parameters**:
  * `search`: Search by shop name, owner name, or phone
  * `status`: Filter by `active`, `suspended`, `pending_approval`
  * `category`: Filter by category name
  * `page`: Page number (Default: `1`)
  * `limit`: Items per page (Default: `20`)

---

### 4.2 Vendor 360° Detailed Profile
Fetches complete store profile, KYC docs, recent orders, and wallet ledger audit trail.

* **Endpoint**: `GET /crm/vendors/{id}`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": {
      "vendor": {
        "id": 1,
        "shopName": "Rahman Electronics",
        "ownerName": "Abdur Rahman",
        "phone": "01711111111",
        "category": "Electronics",
        "address": "Shop 12, Main Road, Kaliganj Bazar",
        "walletBalance": 12398.00,
        "commissionRate": 2.00,
        "isVerified": true,
        "nidNumber": "19902617283912",
        "tradeLicense": "TRD-KAL-2026-098",
        "status": "active"
      },
      "productsCount": 18,
      "recentInvoices": [
        { "id": "INV-10001", "total": 1700.00, "commission": 34.00, "date": "2026-09-25T14:30:00" }
      ],
      "walletLedger": [
        { "id": 1, "amount": 34.00, "type": "commission_debit", "desc": "2% Category platform commission deducted for order INV-10001" }
      ]
    }
  }
  ```

---

### 4.3 Verify Vendor KYC
* **Endpoint**: `PATCH /crm/vendors/{id}/verify-kyc`
* **Request Body**:
  ```json
  {
    "isVerified": true,
    "commissionRate": 2.00,
    "adminNote": "Verified NID and trade license"
  }
  ```

---

### 4.4 Update Vendor Status (Suspend / Activate)
* **Endpoint**: `PATCH /crm/vendors/{id}/status`
* **Request Body**:
  ```json
  {
    "status": "suspended",
    "reason": "Policy violation regarding counter products"
  }
  ```

---

## 5. Customer 360° Management

### 5.1 List Customers with Lifetime Value (LTV)
* **Endpoint**: `GET /crm/customers?page=1&limit=20&search=Tareq`

---

### 5.2 Customer 360° Profile
* **Endpoint**: `GET /crm/customers/{id}`
* **Returns**: Customer details, total orders count, lifetime spend (LTV), past unfulfilled search requests, and support tickets history.

---

### 5.3 Update Customer Account Status
* **Endpoint**: `PATCH /crm/customers/{id}/status`
* **Request Body**:
  ```json
  {
    "status": "suspended",
    "reason": "Suspicious fraudulent activity"
  }
  ```

---

## 6. Support Tickets & Dispute Resolution

### 6.1 List Support Tickets
* **Endpoint**: `GET /crm/tickets?status=open&priority=high`

---

### 6.2 View Ticket Details with Full Reply History
* **Endpoint**: `GET /crm/tickets/{id}`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": {
      "id": 1,
      "ticketNumber": "TCK-1001",
      "creator": {
        "id": 3,
        "name": "Tareq Hasan",
        "phone": "01812220000",
        "role": "customer"
      },
      "subject": "Charger fast charging not working",
      "description": "The item received is 15W instead of 25W.",
      "category": "Order Dispute",
      "status": "in_progress",
      "priority": "high",
      "replies": [
        {
          "id": 1,
          "senderName": "Tareq Hasan",
          "senderRole": "customer",
          "isInternalNote": false,
          "message": "Please replace this.",
          "createdAt": "2026-09-25T15:00:00"
        },
        {
          "id": 2,
          "senderName": "Express Super Admin",
          "senderRole": "super_admin",
          "isInternalNote": false,
          "message": "Merchant in Kaliganj Bazar has been instructed to replace the item.",
          "createdAt": "2026-09-25T15:30:00"
        }
      ]
    }
  }
  ```

---

### 6.3 Reply to Ticket or Add Internal Staff Note
* **Endpoint**: `POST /crm/tickets/{id}/reply`
* **Request Body**:
  ```json
  {
    "message": "Customer contacted via phone and replacement scheduled for tomorrow.",
    "isInternalNote": false
  }
  ```

---

### 6.4 Update Ticket Status
* **Endpoint**: `PATCH /crm/tickets/{id}/status`
* **Request Body**:
  ```json
  {
    "status": "resolved",
    "resolutionSummary": "Replacement delivered successfully"
  }
  ```

---

## 7. Finance, Payouts & Commission Audit

### 7.1 Category-Based 2% Commission Report
* **Endpoint**: `GET /crm/finance/category-commission-report`
* **Sample Response**:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "data": {
      "totalCommissionEarned": 136.00,
      "currency": "BDT",
      "categoryBreakdown": [
        {
          "category": "Electronics",
          "commissionRate": "2.0%",
          "totalOrders": 8,
          "gmv": 6800.00,
          "commissionEarned": 136.00
        }
      ]
    }
  }
  ```

---

### 7.2 List Vendor Payout Requests
* **Endpoint**: `GET /crm/payouts`

---

### 7.3 Approve Payout Request
* **Endpoint**: `POST /crm/payouts/{id}/approve`
* **Request Body**:
  ```json
  {
    "transactionRef": "TRX-BKASH-9082341",
    "adminNote": "Disbursed via bKash Merchant Portal"
  }
  ```

---

### 7.4 Reject Payout Request & Restore Vendor Wallet Balance
* **Endpoint**: `POST /crm/payouts/{id}/reject`
* **Request Body**:
  ```json
  {
    "adminNote": "Invalid bKash account number provided. Please update account."
  }
  ```
> **Note**: Rejecting automatically restores the requested amount to the vendor's wallet balance and creates an audit ledger entry.

---

## 8. Platform Invoices & Orders Management

### 8.1 List Platform Invoices
* **Endpoint**: `GET /crm/invoices?status=completed&page=1&limit=20&search=Tareq`

---

### 8.2 Invoice Details & PDF View
* **API Details**: `GET /invoices/{id}`
* **Printable Invoice**: `GET /invoices/{id}/pdf`

---

## 9. Voice Call Logs & CTI Sessions

### 9.1 List Call Logs
* **Endpoint**: `GET /crm/call-logs?status=completed&page=1&limit=20`
* **Returns**: Caller details, receiver shop details, product name, duration in seconds, invoice ID if converted to order.

---

## 10. Marketplace Demand Stream

### 10.1 List Unfulfilled Search Demands
* **Endpoint**: `GET /crm/search-demands?area=Kaliganj%20Bazar&status=unfulfilled`

---

## 11. Master Location & Geofencing Management

### 11.1 Create Location Nodes
* **Division**: `POST /crm/locations/division` -> `{"name": "Dhaka"}`
* **District**: `POST /crm/locations/district` -> `{"divisionId": 1, "name": "Gazipur"}`
* **Upazila**: `POST /crm/locations/upazila` -> `{"districtId": 1, "name": "Kaliganj"}`
* **Area / Union**: `POST /crm/locations/area` -> `{"upazilaId": 1, "name": "Kaliganj Bazar", "latitude": 23.9984, "longitude": 90.5451}`

---

### 11.2 Delete Location Nodes
* `DELETE /crm/locations/division/{id}`
* `DELETE /crm/locations/district/{id}`
* `DELETE /crm/locations/upazila/{id}`
* `DELETE /crm/locations/area/{id}`

---

## 12. CRM Staff Management

### 12.1 List All CRM Staff
* **Endpoint**: `GET /crm/staff`
* **Access**: `super_admin` only

---

### 12.2 Create CRM Staff Account
* **Endpoint**: `POST /crm/staff`
* **Access**: `super_admin` only
* **Request Body**:
  ```json
  {
    "name": "Kamal Area Manager",
    "phone": "01912000001",
    "password": "password123",
    "email": "kamal@express.com",
    "role": "area_manager",
    "division": "Dhaka",
    "district": "Gazipur",
    "upazila": "Kaliganj",
    "area": "Kaliganj Bazar"
  }
  ```
* **Allowed Staff Roles**: `area_manager`, `crm_operator`, `finance`, `super_admin`

---

## 🚀 Interactive Swagger Documentation
Open in browser:
👉 **`http://localhost:8000/docs`** (or `https://your-app.onrender.com/docs`)
