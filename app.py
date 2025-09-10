import os
from datetime import date, datetime
from typing import List, Tuple

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import and_, or_
from dotenv import load_dotenv

from models import db, Customer, MessageLog, Event, Tenant, User, Watch, Template
from config import Config
import pandas as pd


# Load environment variables from a .env file if present
load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    mail = Mail(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        # Ensure a default tenant exists for demo
        default_tenant = Tenant.query.filter_by(name="Default Watch Shop").first()
        if not default_tenant:
            default_tenant = Tenant(name="Default Watch Shop", email="owner@example.com", mobile="9999999999")
            db.session.add(default_tenant)
            db.session.commit()
        
        # Create default admin user if not exists
        admin_user = User.query.filter_by(email="admin@example.com").first()
        if not admin_user:
            admin_user = User(
                tenant_id=default_tenant.tenant_id,
                email="admin@example.com",
                role="owner"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

    def add_months(start_date: date, months: int) -> date:
        if start_date is None:
            return None
        month = start_date.month - 1 + months
        year = start_date.year + month // 12
        month = month % 12 + 1
        day = min(start_date.day, [31,
                                   29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                   31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return date(year, month, day)

    def rules_description() -> List[Tuple[str, str]]:
        return [
            ("battery_replacement", "Battery replacement reminder (18 months after purchase)"),
            ("birthday_wishes", "Birthday wishes"),
            ("extended_warranty", "Extended warranty upsell"),
            ("bundling_offers", "Bundling offers"),
        ]

    @app.route("/")
    def index():
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid email or password.", "error")
        
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        # Get search query
        search = request.args.get('search', '')
        customers_query = Customer.query
        
        if search:
            customers_query = customers_query.filter(
                or_(
                    Customer.name.contains(search),
                    Customer.email.contains(search),
                    Customer.mobile.contains(search)
                )
            )
        
        customers = customers_query.order_by(Customer.id.desc()).all()
        
        # Get statistics
        total_customers = Customer.query.count()
        total_watches = Watch.query.count()
        total_events = Event.query.count()
        recent_events = Event.query.order_by(Event.sent_at.desc()).limit(5).all()
        
        return render_template("dashboard.html", 
                             customers=customers, 
                             search=search,
                             total_customers=total_customers,
                             total_watches=total_watches,
                             total_events=total_events,
                             recent_events=recent_events)

    @app.route("/add_customer", methods=["GET", "POST"])
    @login_required
    def add_customer():
        if request.method == "POST":
            name = request.form.get("name")
            dob_str = request.form.get("dob")
            purchase_date_str = request.form.get("purchase_date")
            
            model = request.form.get("model")
            mobile = request.form.get("mobile")
            email = request.form.get("email")

            dob = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
            purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date() if purchase_date_str else None

            customer = Customer(
                name=name,
                dob=dob,
                purchase_date=purchase_date,
                model=model,
                mobile=mobile,
                email=email,
            )
            db.session.add(customer)
            db.session.commit()
            flash("Customer added successfully.", "success")
            return redirect(url_for("dashboard"))

        return render_template("add_customer.html")

    @app.route("/watches")
    @login_required
    def watches():
        watches = Watch.query.join(Customer).order_by(Watch.watch_id.desc()).all()
        return render_template("watches.html", watches=watches)

    @app.route("/add_watch", methods=["GET", "POST"])
    @login_required
    def add_watch():
        if request.method == "POST":
            customer_id = request.form.get("customer_id")
            brand = request.form.get("brand")
            model_no = request.form.get("model_no")
            serial_no = request.form.get("serial_no")
            purchase_date_str = request.form.get("purchase_date")
            notes = request.form.get("notes")

            purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date() if purchase_date_str else None

            watch = Watch(
                tenant_id=current_user.tenant_id,
                customer_id=customer_id,
                brand=brand,
                model_no=model_no,
                serial_no=serial_no,
                purchase_date=purchase_date,
                notes=notes
            )
            db.session.add(watch)
            db.session.commit()
            flash("Watch added successfully.", "success")
            return redirect(url_for("watches"))

        customers = Customer.query.all()
        customer_id = request.args.get('customer_id')
        return render_template("add_watch.html", customers=customers, selected_customer_id=customer_id)

    @app.route("/templates")
    @login_required
    def templates():
        templates = Template.query.filter_by(tenant_id=current_user.tenant_id).all()
        return render_template("templates.html", templates=templates)

    @app.route("/add_template", methods=["GET", "POST"])
    @login_required
    def add_template():
        if request.method == "POST":
            name = request.form.get("name")
            content = request.form.get("content")

            template = Template(
                tenant_id=current_user.tenant_id,
                name=name,
                content=content
            )
            db.session.add(template)
            db.session.commit()
            flash("Template added successfully.", "success")
            return redirect(url_for("templates"))

        return render_template("add_template.html")

    @app.route("/edit_template/<int:template_id>", methods=["GET", "POST"])
    @login_required
    def edit_template(template_id):
        template = Template.query.filter_by(template_id=template_id, tenant_id=current_user.tenant_id).first_or_404()
        
        if request.method == "POST":
            template.name = request.form.get("name")
            template.content = request.form.get("content")
            db.session.commit()
            flash("Template updated successfully.", "success")
            return redirect(url_for("templates"))

        return render_template("edit_template.html", template=template)

    @app.route("/events", methods=["GET", "POST"])
    @login_required
    def events():
        if request.method == "POST":
            sent_messages = 0
            now_date = date.today()
            customers = Customer.query.all()

            # Use default tenant for demo purposes
            tenant = Tenant.query.filter_by(name="Default Watch Shop").first()

            for customer in customers:
                # Rule: Battery replacement reminder
                if customer.purchase_date:
                    due_date = add_months(customer.purchase_date, 18)
                    if due_date and now_date >= due_date:
                        text = f"Hi {customer.name}, it's been 18 months since your {customer.model} purchase. Time for a battery check!"
                        db.session.add(MessageLog(
                            customer_id=customer.id,
                            event_type="battery_replacement",
                            message=text,
                            status="sent",
                        ))
                        db.session.add(Event(
                            tenant_id=tenant.tenant_id if tenant else None,
                            customer_id=customer.id,
                            event_type="battery_replacement",
                            channel="whatsapp",
                            sent_at=datetime.utcnow(),
                            status="sent",
                        ))
                        sent_messages += 1
                        flash(f"Message sent to {customer.name} via WhatsApp (mock).", "success")

                # Rule: Birthday wishes
                if customer.dob:
                    if customer.dob.month == now_date.month and customer.dob.day == now_date.day:
                        text = f"Happy Birthday, {customer.name}! Wishing you a wonderful year ahead. – Your Watch Retailer"
                        email_status = "sent"
                        if customer.email and app.config.get("MAIL_USERNAME"):
                            try:
                                msg = Message("Happy Birthday!", recipients=[customer.email])
                                msg.body = text
                                Mail(app).send(msg)
                                email_status = "email_sent"
                            except Exception:
                                email_status = "email_failed"
                        db.session.add(MessageLog(
                            customer_id=customer.id,
                            event_type="birthday_wishes",
                            message=text,
                            status=email_status,
                        ))
                        db.session.add(Event(
                            tenant_id=tenant.tenant_id if tenant else None,
                            customer_id=customer.id,
                            event_type="birthday_wishes",
                            channel="email" if email_status == "email_sent" else "whatsapp",
                            sent_at=datetime.utcnow(),
                            status="sent" if email_status != "email_failed" else "failed",
                        ))
                        sent_messages += 1
                        flash(f"Birthday message sent to {customer.name} via {'Email' if email_status=='email_sent' else 'mock' }.", "success")

                # Rule: Extended warranty upsell (e.g., 11 months after purchase)
                if customer.purchase_date:
                    warranty_offer_date = add_months(customer.purchase_date, 11)
                    if warranty_offer_date and now_date >= warranty_offer_date:
                        text = f"Hi {customer.name}, extend your warranty for {customer.model} before it expires!"
                        db.session.add(MessageLog(
                            customer_id=customer.id,
                            event_type="extended_warranty",
                            message=text,
                            status="sent",
                        ))
                        db.session.add(Event(
                            tenant_id=tenant.tenant_id if tenant else None,
                            customer_id=customer.id,
                            event_type="extended_warranty",
                            channel="whatsapp",
                            sent_at=datetime.utcnow(),
                            status="sent",
                        ))
                        sent_messages += 1

                # Rule: Bundling offers (always available as periodic promotion)
                text = f"Exclusive offer for you, {customer.name}: Save on straps and accessories when you visit us this week!"
                db.session.add(MessageLog(
                    customer_id=customer.id,
                    event_type="bundling_offers",
                    message=text,
                    status="sent",
                ))
                db.session.add(Event(
                    tenant_id=tenant.tenant_id if tenant else None,
                    customer_id=customer.id,
                    event_type="bundling_offers",
                    channel="whatsapp",
                    sent_at=datetime.utcnow(),
                    status="sent",
                ))
                sent_messages += 1

            db.session.commit()
            flash(f"Event check completed. {sent_messages} messages logged.", "info")
            return redirect(url_for("events"))

        return render_template("events.html", rules=rules_description())

    @app.route("/reports")
    @login_required
    def reports():
        logs = MessageLog.query.order_by(MessageLog.sent_at.desc()).all()
        return render_template("reports.html", logs=logs)

    @app.route("/reports/download")
    @login_required
    def download_reports():
        logs = MessageLog.query.order_by(MessageLog.sent_at.desc()).all()
        if not logs:
            flash("No logs to export.", "warning")
            return redirect(url_for("reports"))
        df = pd.DataFrame([
            {
                "id": log.id,
                "customer_id": log.customer_id,
                "customer_name": log.customer.name if log.customer else None,
                "event_type": log.event_type,
                "message": log.message,
                "sent_at": log.sent_at.isoformat(timespec="seconds"),
                "status": log.status,
            }
            for log in logs
        ])
        csv_path = os.path.join(os.path.dirname(__file__), "message_logs.csv")
        df.to_csv(csv_path, index=False)
        return send_file(csv_path, as_attachment=True, download_name="message_logs.csv")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
