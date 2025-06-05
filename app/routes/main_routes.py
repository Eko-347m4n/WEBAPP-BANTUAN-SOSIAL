from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required # Hanya bisa diakses setelah login
def index():
    return render_template('index.html', title='Halaman Utama')