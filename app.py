from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Patient, Doctor, Treatment, Appointment, Invoice, InvoiceItem, User, Role, Permission, RolePermission
from datetime import datetime, date, time, timedelta
import os
import functools

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'dental_clinic_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'dental_clinic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعدادات ترقيم الصفحات
app.config['ITEMS_PER_PAGE'] = 10

csrf = CSRFProtect(app)
db.init_app(app)

# إعداد نظام تسجيل الدخول
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'warning'

# إعادة توجيه المستخدم إلى صفحة تسجيل الدخول إذا لم يكن مسجلاً
@app.before_request
def check_login():
    # قائمة المسارات المسموح بها بدون تسجيل دخول
    public_endpoints = ['login', 'static']

    # التحقق من أن المستخدم مسجل الدخول أو يحاول الوصول إلى مسار عام
    if not current_user.is_authenticated and request.endpoint not in public_endpoints:
        return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# دالة للتحقق من الصلاحيات
def permission_required(permission):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.has_permission(permission):
                flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# دالة للتحقق من المستخدم المسؤول
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role.name != 'admin':
            flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# إنشاء قاعدة البيانات إذا لم تكن موجودة
with app.app_context():
    import os
    import sqlite3

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

    # إنشاء الأدوار والصلاحيات الافتراضية إذا لم تكن موجودة
    # التحقق من وجود الأدوار
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        # إنشاء الأدوار
        admin_role = Role(name='admin', description='مدير النظام')
        doctor_role = Role(name='doctor', description='طبيب')
        receptionist_role = Role(name='receptionist', description='موظف استقبال')
        accountant_role = Role(name='accountant', description='محاسب')

        db.session.add_all([admin_role, doctor_role, receptionist_role, accountant_role])
        db.session.commit()

        # إنشاء الصلاحيات
        permissions = [
            Permission(name='view_patients', description='عرض المرضى'),
            Permission(name='add_patient', description='إضافة مريض'),
            Permission(name='edit_patient', description='تعديل بيانات المريض'),
            Permission(name='delete_patient', description='حذف مريض'),

            Permission(name='view_doctors', description='عرض الأطباء'),
            Permission(name='add_doctor', description='إضافة طبيب'),
            Permission(name='edit_doctor', description='تعديل بيانات الطبيب'),
            Permission(name='delete_doctor', description='حذف طبيب'),

            Permission(name='view_treatments', description='عرض العلاجات'),
            Permission(name='add_treatment', description='إضافة علاج'),
            Permission(name='edit_treatment', description='تعديل بيانات العلاج'),
            Permission(name='delete_treatment', description='حذف علاج'),

            Permission(name='view_appointments', description='عرض المواعيد'),
            Permission(name='add_appointment', description='إضافة موعد'),
            Permission(name='edit_appointment', description='تعديل بيانات الموعد'),
            Permission(name='delete_appointment', description='حذف موعد'),

            Permission(name='view_invoices', description='عرض الفواتير'),
            Permission(name='add_invoice', description='إضافة فاتورة'),
            Permission(name='edit_invoice', description='تعديل بيانات الفاتورة'),
            Permission(name='delete_invoice', description='حذف فاتورة'),

            Permission(name='view_reports', description='عرض التقارير'),

            Permission(name='manage_users', description='إدارة المستخدمين'),
        ]

        db.session.add_all(permissions)
        db.session.commit()

        # إعطاء جميع الصلاحيات للمدير
        for permission in Permission.query.all():
            role_permission = RolePermission(role_id=admin_role.id, permission_id=permission.id)
            db.session.add(role_permission)

        # إعطاء صلاحيات للطبيب
        doctor_permissions = ['view_patients', 'view_appointments', 'edit_appointment', 'view_treatments', 'view_invoices']
        for perm_name in doctor_permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm:
                role_permission = RolePermission(role_id=doctor_role.id, permission_id=perm.id)
                db.session.add(role_permission)

        # إعطاء صلاحيات لموظف الاستقبال
        receptionist_permissions = ['view_patients', 'add_patient', 'edit_patient', 'view_doctors', 'view_treatments',
                                  'view_appointments', 'add_appointment', 'edit_appointment', 'delete_appointment',
                                  'view_invoices']
        for perm_name in receptionist_permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm:
                role_permission = RolePermission(role_id=receptionist_role.id, permission_id=perm.id)
                db.session.add(role_permission)

        # إعطاء صلاحيات للمحاسب
        accountant_permissions = ['view_patients', 'view_treatments', 'view_invoices', 'add_invoice', 'edit_invoice',
                                'view_reports']
        for perm_name in accountant_permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm:
                role_permission = RolePermission(role_id=accountant_role.id, permission_id=perm.id)
                db.session.add(role_permission)

        db.session.commit()

        # إنشاء مستخدم مسؤول افتراضي
        admin_user = User(username='admin', email='admin@example.com', full_name='مدير النظام', role_id=admin_role.id)
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()

        print("Created default roles, permissions, and admin user")

# ======== نظام المصادقة وإدارة المستخدمين ========
@app.route('/login', methods=['GET', 'POST'])
def login():
    # إذا كان المستخدم مسجل الدخول بالفعل، نوجهه إلى الصفحة الرئيسية
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('تم تعطيل هذا الحساب. يرجى التواصل مع المسؤول.', 'danger')
                return redirect(url_for('login'))

            login_user(user, remember=remember)
            user.last_login = datetime.now()
            db.session.commit()

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')

    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        full_name = request.form['full_name']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role_id = request.form['role_id']

        # التحقق من تطابق كلمة المرور
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'danger')
            return redirect(url_for('register'))

        # التحقق من عدم وجود اسم المستخدم أو البريد الإلكتروني مسبقاً
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود بالفعل', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('البريد الإلكتروني موجود بالفعل', 'danger')
            return redirect(url_for('register'))

        # إنشاء المستخدم الجديد
        new_user = User(username=username, email=email, full_name=full_name, phone=phone, role_id=role_id)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('تم إنشاء المستخدم بنجاح', 'success')
        return redirect(url_for('users'))

    roles = Role.query.all()
    return render_template('auth/register.html', roles=roles)

@app.route('/users')
@admin_required
def users():
    # الحصول على معاملات البحث
    username = request.args.get('username', '')
    email = request.args.get('email', '')
    role_id = request.args.get('role_id', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # بدء الاستعلام
    query = User.query

    # تطبيق معاملات البحث
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))

    if email:
        query = query.filter(User.email.ilike(f'%{email}%'))

    if role_id:
        try:
            role_id_int = int(role_id)
            query = query.filter(User.role_id == role_id_int)
        except ValueError:
            pass

    if status:
        is_active = (status == 'active')
        query = query.filter(User.is_active == is_active)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(User.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            # إضافة يوم واحد لتضمين اليوم المحدد
            date_to_obj = date_to_obj + timedelta(days=1)
            query = query.filter(User.created_at < date_to_obj)
        except ValueError:
            pass

    # ترتيب النتائج
    query = query.order_by(User.id.asc())

    # الحصول على النتائج
    all_users = query.all()
    all_roles = Role.query.all()
    all_permissions = Permission.query.all()

    return render_template('auth/users.html', users=all_users, roles=all_roles, permissions=all_permissions)

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        full_name = request.form['full_name']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role_id = request.form['role_id']
        is_active = 'is_active' in request.form

        # التحقق من عدم وجود اسم المستخدم أو البريد الإلكتروني لمستخدم آخر
        username_exists = User.query.filter(User.username == username, User.id != id).first()
        if username_exists:
            flash('اسم المستخدم موجود بالفعل', 'danger')
            return redirect(url_for('edit_user', id=id))

        email_exists = User.query.filter(User.email == email, User.id != id).first()
        if email_exists:
            flash('البريد الإلكتروني موجود بالفعل', 'danger')
            return redirect(url_for('edit_user', id=id))

        # تحديث بيانات المستخدم
        user.username = username
        user.email = email
        user.full_name = full_name
        user.phone = phone
        user.role_id = role_id
        user.is_active = is_active

        # تحديث كلمة المرور إذا تم توفيرها
        if password:
            if password != confirm_password:
                flash('كلمات المرور غير متطابقة', 'danger')
                return redirect(url_for('edit_user', id=id))
            user.set_password(password)

        db.session.commit()
        flash('تم تحديث بيانات المستخدم بنجاح', 'success')
        return redirect(url_for('users'))

    roles = Role.query.all()
    return render_template('auth/edit_user.html', user=user, roles=roles)

@app.route('/users/toggle-status/<int:id>')
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)

    # لا يمكن تعطيل المستخدم الحالي
    if user.id == current_user.id:
        flash('لا يمكنك تعطيل حسابك الحالي', 'danger')
        return redirect(url_for('users'))

    user.is_active = not user.is_active
    db.session.commit()

    status_msg = 'تفعيل' if user.is_active else 'تعطيل'
    flash(f'تم {status_msg} حساب المستخدم بنجاح', 'success')
    return redirect(url_for('users'))

@app.route('/users/delete/<int:id>')
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)

    # لا يمكن حذف المستخدم الحالي أو المسؤول
    if user.id == current_user.id or user.role.name == 'admin':
        flash('لا يمكنك حذف هذا المستخدم', 'danger')
        return redirect(url_for('users'))

    db.session.delete(user)
    db.session.commit()

    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('users'))

@app.route('/roles/permissions/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_role_permissions(id):
    role = Role.query.get_or_404(id)

    if request.method == 'POST':
        # حذف جميع الصلاحيات الحالية
        RolePermission.query.filter_by(role_id=role.id).delete()

        # إضافة الصلاحيات الجديدة
        permission_ids = request.form.getlist('permissions')
        for perm_id in permission_ids:
            role_permission = RolePermission(role_id=role.id, permission_id=int(perm_id))
            db.session.add(role_permission)

        db.session.commit()
        flash('تم تحديث صلاحيات الدور بنجاح', 'success')
        return redirect(url_for('users'))

    permissions = Permission.query.all()
    role_permissions = [rp.permission_id for rp in role.permissions]

    return render_template('auth/edit_role_permissions.html', role=role, permissions=permissions, role_permissions=role_permissions)

# الصفحة الرئيسية
@app.route('/')
def index():
    # إذا لم يكن المستخدم مسجل الدخول، سيتم توجيهه إلى صفحة تسجيل الدخول بواسطة before_request
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
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
@permission_required('view_patients')
def patients():
    # الحصول على معاملات البحث والترقيم
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    search_by = request.args.get('search_by', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # بدء الاستعلام
    query = Patient.query

    # تطبيق معاملات البحث
    if search_query:
        if search_by == 'name':
            query = query.filter(Patient.name.ilike(f'%{search_query}%'))
        elif search_by == 'phone':
            query = query.filter(Patient.phone.ilike(f'%{search_query}%'))
        elif search_by == 'address':
            query = query.filter(Patient.address.ilike(f'%{search_query}%'))
        else:  # all
            query = query.filter(
                db.or_(
                    Patient.name.ilike(f'%{search_query}%'),
                    Patient.phone.ilike(f'%{search_query}%'),
                    Patient.address.ilike(f'%{search_query}%')
                )
            )

    # تطبيق فلتر التاريخ
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        query = query.filter(Patient.created_at >= date_from_obj)

    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        # إضافة يوم واحد لتضمين اليوم المحدد
        date_to_obj = date_to_obj + timedelta(days=1)
        query = query.filter(Patient.created_at < date_to_obj)

    # ترتيب النتائج حسب تاريخ الإنشاء (الأحدث أولاً)
    query = query.order_by(Patient.created_at.desc())

    # تطبيق ترقيم الصفحات
    pagination = query.paginate(page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False)
    patients = pagination.items

    # تجميع معاملات البحث لتمريرها إلى مكون الترقيم
    search_params = {}
    if search_query:
        search_params['q'] = search_query
    if search_by != 'all':
        search_params['search_by'] = search_by
    if date_from:
        search_params['date_from'] = date_from
    if date_to:
        search_params['date_to'] = date_to

    return render_template('patients.html',
                           patients=patients,
                           pagination=pagination,
                           search_query=search_query,
                           search_params=search_params)

@app.route('/patients/add', methods=['GET', 'POST'])
@permission_required('add_patient')
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
@permission_required('edit_patient')
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
@permission_required('delete_patient')
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()

    flash('تم حذف المريض بنجاح!', 'success')
    return redirect(url_for('patients'))

# ======== إدارة الأطباء ========
@app.route('/doctors')
@permission_required('view_doctors')
def doctors():
    all_doctors = Doctor.query.all()
    return render_template('doctors.html', doctors=all_doctors)

@app.route('/doctors/add', methods=['GET', 'POST'])
@permission_required('add_doctor')
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
@permission_required('edit_doctor')
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
@permission_required('delete_doctor')
def delete_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()

    flash('تم حذف الطبيب بنجاح!', 'success')
    return redirect(url_for('doctors'))

# ======== إدارة العلاجات ========
@app.route('/treatments')
@permission_required('view_treatments')
def treatments():
    all_treatments = Treatment.query.all()
    return render_template('treatments.html', treatments=all_treatments)

@app.route('/treatments/add', methods=['GET', 'POST'])
@permission_required('add_treatment')
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
@permission_required('edit_treatment')
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
@permission_required('delete_treatment')
def delete_treatment(id):
    treatment = Treatment.query.get_or_404(id)
    db.session.delete(treatment)
    db.session.commit()

    flash('تم حذف العلاج بنجاح!', 'success')
    return redirect(url_for('treatments'))

# ======== إدارة المواعيد ========
@app.route('/appointments')
@permission_required('view_appointments')
def appointments():
    # الحصول على معاملات البحث والترقيم
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    search_by = request.args.get('search_by', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # الحصول على حالات المواعيد المحددة
    status_scheduled = request.args.get('status_scheduled')
    status_completed = request.args.get('status_completed')
    status_cancelled = request.args.get('status_cancelled')

    # بدء الاستعلام
    query = Appointment.query

    # تطبيق معاملات البحث
    if search_query:
        if search_by == 'patient':
            query = query.join(Patient).filter(Patient.name.ilike(f'%{search_query}%'))
        elif search_by == 'doctor':
            query = query.join(Doctor).filter(Doctor.name.ilike(f'%{search_query}%'))
        elif search_by == 'status':
            query = query.filter(Appointment.status.ilike(f'%{search_query}%'))
        else:  # all
            query = query.join(Patient).join(Doctor).filter(
                db.or_(
                    Patient.name.ilike(f'%{search_query}%'),
                    Doctor.name.ilike(f'%{search_query}%'),
                    Appointment.status.ilike(f'%{search_query}%'),
                    Appointment.notes.ilike(f'%{search_query}%')
                )
            )

    # تطبيق فلتر التاريخ
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        query = query.filter(Appointment.date >= date_from_obj)

    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        query = query.filter(Appointment.date <= date_to_obj)

    # تطبيق فلتر الحالة
    status_filters = []
    if status_scheduled:
        status_filters.append('scheduled')
    if status_completed:
        status_filters.append('completed')
    if status_cancelled:
        status_filters.append('cancelled')

    if status_filters:
        query = query.filter(Appointment.status.in_(status_filters))

    # ترتيب النتائج حسب التاريخ (الأحدث أولاً)
    query = query.order_by(Appointment.date.desc(), Appointment.time.desc())

    # تطبيق ترقيم الصفحات
    pagination = query.paginate(page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False)
    appointments = pagination.items

    # تجميع معاملات البحث لتمريرها إلى مكون الترقيم
    search_params = {}
    if search_query:
        search_params['q'] = search_query
    if search_by != 'all':
        search_params['search_by'] = search_by
    if date_from:
        search_params['date_from'] = date_from
    if date_to:
        search_params['date_to'] = date_to
    if status_scheduled:
        search_params['status_scheduled'] = status_scheduled
    if status_completed:
        search_params['status_completed'] = status_completed
    if status_cancelled:
        search_params['status_cancelled'] = status_cancelled

    return render_template('appointments.html',
                           appointments=appointments,
                           pagination=pagination,
                           search_query=search_query,
                           search_params=search_params)

@app.route('/appointments/add', methods=['GET', 'POST'])
@permission_required('add_appointment')
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
@permission_required('edit_appointment')
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
@permission_required('delete_appointment')
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()

    flash('تم حذف الموعد بنجاح!', 'success')
    return redirect(url_for('appointments'))

# ======== إدارة الفواتير ========
@app.route('/invoices')
@permission_required('view_invoices')
def invoices():
    # الحصول على معاملات البحث والترقيم
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    search_by = request.args.get('search_by', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    amount_from = request.args.get('amount_from', '')
    amount_to = request.args.get('amount_to', '')

    # الحصول على حالات الفواتير المحددة
    status_paid = request.args.get('status_paid')
    status_partial = request.args.get('status_partial')
    status_unpaid = request.args.get('status_unpaid')
    status_carried_forward = request.args.get('status_carried_forward')
    status_paid_in_next = request.args.get('status_paid_in_next')

    # بدء الاستعلام
    query = Invoice.query

    # تطبيق معاملات البحث
    if search_query:
        if search_by == 'invoice_id':
            try:
                invoice_id = int(search_query)
                query = query.filter(Invoice.id == invoice_id)
            except ValueError:
                pass  # إذا لم يكن رقماً صحيحاً، لا تطبق الفلتر
        elif search_by == 'patient':
            query = query.join(Patient).filter(Patient.name.ilike(f'%{search_query}%'))
        elif search_by == 'status':
            query = query.filter(Invoice.status.ilike(f'%{search_query}%'))
        else:  # all
            try:
                invoice_id = int(search_query)
                id_filter = Invoice.id == invoice_id
            except ValueError:
                id_filter = db.false()

            query = query.join(Patient).filter(
                db.or_(
                    id_filter,
                    Patient.name.ilike(f'%{search_query}%'),
                    Invoice.status.ilike(f'%{search_query}%')
                )
            )

    # تطبيق فلتر التاريخ
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        query = query.filter(Invoice.date >= date_from_obj)

    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        query = query.filter(Invoice.date <= date_to_obj)

    # تطبيق فلتر المبلغ
    if amount_from:
        try:
            amount_from_val = float(amount_from)
            query = query.filter(Invoice.total_amount >= amount_from_val)
        except ValueError:
            pass

    if amount_to:
        try:
            amount_to_val = float(amount_to)
            query = query.filter(Invoice.total_amount <= amount_to_val)
        except ValueError:
            pass

    # تطبيق فلتر الحالة
    status_filters = []
    if status_paid:
        status_filters.append('paid')
    if status_partial:
        status_filters.append('partial')
    if status_unpaid:
        status_filters.append('unpaid')
    if status_carried_forward:
        status_filters.append('carried_forward')
    if status_paid_in_next:
        status_filters.append('paid_in_next')

    if status_filters:
        query = query.filter(Invoice.status.in_(status_filters))

    # ترتيب النتائج حسب التاريخ (الأحدث أولاً)
    query = query.order_by(Invoice.date.desc(), Invoice.id.desc())

    # تطبيق ترقيم الصفحات
    pagination = query.paginate(page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False)
    invoices = pagination.items

    # تجميع معاملات البحث لتمريرها إلى مكون الترقيم
    search_params = {}
    if search_query:
        search_params['q'] = search_query
    if search_by != 'all':
        search_params['search_by'] = search_by
    if date_from:
        search_params['date_from'] = date_from
    if date_to:
        search_params['date_to'] = date_to
    if amount_from:
        search_params['amount_from'] = amount_from
    if amount_to:
        search_params['amount_to'] = amount_to
    if status_paid:
        search_params['status_paid'] = status_paid
    if status_partial:
        search_params['status_partial'] = status_partial
    if status_unpaid:
        search_params['status_unpaid'] = status_unpaid
    if status_carried_forward:
        search_params['status_carried_forward'] = status_carried_forward
    if status_paid_in_next:
        search_params['status_paid_in_next'] = status_paid_in_next

    return render_template('invoices.html',
                           invoices=invoices,
                           pagination=pagination,
                           search_query=search_query,
                           search_params=search_params)

@app.route('/invoices/add', methods=['GET', 'POST'])
@permission_required('add_invoice')
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
@permission_required('edit_invoice')
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
@permission_required('delete_invoice')
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

# ======== البحث الشامل ========
@app.route('/search')
def global_search():
    # الحصول على معاملات البحث
    query = request.args.get('q', '')
    search_in = request.args.get('search_in', 'all')

    # التحقق من وجود استعلام بحث
    if not query:
        return redirect(url_for('index'))

    # البحث في المرضى
    patients = []
    if search_in in ['all', 'patients']:
        patients = Patient.query.filter(
            db.or_(
                Patient.name.ilike(f'%{query}%'),
                Patient.phone.ilike(f'%{query}%'),
                Patient.address.ilike(f'%{query}%')
            )
        ).all()

    # البحث في المواعيد
    appointments = []
    if search_in in ['all', 'appointments']:
        appointments = Appointment.query.join(Patient).join(Doctor).filter(
            db.or_(
                Patient.name.ilike(f'%{query}%'),
                Doctor.name.ilike(f'%{query}%'),
                Appointment.notes.ilike(f'%{query}%')
            )
        ).all()

    # البحث في الفواتير
    invoices = []
    if search_in in ['all', 'invoices']:
        # محاولة البحث برقم الفاتورة
        try:
            invoice_id = int(query)
            id_filter = Invoice.id == invoice_id
        except ValueError:
            id_filter = db.false()

        invoices = Invoice.query.join(Patient).filter(
            db.or_(
                id_filter,
                Patient.name.ilike(f'%{query}%'),
                Invoice.status.ilike(f'%{query}%')
            )
        ).all()

    return render_template('search_results.html',
                           query=query,
                           search_in=search_in,
                           patients=patients,
                           appointments=appointments,
                           invoices=invoices)

# ======== التقارير ========
@app.route('/reports')
@permission_required('view_reports')
def reports():
    return render_template('reports.html')

@app.route('/reports/revenue')
@permission_required('view_reports')
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
@permission_required('view_reports')
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
@permission_required('view_reports')
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
