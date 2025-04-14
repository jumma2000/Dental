from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    invoices = db.relationship('Invoice', backref='patient', lazy=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)  # السعر بالدينار الليبي
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_items = db.relationship('InvoiceItem', backref='treatment', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    total_amount = db.Column(db.Float, default=0.0)  # المبلغ الإجمالي بالدينار الليبي
    paid_amount = db.Column(db.Float, default=0.0)  # المبلغ المدفوع بالدينار الليبي
    payment_method = db.Column(db.String(20), default='cash')  # cash, card
    status = db.Column(db.String(20), default='unpaid')  # unpaid, partial, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

    # حقول تتبع الديون
    previous_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)  # الفاتورة السابقة
    carried_amount = db.Column(db.Float, default=0.0)  # المبلغ المحمول من الفاتورة السابقة
    next_invoices = db.relationship('Invoice', backref=db.backref('previous_invoice', remote_side=[id]), lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)  # السعر بالدينار الليبي
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
