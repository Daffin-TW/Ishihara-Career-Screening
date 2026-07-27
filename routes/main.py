"""
routes/main.py – Route untuk halaman utama (Home)
"""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    """Halaman utama / landing page."""
    return render_template("home.html")
