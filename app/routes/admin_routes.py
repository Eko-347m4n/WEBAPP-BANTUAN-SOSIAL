from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.database.models import User, Setting
from app.forms import RegistrationForm, SettingForm, EditUserForm # Ditambahkan EditUserForm
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Akses ditolak: hanya admin yang dapat mengakses halaman ini.', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_view

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    user_count = User.query.count()
    setting = Setting.query.first()
    return render_template('admin/dashboard.html', title='Dashboard Admin', user_count=user_count, setting=setting)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', title='Manajemen User', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username atau email sudah terdaftar.', 'danger')
            return render_template('admin/add_user.html', title='Tambah User', form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='petugas'  # default role diubah menjadi petugas
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User petugas berhasil ditambahkan.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/add_user.html', title='Tambah User Petugas', form=form)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin' and user.id != current_user.id: # Admin tidak bisa edit admin lain
        flash('Anda tidak dapat mengedit akun admin lain.', 'danger')
        return redirect(url_for('admin.users'))
    # Jika admin mencoba mengedit dirinya sendiri dan mengubah role, bisa ditambahkan validasi di sini

    form = EditUserForm(obj=user) # Pre-populate form dengan data user

    if form.validate_on_submit():
        # Cek apakah email diubah dan sudah ada yang pakai (kecuali email user itu sendiri)
        if form.email.data != user.email:
            existing_email = User.query.filter(User.email == form.email.data, User.id != user.id).first()
            if existing_email:
                flash('Email tersebut sudah digunakan oleh user lain.', 'danger')
                return render_template('admin/edit_user.html', title='Edit User', form=form, user=user)
        user.email = form.email.data
        if form.password.data: # Jika password diisi, maka diubah
            user.set_password(form.password.data)
        db.session.commit()
        flash('Data user berhasil diperbarui.', 'success')
        return redirect(url_for('admin.users'))
    elif request.method == 'GET':
        form.email.data = user.email # Pastikan email terisi saat GET
    return render_template('admin/edit_user.html', title=f'Edit User: {user.username}', form=form, user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Tidak dapat menghapus user admin.', 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash('User berhasil dihapus.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    form = SettingForm()
    setting = Setting.query.first()
    if not setting:
        setting = Setting(passing_grade=10, kuota=50)
        db.session.add(setting)
        db.session.commit()

    if form.validate_on_submit():
        setting.passing_grade = form.passing_grade.data
        setting.kuota = form.kuota.data
        try:
            db.session.commit()
            flash('Pengaturan berhasil disimpan.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menyimpan pengaturan: {str(e)}', 'danger')

    form.passing_grade.data = setting.passing_grade
    form.kuota.data = setting.kuota

    return render_template('admin/settings.html', title='Pengaturan Sistem', form=form)
