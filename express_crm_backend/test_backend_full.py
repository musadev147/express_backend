import sys
import os

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
    print("🚀 Running Express Platform Full Backend Test Suite")
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

    # 5. Location Hierarchy
    res = client.get("/api/v1/locations/hierarchy")
    assert res.status_code == 200
    divisions = res.json()["data"]["divisions"]
    assert len(divisions) > 0
    print(f"✅ 5. Location hierarchy OK: Found {len(divisions)} division(s), including '{divisions[0]['name']}'")

    # 6. Reverse Geocoding
    res = client.post("/api/v1/locations/reverse-geocode", json={
        "latitude": 23.9984,
        "longitude": 90.5451
    })
    assert res.status_code == 200
    geo_data = res.json()["data"]
    print(f"✅ 6. Reverse geocoding OK: {geo_data['area']}, {geo_data['upazila']}, {geo_data['district']}")

    # 7. Customer Vendor Discovery
    res = client.get("/api/v1/customer/vendors?area=Kaliganj%20Bazar")
    assert res.status_code == 200
    vendors = res.json()["data"]
    assert len(vendors) > 0
    vendor_id = vendors[0]["id"]
    print(f"✅ 7. Customer Vendor discovery OK: Found {len(vendors)} vendor(s) in Kaliganj Bazar ({vendors[0]['shopName']})")

    # 8. Vendor Products
    res = client.get(f"/api/v1/customer/vendors/{vendor_id}/products")
    assert res.status_code == 200
    products = res.json()["data"]
    assert len(products) >= 2
    prod1 = products[0]
    prod2 = products[1]
    print(f"✅ 8. Vendor products OK: {prod1['name']} (৳{prod1['price']}) & {prod2['name']} (৳{prod2['price']})")

    # 9. Invoicing & 2% Category Commission Billing Test
    print("\n--- ⚡ Testing 2% Category Commission Billing ---")
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
    
    expected_subtotal = 1700.00
    expected_commission = 34.00 # 2% of 1700 BDT
    assert inv_data["subtotal"] == expected_subtotal, f"Expected {expected_subtotal}, got {inv_data['subtotal']}"
    assert inv_data["commissionAmount"] == expected_commission, f"Expected {expected_commission}, got {inv_data['commissionAmount']}"
    
    # Check itemized breakdown
    item1_comm = inv_data["items"][0]["commissionAmount"]
    item2_comm = inv_data["items"][1]["commissionAmount"]
    assert item1_comm == 24.00
    assert item2_comm == 10.00
    
    print(f"✅ 9. Invoice Created: {inv_data['id']}")
    print(f"   - Subtotal: ৳{inv_data['subtotal']}")
    print(f"   - 2% Category Commission: ৳{inv_data['commissionAmount']} (Item 1: ৳{item1_comm}, Item 2: ৳{item2_comm})")
    print(f"   - Total Payable: ৳{inv_data['total']}")
    print(f"   - Vendor Wallet Deduction: -৳{inv_data['vendorWalletDeduction']}")
    print(f"   - Vendor Updated Wallet Balance: ৳{inv_data['vendorUpdatedWalletBalance']}")

    # 10. Customer Search Request (Demand Stream)
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
    print(f"✅ 10. Search demand logged: {res.json()['data']['requestId']} (Notified {res.json()['data']['vendorsNotifiedCount']} local vendors)")

    # 11. Vendor Dashboard Summary
    res = client.get(
        "/api/v1/vendor/dashboard-summary",
        headers={"Authorization": f"Bearer {vendor_token}"}
    )
    assert res.status_code == 200
    dash_data = res.json()["data"]
    print(f"✅ 11. Vendor Dashboard Summary OK: Today Sales: ৳{dash_data['todaySales']}, Invoices: {dash_data['totalInvoices']}, Wallet: ৳{dash_data['walletBalance']}")

    # 12. CRM Analytics Overview
    res = client.get(
        "/api/v1/crm/analytics/overview",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    crm_analytics = res.json()["data"]
    print(f"✅ 12. CRM Analytics Overview OK: Total GMV: ৳{crm_analytics['totalGMV']}, Total 2% Commission Revenue: ৳{crm_analytics['monthlyRevenue']}")

    # 13. CRM Category Commission Report
    res = client.get(
        "/api/v1/crm/finance/category-commission-report",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    report = res.json()["data"]
    print(f"✅ 13. CRM Category Commission Report OK: Total Commission Earned: ৳{report['totalCommissionEarned']}")
    for cat_rep in report["categoryBreakdown"]:
        if cat_rep["gmv"] > 0:
            print(f"   - {cat_rep['category']} ({cat_rep['commissionRate']}): Orders: {cat_rep['totalOrders']}, GMV: ৳{cat_rep['gmv']}, Earned: ৳{cat_rep['commissionEarned']}")

    # 14. CRM Support Tickets & Reply
    res = client.get(
        "/api/v1/crm/tickets",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    tickets = res.json()["data"]
    if tickets:
        ticket_id = tickets[0]["id"]
        reply_res = client.post(
            f"/api/v1/crm/tickets/{ticket_id}/reply",
            json={"message": "Merchant in Kaliganj Bazar has been instructed to replace the item.", "isInternalNote": False},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reply_res.status_code == 201
        print(f"✅ 14. Support Ticket Reply OK on {tickets[0]['ticketNumber']}")

    print("\n==================================================")
    print("🎉 ALL 14 TEST SUITES PASSED FLAWLESSLY!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
