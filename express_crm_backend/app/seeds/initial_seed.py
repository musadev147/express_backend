from sqlalchemy.orm import Session
from app.models.user import User, UserRole, UserStatus
from app.models.location import Division, District, Upazila, Area
from app.models.category import Category
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.invoice import Invoice, InvoiceItem
from app.models.search_request import SearchRequest
from app.models.support_ticket import SupportTicket
from app.models.payout import VendorWalletLedger
from app.services.auth_service import AuthService

def seed_database(db: Session):
    # Check if already seeded
    if db.query(Category).count() > 0:
        return

    print("🌱 Seeding Express Platform Database...")

    # 1. Locations (Dhaka -> Gazipur -> Kaliganj & Sreepur)
    dhaka_div = Division(name="Dhaka")
    db.add(dhaka_div)
    db.commit()
    db.refresh(dhaka_div)

    gazipur_dist = District(division_id=dhaka_div.id, name="Gazipur")
    db.add(gazipur_dist)
    db.commit()
    db.refresh(gazipur_dist)

    kaliganj_upazila = Upazila(district_id=gazipur_dist.id, name="Kaliganj")
    sreepur_upazila = Upazila(district_id=gazipur_dist.id, name="Sreepur")
    db.add_all([kaliganj_upazila, sreepur_upazila])
    db.commit()
    db.refresh(kaliganj_upazila)
    db.refresh(sreepur_upazila)

    area1 = Area(upazila_id=kaliganj_upazila.id, name="Kaliganj Bazar", latitude=23.9984, longitude=90.5451)
    area2 = Area(upazila_id=kaliganj_upazila.id, name="Tumulia", latitude=23.9850, longitude=90.5320)
    area3 = Area(upazila_id=kaliganj_upazila.id, name="Nagari", latitude=23.9720, longitude=90.5110)
    area4 = Area(upazila_id=sreepur_upazila.id, name="Maona Bazar", latitude=24.1820, longitude=90.4120)
    db.add_all([area1, area2, area3, area4])
    db.commit()
    db.refresh(area1)

    # 2. Categories with 2% Commission
    categories_data = [
        {"name": "Electronics", "slug": "electronics", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/electronics.png"},
        {"name": "Grocery", "slug": "grocery", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/shopping-bag.png"},
        {"name": "Medicine", "slug": "medicine", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/pill.png"},
        {"name": "Clothing & Fashion", "slug": "clothing-fashion", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/t-shirt.png"},
        {"name": "Hardware & Sanitary", "slug": "hardware-sanitary", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/hammer.png"},
        {"name": "Cosmetics & Beauty", "slug": "cosmetics-beauty", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/cosmetics.png"},
        {"name": "Others", "slug": "others", "commission_rate": 2.00, "icon_url": "https://img.icons8.com/color/96/box.png"},
    ]
    created_categories = {}
    for cat_data in categories_data:
        cat = Category(**cat_data)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        created_categories[cat.name] = cat

    # 3. Super Admin
    admin_user = User(
        name="Express Super Admin",
        phone="01900000000",
        email="admin@express.com",
        password_hash=AuthService.hash_password("admin123"),
        role=UserRole.SUPER_ADMIN.value,
        status=UserStatus.ACTIVE.value,
        division_name="Dhaka",
        district_name="Gazipur",
        upazila_name="Kaliganj",
        area_name="Kaliganj Bazar"
    )
    db.add(admin_user)

    # 4. Demo Customer (Tareq Hasan)
    customer_user = User(
        name="Tareq Hasan",
        phone="01812220000",
        email="tareq@mail.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.CUSTOMER.value,
        status=UserStatus.ACTIVE.value,
        division_name="Dhaka",
        district_name="Gazipur",
        upazila_name="Kaliganj",
        area_name="Kaliganj Bazar"
    )
    db.add(customer_user)

    # 5. Demo Vendor (Rahman Electronics)
    vendor_user = User(
        name="Abdur Rahman",
        phone="01711111111",
        email="rahman@mail.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.VENDOR.value,
        status=UserStatus.ACTIVE.value,
        division_name="Dhaka",
        district_name="Gazipur",
        upazila_name="Kaliganj",
        area_name="Kaliganj Bazar"
    )
    db.add(vendor_user)
    db.commit()
    db.refresh(vendor_user)

    vendor_profile = Vendor(
        user_id=vendor_user.id,
        shop_name="Rahman Electronics",
        category="Electronics",
        category_id=created_categories["Electronics"].id,
        address="Shop #4, Kaliganj Main Road, Kaliganj Bazar",
        division_name="Dhaka",
        district_name="Gazipur",
        upazila_name="Kaliganj",
        area_name="Kaliganj Bazar",
        area_id=area1.id,
        commission_rate=2.00, # 2% category commission
        is_verified=True,
        wallet_balance=12500.00,
        rating=4.9
    )
    db.add(vendor_profile)
    db.commit()
    db.refresh(vendor_profile)

    # 6. Demo Products for Rahman Electronics
    p1 = Product(
        vendor_id=vendor_profile.id,
        category_id=created_categories["Electronics"].id,
        name="Samsung Charger 25W Fast Adapter",
        category="Electronics",
        description="Original Samsung Type-C 25W Super Fast Charging Adapter",
        price=1200.00,
        stock=25,
        unit="pcs",
        is_available=True,
        tags="samsung,charger,fast charging,adapter,25w",
        image_url="https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=500"
    )
    p2 = Product(
        vendor_id=vendor_profile.id,
        category_id=created_categories["Electronics"].id,
        name="USB Type-C Fast Data Cable 65W",
        category="Electronics",
        description="Nylon Braided 65W High Speed Data Cable",
        price=250.00,
        stock=50,
        unit="pcs",
        is_available=True,
        tags="type-c,cable,usb,fast data",
        image_url="https://images.unsplash.com/photo-1616401784845-180882ba9ba8?w=500"
    )
    p3 = Product(
        vendor_id=vendor_profile.id,
        category_id=created_categories["Electronics"].id,
        name="Wireless Bluetooth Earbuds TWS",
        category="Electronics",
        description="Noise Cancelling TWS Bluetooth 5.3 Earphones",
        price=1450.00,
        stock=15,
        unit="pcs",
        is_available=True,
        tags="earbuds,tws,bluetooth,sound,audio",
        image_url="https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=500"
    )
    db.add_all([p1, p2, p3])
    db.commit()

    # 7. Sample Initial Invoice (Total: 1700 BDT, 2% Commission: 34 BDT)
    inv = Invoice(
        id="INV-10001",
        customer_id=customer_user.id,
        customer_name="Tareq Hasan",
        customer_phone="01812220000",
        vendor_id=vendor_profile.id,
        vendor_shop_name="Rahman Electronics",
        vendor_phone="01711111111",
        vendor_area="Kaliganj Bazar",
        subtotal=1700.00,
        discount=0.00,
        commission_amount=34.00, # 2% Commission on 1700 BDT
        total=1700.00,
        status="completed",
        payment_method="Cash on Delivery"
    )
    db.add(inv)
    db.commit()

    item1 = InvoiceItem(
        invoice_id=inv.id,
        product_id=p1.id,
        product_name=p1.name,
        category_id=created_categories["Electronics"].id,
        category_name="Electronics",
        commission_rate=2.00,
        commission_amount=24.00, # 2% of 1200
        price=1200.00,
        quantity=1,
        line_total=1200.00
    )
    item2 = InvoiceItem(
        invoice_id=inv.id,
        product_id=p2.id,
        product_name=p2.name,
        category_id=created_categories["Electronics"].id,
        category_name="Electronics",
        commission_rate=2.00,
        commission_amount=10.00, # 2% of 500
        price=250.00,
        quantity=2,
        line_total=500.00
    )
    db.add_all([item1, item2])

    # Initial ledger entry
    ledger = VendorWalletLedger(
        vendor_id=vendor_profile.id,
        invoice_id=inv.id,
        transaction_type="commission_debit",
        amount=34.00,
        balance_before=12534.00,
        balance_after=12500.00,
        description="2% Category platform commission deducted for order INV-10001"
    )
    db.add(ledger)

    # 8. Sample Search Demand
    demand = SearchRequest(
        id="req_1725458000123",
        query_text="iPhone 15 Pro Max Clear Case",
        customer_id=customer_user.id,
        customer_phone="01812220000",
        division_name="Dhaka",
        district_name="Gazipur",
        upazila_name="Kaliganj",
        area_name="Kaliganj Bazar",
        status="unfulfilled"
    )
    db.add(demand)

    # 9. Sample Support Ticket
    ticket = SupportTicket(
        ticket_number="TCK-1001",
        creator_id=customer_user.id,
        subject="Exchange request for damaged charger pin",
        description="Received charger with loose type-c pin in Kaliganj Bazar, requested replacement.",
        category="Returns & Exchange",
        status="open",
        priority="medium"
    )
    db.add(ticket)

    db.commit()
    print("✅ Database seeding complete with 2% Category Commissions, Admin, Vendor, Products, and Locations!")
