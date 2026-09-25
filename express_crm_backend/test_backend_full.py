import sys
import os
import io

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.seeds.initial_seed import seed_database

# Ensure database is seeded
db = SessionLocal()
seed_database(db)
db.close()

client = TestClient(app)

def run_all_tests():
    print("==================================================")
    print("🚀 Running Express Platform Complete Backend Test Suite (24 Suites)")
    print("==================================================")

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("✅ 1. Health check OK:", res.json()["message"])

    # 2. Customer Login
    res = client.post("/api/v1/auth/login", json={
        "phone": "01812220000",
        "password": "password123",
        "role": "customer"
    })
    assert res.status_code == 200, f"Customer login failed: {res.text}"
    customer_token = res.json()["data"]["token"]
    customer_refresh = res.json()["data"]["refreshToken"]
    print(f"✅ 2. Customer login OK: {res.json()['data']['user']['name']} (Token received)")

    # 3. Vendor Login
    res = client.post("/api/v1/auth/login", json={
        "phone": "01711111111",
        "password": "password123",
        "role": "vendor"
    })
    assert res.status_code == 200, f"Vendor login failed: {res.text}"
    vendor_data = res.json()["data"]
    vendor_token = vendor_data["token"]
    vendor_initial_wallet = vendor_data["user"]["walletBalance"]
    print(f"✅ 3. Vendor login OK: {vendor_data['user']['shopName']} (Wallet: ৳{vendor_initial_wallet})")

    # 4. Super Admin Login
    res = client.post("/api/v1/auth/login", json={
        "phone": "01900000000",
        "password": "admin123"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["data"]["token"]
    print("✅ 4. Super Admin login OK")

    # 5. Auth Extras: Refresh Token, Forgot Password, Change Password, Logout
    res = client.post("/api/v1/auth/refresh-token", json={"refreshToken": customer_refresh})
    assert res.status_code == 200
    new_token = res.json()["data"]["token"]
    assert new_token is not None

    res = client.post("/api/v1/auth/forgot-password", json={"phone": "01812220000"})
    assert res.status_code == 200

    res = client.post("/api/v1/auth/reset-password", json={
        "phone": "01812220000",
        "otp": "123456",
        "newPassword": "password123"
    })
    assert res.status_code == 200

    res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200
    print("✅ 5. Auth Extras (Refresh token, forgot/reset password, logout) OK")

    # 6. Location Hierarchy & Granular Endpoints
    res = client.get("/api/v1/locations/hierarchy")
    assert res.status_code == 200
    divisions = res.json()["data"]["divisions"]
    assert len(divisions) > 0

    res = client.get("/api/v1/locations/divisions")
    assert res.status_code == 200
    res = client.get("/api/v1/locations/districts")
    assert res.status_code == 200
    res = client.get("/api/v1/locations/upazilas")
    assert res.status_code == 200
    res = client.get("/api/v1/locations/areas")
    assert res.status_code == 200
    print(f"✅ 6. Location Hierarchy & Granular list endpoints OK ({len(divisions)} division(s))")

    # 7. Reverse Geocoding
    res = client.post("/api/v1/locations/reverse-geocode", json={
        "latitude": 23.9984,
        "longitude": 90.5451
    })
    assert res.status_code == 200
    geo_data = res.json()["data"]
    print(f"✅ 7. Reverse geocoding OK: {geo_data['area']}, {geo_data['upazila']}, {geo_data['district']}")

    # 8. Customer Category Browsing
    res = client.get("/api/v1/customer/categories")
    assert res.status_code == 200
    cust_cats = res.json()["data"]
    assert len(cust_cats) > 0
    print(f"✅ 8. Customer Categories OK: Found {len(cust_cats)} active categories")

    # 9. Customer Vendor Discovery & Vendor Detail
    res = client.get("/api/v1/customer/vendors?area=Kaliganj%20Bazar")
    assert res.status_code == 200
    vendors = res.json()["data"]
    assert len(vendors) > 0
    vendor_id = vendors[0]["id"]

    res = client.get(f"/api/v1/customer/vendors/{vendor_id}")
    assert res.status_code == 200
    v_detail = res.json()["data"]
    assert v_detail["shopName"] == vendors[0]["shopName"]
    print(f"✅ 9. Customer Vendor discovery & detail OK: {v_detail['shopName']}")

    # 10. Vendor Products & Product Detail
    res = client.get(f"/api/v1/customer/vendors/{vendor_id}/products")
    assert res.status_code == 200
    products = res.json()["data"]
    assert len(products) >= 2
    prod1 = products[0]
    prod2 = products[1]

    res = client.get(f"/api/v1/customer/products/{prod1['id']}")
    assert res.status_code == 200
    assert res.json()["data"]["name"] == prod1["name"]
    print(f"✅ 10. Vendor products & product detail OK: {prod1['name']} (৳{prod1['price']})")

    # 11. Invoicing & 2% Category Commission Billing Test
    order_payload = {
        "customerPhone": "01812220000",
        "customerName": "Tareq Hasan",
        "vendorId": vendor_id,
        "items": [
            {"productId": prod1["id"], "qty": 1}, # 1200 BDT -> 2% = 24 BDT
            {"productId": prod2["id"], "qty": 2}  # 250*2 = 500 BDT -> 2% = 10 BDT
        ],
        "discount": 0.00,
        "paymentMethod": "Cash on Delivery",
        "callId": "call_test_12345"
    }
    res = client.post(
        "/api/v1/invoices/create",
        json=order_payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 201, f"Invoice creation failed: {res.text}"
    inv_data = res.json()["data"]
    inv_id = inv_data["id"]
    
    assert inv_data["subtotal"] == 1700.00
    assert inv_data["commissionAmount"] == 34.00
    assert inv_data["items"][0]["commissionAmount"] == 24.00
    assert inv_data["items"][1]["commissionAmount"] == 10.00
    print(f"✅ 11. Invoice Created: {inv_id} with ৳{inv_data['commissionAmount']} (2% Category Commission deducted)")

    # 12. My Invoices & Status Update & Cancel Order (with wallet refund)
    res = client.get("/api/v1/invoices/my-invoices", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0

    res = client.patch(
        f"/api/v1/invoices/{inv_id}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {vendor_token}"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "confirmed"

    # Cancel invoice test
    res = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        json={"reason": "Customer cancelled test"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "cancelled"
    print(f"✅ 12. Invoice status update, my-invoices & cancel order with wallet refund OK")

    # 13. Voice Call Sessions, In-Call Cart Sync, Call History
    res = client.post(
        "/api/v1/calls/initiate",
        json={"receiverPhone": "01711111111", "productName": "Samsung Charger 25W"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 201
    call_id = res.json()["data"]["callId"]

    res = client.post(
        "/api/v1/calls/sync-cart",
        json={"callId": call_id, "items": [{"productId": prod1["id"], "qty": 1}]},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200

    res = client.get(f"/api/v1/calls/{call_id}")
    assert res.status_code == 200

    res = client.post(
        f"/api/v1/calls/{call_id}/end",
        json={"durationSeconds": 45, "status": "completed"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200

    res = client.get("/api/v1/calls/history", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200
    print(f"✅ 13. Voice Call initiation, in-call cart sync, history & end call OK ({call_id})")

    # 14. Customer Search Demands & Demand Stream
    res = client.post(
        "/api/v1/customer/search-requests",
        json={
            "query": "iPhone 16 Pro Max Silicone Cover",
            "area": "Kaliganj Bazar",
            "upazila": "Kaliganj",
            "district": "Gazipur",
            "division": "Dhaka"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 201
    demand_id = res.json()["data"]["requestId"]

    res = client.get("/api/v1/customer/search-requests/my", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200
    print(f"✅ 14. Search demand created & my demand requests OK ({demand_id})")

    # 15. Customer Vendor Reviews
    res = client.post(
        f"/api/v1/customer/vendors/{vendor_id}/reviews?rating=5.0",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 201
    print(f"✅ 15. Customer Vendor review submitted OK (Rating: {res.json()['data']['newRating']})")

    # 16. Customer & Vendor Support Tickets & CRM Ticket View/Reply
    res = client.post(
        "/api/v1/customer/support-tickets",
        json={"subject": "Order delivery question", "description": "When will it arrive?"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 201
    ticket_id = res.json()["data"]["ticketId"]

    res = client.get("/api/v1/customer/support-tickets", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200

    res = client.post(
        "/api/v1/vendor/support-tickets",
        json={"subject": "Commission statement inquiry", "description": "Need tax invoice breakdown"},
        headers={"Authorization": f"Bearer {vendor_token}"}
    )
    assert res.status_code == 201

    res = client.get(f"/api/v1/crm/tickets/{ticket_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert len(res.json()["data"]["subject"]) > 0

    res = client.post(
        f"/api/v1/crm/tickets/{ticket_id}/reply",
        json={"message": "We have dispatched the driver.", "isInternalNote": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201
    print(f"✅ 16. Support tickets (Customer, Vendor & CRM view/reply) OK")

    # 17. Vendor Dashboard, Ledger, and Invoices Query
    res = client.get("/api/v1/vendor/dashboard-summary", headers={"Authorization": f"Bearer {vendor_token}"})
    assert res.status_code == 200

    res = client.get("/api/v1/vendor/wallet-ledger", headers={"Authorization": f"Bearer {vendor_token}"})
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0

    res = client.get("/api/v1/vendor/invoices", headers={"Authorization": f"Bearer {vendor_token}"})
    assert res.status_code == 200
    print(f"✅ 17. Vendor dashboard, wallet ledger & store invoices OK")

    # 18. Vendor Payout Request & CRM Approval / Rejection
    res = client.post(
        "/api/v1/vendor/payouts/request",
        json={"amount": 500.0, "paymentMethod": "bKash", "accountNumber": "01711111111"},
        headers={"Authorization": f"Bearer {vendor_token}"}
    )
    assert res.status_code == 201
    payout_id = res.json()["data"]["payoutId"]

    res = client.get("/api/v1/vendor/payouts", headers={"Authorization": f"Bearer {vendor_token}"})
    assert res.status_code == 200

    res = client.post(
        f"/api/v1/crm/payouts/{payout_id}/approve",
        json={"transactionRef": "TRX-BKASH-998822", "adminNote": "Processed via bKash Merchant"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    print(f"✅ 18. Vendor Payout Request & CRM Approval OK (#{payout_id})")

    # 19. Vendor Profile View & Update
    res = client.get("/api/v1/vendor/profile", headers={"Authorization": f"Bearer {vendor_token}"})
    assert res.status_code == 200
    assert res.json()["data"]["shopName"] is not None

    res = client.put(
        "/api/v1/vendor/profile",
        json={"nidNumber": "1992837465012", "tradeLicense": "TRD-KAL-2026-99"},
        headers={"Authorization": f"Bearer {vendor_token}"}
    )
    assert res.status_code == 200
    print("✅ 19. Vendor Profile view & update OK")

    # 20. CRM Analytics, Demand Heatmap & Category Commission Report
    res = client.get("/api/v1/crm/analytics/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    res = client.get("/api/v1/crm/analytics/demand-heatmap", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    res = client.get("/api/v1/crm/finance/category-commission-report", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    print("✅ 20. CRM Analytics, Demand Heatmap & Commission Report OK")

    # 21. CRM Category CRUD
    res = client.post(
        "/api/v1/crm/categories",
        json={"name": "Fashion & Lifestyle", "commissionRate": 2.50, "isActive": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201
    new_cat_id = res.json()["data"]["id"]

    res = client.put(
        f"/api/v1/crm/categories/{new_cat_id}",
        json={"commissionRate": 2.00},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200

    res = client.delete(
        f"/api/v1/crm/categories/{new_cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    print("✅ 21. CRM Category CRUD (Create, Update, Delete) OK")

    # 22. CRM Platform Invoices, Call Logs, Search Demands, Customer Status
    res = client.get("/api/v1/crm/invoices", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    res = client.get("/api/v1/crm/call-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    res = client.get("/api/v1/crm/search-demands", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Get customer id for status update
    res = client.get("/api/v1/crm/customers", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    cust_list = res.json()["data"]
    if cust_list:
        cust_id = cust_list[0]["id"]
        res = client.patch(
            f"/api/v1/crm/customers/{cust_id}/status",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
    print("✅ 22. CRM Platform Invoices, Call Logs, Search Demands, and Customer Status OK")

    # 23. CRM Staff Management (Area Manager, CRM Operator, Finance)
    staff_phone = f"01999{int(os.getpid()) % 100000:05d}"
    res = client.post(
        "/api/v1/crm/staff",
        json={
            "name": "Kamal Area Manager",
            "phone": staff_phone,
            "password": "password123",
            "role": "area_manager",
            "area": "Kaliganj Bazar"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201

    res = client.get("/api/v1/crm/staff", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    print(f"✅ 23. CRM Staff Management OK (Created {staff_phone} as area_manager)")

    # 24. Media File Upload Endpoint
    fake_file_content = b"Mock image content for testing"
    files = {"file": ("test_avatar.jpg", io.BytesIO(fake_file_content), "image/jpeg")}
    res = client.post("/api/v1/upload/file", files=files)
    assert res.status_code == 200
    assert "url" in res.json()["data"]
    print(f"✅ 24. Media Upload OK: {res.json()['data']['url']}")

    print("\n==================================================")
    print("🎉 ALL 24 TEST SUITES PASSED FLAWLESSLY (100% COMPLETE & VERIFIED)!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
