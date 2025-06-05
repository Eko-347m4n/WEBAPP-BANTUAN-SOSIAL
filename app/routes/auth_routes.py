from flask import Blueprint, render_template, redirect, url_for, flash
# from flask_login import login_user, logout_user, login_required, current_user
# from app.models import User # Akan dibuat nanti
# from app import db # Akan diaktifkan nanti
from app.forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    form = LoginForm()
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/register')
def register():
    form = RegistrationForm()
    return render_template('register.html', title='Register', form=form)
