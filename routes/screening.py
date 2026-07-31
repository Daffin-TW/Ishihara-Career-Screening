"""
routes/screening.py – Route untuk form skrining dan hasil prediksi
"""
import os
import json
import logging
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, jsonify,
    current_app, send_from_directory
)
from utils.preprocessor import (
    get_ishihara_images,
    calculate_ishihara_score,
    calculate_color_ability,
    calculate_riasec,
    build_feature_dict,
    build_summary,
    CAREER_CHOICES,
    PENDIDIKAN_CHOICES,
    JK_CHOICES,
)
from utils.predictor import predict, is_model_loaded, get_feature_list, load_model

logger = logging.getLogger(__name__)

screening_bp = Blueprint("screening", __name__)


# ── Lazy load model saat pertama kali dibutuhkan ─────────────────────────────

def _ensure_model_loaded():
    """Pastikan model sudah dimuat; muat jika belum."""
    if not is_model_loaded():
        try:
            load_model(current_app.config)
        except Exception as e:
            logger.error(f"Gagal memuat model: {e}")


# ── Helper: ambil daftar gambar Ishihara ────────────────────────────────────

def _get_ishihara():
    return get_ishihara_images(current_app.config["ISHIHARA_DIR"])


# ────────────────────────────────────────────────────────────────────────────────
# ROUTE: Halaman Form (GET)
# ────────────────────────────────────────────────────────────────────────────────

@screening_bp.route("/screening")
def form():
    """Tampilkan halaman multi-step form skrining."""
    _ensure_model_loaded()

    ishihara_images = _get_ishihara()
    ishihara_json   = json.dumps(ishihara_images)   # Kirim ke JS

    return render_template(
        "form.html",
        ishihara_images = ishihara_images,
        ishihara_json   = ishihara_json,
        career_choices  = CAREER_CHOICES,
        pendidikan_opts = PENDIDIKAN_CHOICES,
        jk_opts         = JK_CHOICES,
        model_loaded    = is_model_loaded(),
    )


# ────────────────────────────────────────────────────────────────────────────────
# ROUTE: Proses Prediksi (POST)
# ────────────────────────────────────────────────────────────────────────────────

@screening_bp.route("/predict", methods=["POST"])
def predict_route():
    """
    Terima data form, lakukan preprocessing & prediksi, simpan ke session,
    lalu redirect ke halaman hasil.
    """
    _ensure_model_loaded()

    try:
        form_data = request.form.to_dict()

        # ── 1. Ambil daftar gambar Ishihara & jawaban benar ──────────────────
        ishihara_images  = _get_ishihara()
        correct_answers  = [img["answer"] for img in ishihara_images]
        user_answers     = [
            form_data.get(f"ishihara_{img['no']}", "0")
            for img in ishihara_images
        ]

        # ── 2. Hitung skor Ishihara ──────────────────────────────────────────
        ishihara_result  = calculate_ishihara_score(user_answers, correct_answers)
        form_data["ishihara_percentage"] = ishihara_result["percentage"]
        form_data["ishihara_severity"]   = ishihara_result["severity"]

        # ── 3. Hitung kemampuan identifikasi warna ───────────────────────────
        color_scores = {
            "merah" : form_data.get("color_merah",  3),
            "hijau" : form_data.get("color_hijau",  3),
            "biru"  : form_data.get("color_biru",   3),
            "kuning": form_data.get("color_kuning", 3),
            "orange": form_data.get("color_orange", 3),
            "ungu"  : form_data.get("color_ungu",   3),
            "coklat": form_data.get("color_coklat", 3),
        }
        color_ability = calculate_color_ability(color_scores)
        form_data["color_ability_total"] = color_ability

        # ── 4. Hitung skor RIASEC ────────────────────────────────────────────
        riasec_input = {}
        for dim in ["R", "I", "A", "S", "E", "C"]:
            scores = [form_data.get(f"riasec_{dim}_{i}", 3) for i in range(1, 6)]
            riasec_input[dim] = scores

        riasec_scores = calculate_riasec(riasec_input)
        form_data.update(riasec_scores)   # Tambahkan R,I,A,S,E,C ke form_data

        # ── 5. Bangun feature dict (urutan sesuai feature_list.json) ─────────
        feature_list = get_feature_list()
        feature_dict = build_feature_dict(form_data, feature_list)

        # ── 6. Prediksi ──────────────────────────────────────────────────────
        result = predict(feature_dict)

        # ── 7. Bangun ringkasan jawaban ───────────────────────────────────────
        summary = build_summary(form_data, ishihara_images)

        # ── 8. Simpan ke session & redirect ke result ────────────────────────
        session["prediction"]     = result
        session["ishihara_result"] = ishihara_result
        session["summary"]        = summary

        flash("Prediksi berhasil dilakukan!", "success")
        return redirect(url_for("screening.result"))

    except RuntimeError as e:
        logger.error(f"Runtime error saat prediksi: {e}")
        flash(f"⚠️ Model belum tersedia: {e}", "danger")
        return redirect(url_for("screening.form"))

    except Exception as e:
        logger.exception(f"Error tidak terduga saat prediksi: {e}")
        flash(f"❌ Terjadi kesalahan: {e}", "danger")
        return redirect(url_for("screening.form"))


# ────────────────────────────────────────────────────────────────────────────────
# ROUTE: Halaman Hasil
# ────────────────────────────────────────────────────────────────────────────────

@screening_bp.route("/result")
def result():
    """Tampilkan dashboard hasil prediksi."""
    prediction      = session.get("prediction")
    ishihara_result  = session.get("ishihara_result")
    summary         = session.get("summary")

    if not prediction:
        flash("Belum ada data prediksi. Silakan lakukan skrining terlebih dahulu.", "warning")
        return redirect(url_for("screening.form"))

    # Warna badge berdasarkan label prediksi
    label = prediction.get("label", "")
    if "Tidak" in label:
        badge_class = "danger"
        badge_icon  = "❌"
    elif "Kurang" in label:
        badge_class = "warning"
        badge_icon  = "⚠️"
    else:
        badge_class = "success"
        badge_icon  = "✅"

    # Warna severity
    severity       = ishihara_result.get("severity", "Normal")
    severity_class = {
        "Normal": "success",
        "Ringan": "info",
        "Sedang": "warning",
        "Berat" : "danger",
    }.get(severity, "secondary")

    return render_template(
        "result.html",
        prediction      = prediction,
        ishihara_result  = ishihara_result,
        summary         = summary,
        badge_class     = badge_class,
        badge_icon      = badge_icon,
        severity_class  = severity_class,
    )


# ────────────────────────────────────────────────────────────────────────────────
# ROUTE: Gambar Ishihara (static serve)
# ────────────────────────────────────────────────────────────────────────────────

@screening_bp.route("/ishihara/<filename>")
def ishihara_image(filename):
    """Sajikan gambar Ishihara dari folder ishihara."""
    search_dirs = [
        current_app.config.get("ISHIHARA_DIR"),
        os.path.join(current_app.config["BASE_DIR"], "ishihara"),
        os.path.join(current_app.config["BASE_DIR"], "src", "img", "ishihara"),
    ]
    for d in search_dirs:
        if d and os.path.isdir(d):
            full_path = os.path.join(d, filename)
            if os.path.isfile(full_path):
                return send_from_directory(os.path.abspath(d), filename)

    return ("Gambar tidak ditemukan", 404)


# ────────────────────────────────────────────────────────────────────────────────
# ROUTE: API – Info gambar Ishihara (JSON)
# ────────────────────────────────────────────────────────────────────────────────

@screening_bp.route("/api/ishihara")
def api_ishihara():
    """Kembalikan daftar gambar Ishihara sebagai JSON."""
    images = _get_ishihara()
    # Hapus kunci 'answer' sebelum dikirim ke klien (jangan bocorkan jawaban)
    safe = [{"no": img["no"], "filename": img["filename"]} for img in images]
    return jsonify(safe)
