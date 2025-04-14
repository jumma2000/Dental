from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from models import db, Patient, Doctor, Treatment, Appointment, Invoice, InvoiceItem
from datetime import datetime, date, time
import os

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'dental_clinic_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'dental_clinic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

csrf = CSRFProtect(app)
db.init_app(app)

# إنشاء قاعدة البيانات إذا لم تكن موجودة
with app.app_context():
    import os
    import sqlite3
    from sqlalchemy import text

    # مسار قاعدة البيانات
    db_path = os.path.join(app.instance_path, 'dental_clinic.db')

    # التحقق من وجود قاعدة البيانات
    db_exists = os.path.exists(db_path)

    # إنشاء قاعدة البيانات والجداول
    db.create_all()

    # إذا كانت قاعدة البيانات موجودة مسبقاً، نتحقق من وجود الأعمدة الجديدة
    if db_exists:
        try:
            # التحقق من وجود الأعمدة الجديدة
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # التحقق من وجود عمود previous_invoice_id
            cursor.execute("PRAGMA table_info(invoice)")
            columns = [column[1] for column in cursor.fetchall()]

            # إذا لم يكن العمود موجوداً، نضيفه
            if 'previous_invoice_id' not in columns:
                cursor.execute("ALTER TABLE invoice ADD COLUMN previous_invoice_id INTEGER REFERENCES invoice(id)")
                print("Added previous_invoice_id column to invoice table")

            # التحقق من وجود عمود carried_amount
            if 'carried_amount' not in columns:
                cursor.execute("ALTER TABLE invoice ADD COLUMN carried_amount FLOAT DEFAULT 0.0")
                print("Added carried_amount column to invoice table")

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating database schema: {e}")

# الصفحة الرئيسية
@app.route('/')
def index():
    # إحصائيات سريعة
    patients_count = Patient.query.count()
    doctors_count = Doctor.query.count()
    appointments_count = Appointment.query.count()
    invoices_count = Invoice.query.count()

    # مواعيد اليوم
    today_appointments = Appointment.query.filter_by(date=date.today()).all()

    # آخر الفواتير
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()

    return render_template('index.html',
                           patients_count=patients_count,
                           doctors_count=doctors_count,
                           appointments_count=appointments_count,
                           invoices_count=invoices_count,
                           today_appointments=today_appointments,
                           recent_invoices=recent_invoices,
                           now=datetime.now())

# ======== إدارة المرضى ========
@app.route('/patients')
def patients():
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

@app.route('/patients/add', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        new_patient = Patient(name=name, phone=phone, address=address)
        db.session.add(new_patient)
        db.session.commit()

        flash('تمت إضافة المريض بنجاح!', 'success')
        return redirect(url_for('patients'))

    return render_template('add_patient.html')

@app.route('/patients/edit/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    patient = Patient.query.get_or_404(id)

    if request.method == 'POST':
        patient.name = request.form['name']
        patient.phone = request.form['phone']
        patient.address = request.form['address']

        db.session.commit()
        flash('تم تحديث بيانات المريض بنجاح!', 'success')
        return redirect(url_for('patients'))

    return render_template('edit_patient.html', patient=patient)

@app.route('/patients/delete/<int:id>')
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()

    flash('تم حذف المريض بنجاح!', 'success')
    return redirect(url_for('patients'))

# ======== إدارة الأطباء ========
@app.route('/doctors')
def doctors():
    all_doctors = Doctor.query.all()
    return render_template('doctors.html', doctors=all_doctors)

@app.route('/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        new_doctor = Doctor(name=name, phone=phone, address=address)
        db.session.add(new_doctor)
        db.session.commit()

        flash('تمت إضافة الطبيب بنجاح!', 'success')
        return redirect(url_for('doctors'))

    return render_template('add_doctor.html')

@app.route('/doctors/edit/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)

    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.phone = request.form['phone']
        doctor.address = request.form['address']

        db.session.commit()
        flash('تم تحديث بيانات الطبيب بنجاح!', 'success')
        return redirect(url_for('doctors'))

    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/doctors/delete/<int:id>')
def delete_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()

    flash('تم حذف الطبيب بنجاح!', 'success')
    return redirect(url_for('doctors'))

# ======== إدارة العلاجات ========
@app.route('/treatments')
def treatments():
    all_treatments = Treatment.query.all()
    return render_template('treatments.html', treatments=all_treatments)

@app.route('/treatments/add', methods=['GET', 'POST'])
def add_treatment():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])

        new_treatment = Treatment(name=name, description=description, price=price)
        db.session.add(new_treatment)
        db.session.commit()

        flash('تمت إضافة العلاج بنجاح!', 'success')
        return redirect(url_for('treatments'))

    return render_template('add_treatment.html')

@app.route('/treatments/edit/<int:id>', methods=['GET', 'POST'])
def edit_treatment(id):
    treatment = Treatment.query.get_or_404(id)

    if request.method == 'POST':
        treatment.name = request.form['name']
        treatment.description = request.form['description']
        treatment.price = float(request.form['price'])

        db.session.commit()
        flash('تم تحديث بيانات العلاج بنجاح!', 'success')
        return redirect(url_for('treatments'))

    return render_template('edit_treatment.html', treatment=treatment)

@app.route('/treatments/delete/<int:id>')
def delete_treatment(id):
    treatment = Treatment.query.get_or_404(id)
    db.session.delete(treatment)
    db.session.commit()

    flash('تم حذف العلاج بنجاح!', 'success')
    return redirect(url_for('treatments'))

# ======== إدارة المواعيد ========
@app.route('/appointments')
def appointments():
    all_appointments = Appointment.query.all()
    return render_template('appointments.html', appointments=all_appointments)

@app.route('/appointments/add', methods=['GET', 'POST'])
def add_appointment():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        doctor_id = request.form['doctor_id']
        date_str = request.form['date']
        time_str = request.form['time']
        notes = request.form['notes']

        # تحويل التاريخ والوقت
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        # التحقق من تضارب المواعيد
        existing_appointments = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time
        ).all()

        if existing_appointments:
            flash('هناك موعد آخر في نفس الوقت لهذا الطبيب!', 'danger')
            return redirect(url_for('add_appointment'))

        new_appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time,
            notes=notes
        )

        db.session.add(new_appointment)
        db.session.commit()

        flash('تم حجز الموعد بنجاح!', 'success')
        return redirect(url_for('appointments'))

    patients = Patient.query.all()
    doctors = Doctor.query.all()
    return render_template('add_appointment.html', patients=patients, doctors=doctors)

@app.route('/appointments/edit/<int:id>', methods=['GET', 'POST'])
def edit_appointment(id):
    appointment = Appointment.query.get_or_404(id)

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        doctor_id = request.form['doctor_id']
        date_str = request.form['date']
        time_str = request.form['time']
        notes = request.form['notes']
        status = request.form['status']

        # تحويل التاريخ والوقت
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        # التحقق من تضارب المواعيد (باستثناء الموعد الحالي)
        existing_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.date == appointment_date,
            Appointment.time == appointment_time,
            Appointment.id != id
        ).all()

        if existing_appointments:
            flash('هناك موعد آخر في نفس الوقت لهذا الطبيب!', 'danger')
            return redirect(url_for('edit_appointment', id=id))

        appointment.patient_id = patient_id
        appointment.doctor_id = doctor_id
        appointment.date = appointment_date
        appointment.time = appointment_time
        appointment.notes = notes
        appointment.status = status

        db.session.commit()
        flash('تم تحديث الموعد بنجاح!', 'success')
        return redirect(url_for('appointments'))

    patients = Patient.query.all()
    doctors = Doctor.query.all()
    return render_template('edit_appointment.html', appointment=appointment, patients=patients, doctors=doctors)

@app.route('/appointments/delete/<int:id>')
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()

    flash('تم حذف الموعد بنجاح!', 'success')
    return redirect(url_for('appointments'))

# ======== إدارة الفواتير ========
@app.route('/invoices')
def invoices():
    all_invoices = Invoice.query.all()
    return render_template('invoices.html', invoices=all_invoices)

@app.route('/invoices/add', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        payment_method = request.form['payment_method']
        carry_forward = request.form.get('carry_forward', 'no')

        # إنشاء فاتورة جديدة
        new_invoice = Invoice(
            patient_id=patient_id,
            payment_method=payment_method,
            date=date.today()
        )

        db.session.add(new_invoice)
        db.session.commit()

        # إذا تم اختيار ترحيل الديون السابقة
        if carry_forward == 'yes':
            # البحث عن الفواتير السابقة غير المدفوعة بالكامل لنفس المريض
            previous_invoices = Invoice.query.filter(
                Invoice.patient_id == patient_id,
                Invoice.id != new_invoice.id,
                Invoice.status.in_(['unpaid', 'partial'])
            ).order_by(Invoice.date.desc()).all()

            if previous_invoices:
                # اختيار أحدث فاتورة غير مدفوعة
                previous_invoice = previous_invoices[0]
                remaining_amount = previous_invoice.total_amount - previous_invoice.paid_amount

                if remaining_amount > 0:
                    # إضافة المبلغ المتبقي إلى الفاتورة الجديدة
                    new_invoice.previous_invoice_id = previous_invoice.id
                    new_invoice.carried_amount = remaining_amount
                    new_invoice.total_amount += remaining_amount

                    # تحديث حالة الفاتورة السابقة
                    previous_invoice.status = 'carried_forward'

                    db.session.commit()
                    flash(f'تم ترحيل المبلغ المتبقي {remaining_amount} د.ل من الفاتورة السابقة #{previous_invoice.id}', 'info')

        # إعادة التوجيه إلى صفحة تحرير الفاتورة لإضافة العناصر
        return redirect(url_for('edit_invoice', id=new_invoice.id))

    # الحصول على قائمة المرضى والفواتير غير المدفوعة
    patients = Patient.query.all()

    # تحضير قاموس للفواتير غير المدفوعة لكل مريض
    unpaid_invoices = {}
    for patient in patients:
        unpaid = Invoice.query.filter(
            Invoice.patient_id == patient.id,
            Invoice.status.in_(['unpaid', 'partial'])
        ).order_by(Invoice.date.desc()).all()

        if unpaid:
            unpaid_invoices[patient.id] = unpaid

    return render_template('add_invoice.html', patients=patients, unpaid_invoices=unpaid_invoices)

@app.route('/invoices/edit/<int:id>', methods=['GET', 'POST'])
def edit_invoice(id):
    invoice = Invoice.query.get_or_404(id)

    if request.method == 'POST':
        invoice.patient_id = request.form['patient_id']
        invoice.payment_method = request.form['payment_method']
        invoice.paid_amount = float(request.form['paid_amount'])

        # تحديث حالة الفاتورة بناءً على المبلغ المدفوع
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'paid'

            # إذا كانت الفاتورة مدفوعة بالكامل وكانت مرتبطة بفاتورة سابقة
            if invoice.previous_invoice_id:
                previous_invoice = Invoice.query.get(invoice.previous_invoice_id)
                if previous_invoice and previous_invoice.status == 'carried_forward':
                    # تحديث حالة الفاتورة السابقة إلى مدفوعة
                    previous_invoice.status = 'paid_in_next'
                    flash(f'تم تحديث حالة الفاتورة السابقة #{previous_invoice.id} إلى مدفوعة في فاتورة لاحقة', 'info')
        elif invoice.paid_amount > 0:
            invoice.status = 'partial'
        else:
            invoice.status = 'unpaid'

        db.session.commit()
        flash('تم تحديث الفاتورة بنجاح!', 'success')
        return redirect(url_for('invoices'))

    # الحصول على الفاتورة السابقة إذا كانت موجودة
    previous_invoice = None
    if invoice.previous_invoice_id:
        previous_invoice = Invoice.query.get(invoice.previous_invoice_id)

    patients = Patient.query.all()
    treatments = Treatment.query.all()
    return render_template('edit_invoice.html', invoice=invoice, patients=patients, treatments=treatments, previous_invoice=previous_invoice)

@app.route('/invoices/delete/<int:id>')
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    db.session.delete(invoice)
    db.session.commit()

    flash('تم حذف الفاتورة بنجاح!', 'success')
    return redirect(url_for('invoices'))

@app.route('/invoices/view/<int:id>')
def view_invoice(id):
    invoice = Invoice.query.get_or_404(id)

    # الحصول على الفاتورة السابقة إذا كانت موجودة
    previous_invoice = None
    if invoice.previous_invoice_id:
        previous_invoice = Invoice.query.get(invoice.previous_invoice_id)

    return render_template('view_invoice.html', invoice=invoice, previous_invoice=previous_invoice)

# إضافة عنصر إلى الفاتورة
@app.route('/invoices/<int:invoice_id>/add_item', methods=['POST'])
def add_invoice_item(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    treatment_id = request.form['treatment_id']
    quantity = int(request.form['quantity'])

    treatment = Treatment.query.get_or_404(treatment_id)
    price = treatment.price

    # إضافة عنصر جديد إلى الفاتورة
    new_item = InvoiceItem(
        invoice_id=invoice_id,
        treatment_id=treatment_id,
        quantity=quantity,
        price=price
    )

    db.session.add(new_item)

    # تحديث إجمالي الفاتورة
    invoice.total_amount += price * quantity

    # تحديث حالة الفاتورة
    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = 'paid'
    elif invoice.paid_amount > 0:
        invoice.status = 'partial'
    else:
        invoice.status = 'unpaid'

    db.session.commit()

    flash('تمت إضافة العنصر إلى الفاتورة بنجاح!', 'success')
    return redirect(url_for('edit_invoice', id=invoice_id))

# حذف عنصر من الفاتورة
@app.route('/invoices/delete_item/<int:item_id>')
def delete_invoice_item(item_id):
    item = InvoiceItem.query.get_or_404(item_id)
    invoice_id = item.invoice_id
    invoice = Invoice.query.get_or_404(invoice_id)

    # تحديث إجمالي الفاتورة
    invoice.total_amount -= item.price * item.quantity

    # حذف العنصر
    db.session.delete(item)

    # تحديث حالة الفاتورة
    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = 'paid'
    elif invoice.paid_amount > 0:
        invoice.status = 'partial'
    else:
        invoice.status = 'unpaid'

    db.session.commit()

    flash('تم حذف العنصر من الفاتورة بنجاح!', 'success')
    return redirect(url_for('edit_invoice', id=invoice_id))

# ======== التقارير ========
@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/reports/revenue')
def revenue_report():
    # الحصول على معاملات التصفية
    period = request.args.get('period', 'monthly')
    start_date = request.args.get('start_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))

    # بيانات افتراضية للعرض
    revenue_data = [
        {'date': '2025-04-01', 'invoices_count': 5, 'total': 1500, 'paid': 1200, 'due': 300},
        {'date': '2025-04-02', 'invoices_count': 3, 'total': 900, 'paid': 900, 'due': 0},
        {'date': '2025-04-03', 'invoices_count': 7, 'total': 2100, 'paid': 1500, 'due': 600},
        {'date': '2025-04-04', 'invoices_count': 4, 'total': 1200, 'paid': 800, 'due': 400},
        {'date': '2025-04-05', 'invoices_count': 6, 'total': 1800, 'paid': 1800, 'due': 0},
    ]

    # إجماليات
    total_invoices = sum(item['invoices_count'] for item in revenue_data)
    total_revenue = sum(item['total'] for item in revenue_data)
    total_paid = sum(item['paid'] for item in revenue_data)
    total_due = sum(item['due'] for item in revenue_data)

    # بيانات الرسم البياني
    chart_labels = [item['date'] for item in revenue_data]
    chart_revenue = [item['total'] for item in revenue_data]
    chart_paid = [item['paid'] for item in revenue_data]
    chart_due = [item['due'] for item in revenue_data]

    return render_template('revenue_report.html',
                           period=period,
                           start_date=start_date,
                           end_date=end_date,
                           revenue_data=revenue_data,
                           total_invoices=total_invoices,
                           total_revenue=total_revenue,
                           total_paid=total_paid,
                           total_due=total_due,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           chart_paid=chart_paid,
                           chart_due=chart_due)

@app.route('/reports/debts')
def debts_report():
    # الحصول على معاملات التصفية
    status = request.args.get('status', 'all')
    date_range = request.args.get('date_range', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # الحصول على الفواتير غير المدفوعة
    invoices = Invoice.query.filter(Invoice.status.in_(['unpaid', 'partial'])).all()

    # إجماليات
    total_amount = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(invoice.paid_amount for invoice in invoices)
    total_debt = total_amount - total_paid
    unpaid_count = sum(1 for invoice in invoices if invoice.status == 'unpaid')
    partial_count = sum(1 for invoice in invoices if invoice.status == 'partial')

    # بيانات الرسم البياني
    # تجميع الديون حسب المريض
    patient_debts = {}
    for invoice in invoices:
        patient_name = invoice.patient.name
        debt = invoice.total_amount - invoice.paid_amount
        if patient_name in patient_debts:
            patient_debts[patient_name] += debt
        else:
            patient_debts[patient_name] = debt

    # ترتيب المرضى حسب الدين وأخذ أعلى 10
    sorted_patients = sorted(patient_debts.items(), key=lambda x: x[1], reverse=True)[:10]
    chart_labels = [patient[0] for patient in sorted_patients]
    chart_data = [patient[1] for patient in sorted_patients]

    return render_template('debts_report.html',
                           status=status,
                           date_range=date_range,
                           start_date=start_date,
                           end_date=end_date,
                           invoices=invoices,
                           total_amount=total_amount,
                           total_paid=total_paid,
                           total_debt=total_debt,
                           unpaid_count=unpaid_count,
                           partial_count=partial_count,
                           chart_labels=chart_labels,
                           chart_data=chart_data)

@app.route('/reports/treatments')
def treatments_report():
    # الحصول على معاملات التصفية
    period = request.args.get('period', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    limit = request.args.get('limit', '10')

    # بيانات افتراضية للعرض
    treatments_data = [
        {'name': 'تنظيف الأسنان', 'count': 45, 'price': 100, 'total_revenue': 4500, 'percentage': 30},
        {'name': 'حشو الأسنان', 'count': 30, 'price': 150, 'total_revenue': 4500, 'percentage': 30},
        {'name': 'تركيب تقويم', 'count': 10, 'price': 300, 'total_revenue': 3000, 'percentage': 20},
        {'name': 'خلع الأسنان', 'count': 15, 'price': 100, 'total_revenue': 1500, 'percentage': 10},
        {'name': 'تبييض الأسنان', 'count': 5, 'price': 300, 'total_revenue': 1500, 'percentage': 10},
    ]

    # إجماليات
    total_count = sum(item['count'] for item in treatments_data)
    total_revenue = sum(item['total_revenue'] for item in treatments_data)

    # بيانات الرسم البياني للعدد
    count_labels = [item['name'] for item in treatments_data]
    count_data = [item['count'] for item in treatments_data]

    # بيانات الرسم البياني للإيرادات
    revenue_labels = [item['name'] for item in treatments_data]
    revenue_data = [item['total_revenue'] for item in treatments_data]

    return render_template('treatments_report.html',
                           period=period,
                           start_date=start_date,
                           end_date=end_date,
                           limit=limit,
                           treatments_data=treatments_data,
                           total_count=total_count,
                           total_revenue=total_revenue,
                           count_labels=count_labels,
                           count_data=count_data,
                           revenue_labels=revenue_labels,
                           revenue_data=revenue_data)

@app.route('/reports/patients')
def patients_report():
    # سيتم تنفيذ هذا التقرير لاحقاً
    return render_template('reports.html')

@app.route('/reports/doctors')
def doctors_report():
    # سيتم تنفيذ هذا التقرير لاحقاً
    return render_template('reports.html')

@app.route('/reports/business-summary')
def business_summary_report():
    # سيتم تنفيذ هذا التقرير لاحقاً
    return render_template('reports.html')

@app.route('/api/dashboard-stats')
def dashboard_stats():
    # بيانات افتراضية للوحة المعلومات
    stats = {
        'current_month_revenue': 7500,
        'total_debts': 1300,
        'current_month_patients': 25,
        'today_appointments': 8
    }
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True)
