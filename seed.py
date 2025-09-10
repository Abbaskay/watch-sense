from datetime import date

from app import create_app
from models import db, Customer


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Example customer: Abbas, purchased Tissot 2023-01-01
        existing = Customer.query.filter_by(name="Abbas").first()
        if not existing:
            customer = Customer(
                name="Abbas",
                dob=date(1995, 5, 15),
                purchase_date=date(2023, 1, 1),
                model="Tissot",
                mobile="9999999999",
                email="example@example.com",
            )
            db.session.add(customer)
            db.session.commit()
            print("Seeded sample customer: Abbas")
        else:
            print("Sample customer already exists.")
