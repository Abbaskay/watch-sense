from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class Tenant(db.Model):
    __tablename__ = "tenants"

    tenant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Tenant {self.tenant_id} {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="owner")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tenant = db.relationship("Tenant", backref=db.backref("users", lazy=True))

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.email}>"


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    model = db.Column(db.String(120), nullable=True)
    mobile = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Multi-tenant support (optional for backward compatibility)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = db.relationship("Tenant", backref=db.backref("customers", lazy=True))

    def __repr__(self) -> str:
        return f"<Customer {self.id} {self.name}>"


class Watch(db.Model):
    __tablename__ = "watches"

    watch_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    brand = db.Column(db.String(255), nullable=True)
    model_no = db.Column(db.String(255), nullable=True)
    serial_no = db.Column(db.String(255), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    tenant = db.relationship("Tenant", backref=db.backref("watches", lazy=True))
    customer = db.relationship("Customer", backref=db.backref("watches", lazy=True))

    def __repr__(self) -> str:
        return f"<Watch {self.watch_id} {self.brand} {self.model_no}>"


class Service(db.Model):
    __tablename__ = "services"

    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    watch_id = db.Column(db.Integer, db.ForeignKey("watches.watch_id"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    service_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    watch = db.relationship("Watch", backref=db.backref("services", lazy=True))
    tenant = db.relationship("Tenant", backref=db.backref("services", lazy=True))

    def __repr__(self) -> str:
        return f"<Service {self.service_id} {self.service_type}>"


class Template(db.Model):
    __tablename__ = "templates"

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)

    tenant = db.relationship("Tenant", backref=db.backref("templates", lazy=True))

    def __repr__(self) -> str:
        return f"<Template {self.template_id} {self.name}>"


class Event(db.Model):
    __tablename__ = "events"

    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.service_id"), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    status = db.Column(db.String(20), default="sent", nullable=False)

    tenant = db.relationship("Tenant")
    customer = db.relationship("Customer")
    service = db.relationship("Service")

    def __repr__(self) -> str:
        return f"<Event {self.event_id} {self.event_type} {self.status}>"


class MessageLog(db.Model):
    __tablename__ = "message_logs"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(40), default="sent", nullable=False)

    customer = db.relationship("Customer", backref=db.backref("messages", lazy=True))

    def __repr__(self) -> str:
        return f"<MessageLog {self.id} customer={self.customer_id} event={self.event_type}>"
