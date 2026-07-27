"""
utils/preprocessor.py – Preprocessing input pengguna sebelum inferensi model
Mengikuti struktur dummy_data.csv dan feature_list.json
"""
import os
import re
import logging

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# KONSTANTA
# ────────────────────────────────────────────────────────────────────────────────

# Total gambar Ishihara yang tersedia
TOTAL_ISHIHARA = 11

# Mapping: label pilihan karier (questions.txt) → nama karier di training data
# Urutan: (display_label, model_career, job_zone, color_req)
CAREER_MAPPING = {
    # ── Kesehatan ──────────────────────────────────────────────────────────────
    "[Kesehatan] Kedokteran"              : ("Dokter",          5, "Tinggi"),
    "[Kesehatan] Keperawatan"             : ("Perawat",         4, "Sedang"),
    "[Kesehatan] Farmasi"                 : ("Dokter",          5, "Tinggi"),
    "[Kesehatan] Laboratorium"            : ("Dokter",          5, "Tinggi"),

    # ── Teknik ─────────────────────────────────────────────────────────────────
    "[Teknik] Teknik Mesin"               : ("Programmer",      4, "Rendah"),
    "[Teknik] Teknik Elektro"             : ("Programmer",      4, "Rendah"),
    "[Teknik] Teknik Sipil"               : ("Programmer",      4, "Rendah"),
    "[Teknik] Teknik Industri"            : ("Programmer",      4, "Rendah"),

    # ── Teknologi Informasi ────────────────────────────────────────────────────
    "[Teknologi Informasi] Informatika / Ilmu Komputer" : ("Programmer",   4, "Rendah"),
    "[Teknologi Informasi] Data Science / Kecerdasan Buatan": ("Data Analyst", 4, "Rendah"),

    # ── Seni & Kreatif ─────────────────────────────────────────────────────────
    "[Seni & Kreatif] Desain Grafis"      : ("Desainer Grafis", 3, "Sedang"),
    "[Seni & Kreatif] Multimedia / Film"  : ("Desainer Grafis", 3, "Sedang"),
    "[Seni & Kreatif] Seni Rupa"          : ("Make Up Artist",  2, "Tinggi"),

    # ── Sosial & Humaniora ─────────────────────────────────────────────────────
    "[Sosial & Humaniora] Pendidikan / Mengajar" : ("Guru",    4, "Rendah"),
    "[Sosial & Humaniora] Psikologi"             : ("Guru",    4, "Rendah"),
    "[Sosial & Humaniora] Hukum"                 : ("Polisi",  3, "Sedang"),

    # ── Bisnis & Administrasi ──────────────────────────────────────────────────
    "[Bisnis & Administrasi] Bisnis / Manajemen" : ("Akuntan", 4, "Rendah"),
    "[Bisnis & Administrasi] Akuntansi"           : ("Akuntan", 4, "Rendah"),
    "[Bisnis & Administrasi] Administrasi"        : ("Akuntan", 4, "Rendah"),

    # ── Keselamatan & Transportasi ────────────────────────────────────────────
    "[Keselamatan & Transportasi] Penerbangan"          : ("Pilot",  5, "Tinggi"),
    "[Keselamatan & Transportasi] Kelautan"             : ("Pilot",  5, "Tinggi"),
    "[Keselamatan & Transportasi] Transportasi / Logistik": ("Polisi", 3, "Sedang"),
    "[Keselamatan & Transportasi] Kepolisian"           : ("Polisi", 3, "Sedang"),
    "[Keselamatan & Transportasi] TNI / Militer"        : ("Polisi", 3, "Sedang"),
    "[Keselamatan & Transportasi] Pemadam Kebakaran"    : ("Polisi", 3, "Sedang"),
}

# Daftar pilihan karier untuk dropdown (tampilan)
CAREER_CHOICES = list(CAREER_MAPPING.keys())

# Pilihan pendidikan
PENDIDIKAN_CHOICES = ["SMA", "D3", "S1", "S2"]

# Pilihan jenis kelamin
JK_CHOICES = [("L", "Laki-laki"), ("P", "Perempuan")]


# ────────────────────────────────────────────────────────────────────────────────
# ISHIHARA
# ────────────────────────────────────────────────────────────────────────────────

def get_ishihara_images(ishihara_dir: str) -> list[dict]:
    """
    Baca folder ishihara dan ekstrak nomor + jawaban benar dari nama file.

    Format file: `nomor-jawaban.png`  (contoh: 1-12.png)

    Returns
    -------
    list of dict: [{'no': int, 'filename': str, 'answer': int}, ...]
    """
    images = []

    if not os.path.exists(ishihara_dir):
        logger.error(f"Folder Ishihara tidak ditemukan: {ishihara_dir}")
        return images

    for fname in sorted(os.listdir(ishihara_dir)):
        if not fname.lower().endswith(".png"):
            continue

        # Ekstrak nomor dan jawaban dari nama file (pola: N-ANSWER.png atau N_ANSWER.png)
        match = re.match(r"^(\d+)[-_](\d+)\.png$", fname, re.IGNORECASE)
        if match:
            no     = int(match.group(1))
            answer = int(match.group(2))
            images.append({"no": no, "filename": fname, "answer": answer})
        else:
            logger.warning(f"Format nama file tidak sesuai: {fname}")

    # Urutkan berdasarkan nomor gambar
    images.sort(key=lambda x: x["no"])
    return images


def calculate_ishihara_score(user_answers: list, correct_answers: list) -> dict:
    """
    Hitung skor tes Ishihara.

    Parameters
    ----------
    user_answers    : list[int or str] – jawaban pengguna per gambar
    correct_answers : list[int]        – jawaban benar per gambar

    Returns
    -------
    dict: {
      'correct'     : int,   # Jumlah benar
      'wrong'       : int,   # Jumlah salah
      'total'       : int,   # Total gambar
      'percentage'  : float, # Persentase identifikasi (0–100)
      'severity'    : str,   # Tingkat keparahan
    }
    """
    total   = len(correct_answers)
    correct = 0

    for user_ans, correct_ans in zip(user_answers, correct_answers):
        try:
            if int(str(user_ans).strip()) == correct_ans:
                correct += 1
        except (ValueError, TypeError):
            pass  # Jawaban tidak valid dianggap salah

    wrong      = total - correct
    percentage = round((correct / total) * 100, 2) if total > 0 else 0.0
    severity   = _determine_severity(percentage)

    return {
        "correct"   : correct,
        "wrong"     : wrong,
        "total"     : total,
        "percentage": percentage,
        "severity"  : severity,
    }


def _determine_severity(percentage: float) -> str:
    """
    Tentukan tingkat keparahan buta warna berdasarkan persentase identifikasi.

    Thresholds didasarkan pada distribusi dummy_data.csv:
    - Normal  : >= 85.71%
    - Ringan  : 71.43% – 85.71%
    - Sedang  : 35.71% – 71.43%
    - Berat   : < 35.71%
    """
    if percentage >= 85.71:
        return "Normal"
    elif percentage >= 71.43:
        return "Ringan"
    elif percentage >= 35.71:
        return "Sedang"
    else:
        return "Berat"


# ────────────────────────────────────────────────────────────────────────────────
# KEMAMPUAN IDENTIFIKASI WARNA
# ────────────────────────────────────────────────────────────────────────────────

def calculate_color_ability(color_scores: dict) -> int:
    """
    Hitung total skor kemampuan identifikasi warna (7 warna, skala 1–5).

    Parameters
    ----------
    color_scores : dict – {'merah': int, 'hijau': int, ..., 'coklat': int}

    Returns
    -------
    int – total skor (7–35)
    """
    COLOR_KEYS = ["merah", "hijau", "biru", "kuning", "orange", "ungu", "coklat"]
    total = 0
    for key in COLOR_KEYS:
        try:
            val = int(color_scores.get(key, 3))
            total += max(1, min(5, val))  # Clamp ke 1–5
        except (ValueError, TypeError):
            total += 3  # Default netral
    return total


# ────────────────────────────────────────────────────────────────────────────────
# RIASEC
# ────────────────────────────────────────────────────────────────────────────────

def calculate_riasec(riasec_scores: dict) -> dict:
    """
    Hitung total skor per dimensi RIASEC (5 soal per dimensi, skala 1–5).

    Parameters
    ----------
    riasec_scores : dict – {'R': [s1,s2,s3,s4,s5], 'I': [...], ...}

    Returns
    -------
    dict – {'R': int, 'I': int, 'A': int, 'S': int, 'E': int, 'C': int}
    """
    dimensions = ["R", "I", "A", "S", "E", "C"]
    result = {}

    for dim in dimensions:
        scores = riasec_scores.get(dim, [3, 3, 3, 3, 3])
        total  = 0
        for s in scores:
            try:
                val = int(s)
                total += max(1, min(5, val))
            except (ValueError, TypeError):
                total += 3
        result[dim] = total

    return result


# ────────────────────────────────────────────────────────────────────────────────
# KARIER
# ────────────────────────────────────────────────────────────────────────────────

def resolve_career(career_label: str) -> tuple:
    """
    Konversi label karier (dari questions.txt) ke:
    - nama karier untuk model (sesuai training data)
    - JobZone
    - ColorReq

    Parameters
    ----------
    career_label : str – pilihan dari dropdown (misal: "[Kesehatan] Kedokteran")

    Returns
    -------
    tuple: (model_career: str, job_zone: int, color_req: str)
    """
    if career_label in CAREER_MAPPING:
        return CAREER_MAPPING[career_label]
    else:
        logger.warning(
            f"Karier '{career_label}' tidak ditemukan di mapping. "
            f"Menggunakan default: Programmer."
        )
        return ("Programmer", 4, "Rendah")


# ── Internal helper ─────────────────────────────────────────────────────────

def _safe_int(val, default=0):
    """Konversi value ke int secara aman (handle string dari form)."""
    try:
        return int(float(str(val).replace(",", ".")))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    """Konversi value ke float secara aman (handle string & comma decimal)."""
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return default


def build_feature_dict(form_data: dict, feature_list: list) -> dict:
    """
    Bangun dictionary fitur yang siap dikirim ke model.
    Urutan fitur IDENTIK dengan feature_list.json.

    Parameters
    ----------
    form_data    : dict – semua data mentah dari form HTML
    feature_list : list – urutan fitur dari feature_list.json

    Returns
    -------
    dict – feature dict dengan kunci sesuai feature_list
    """
    # ── Ishihara Score ────────────────────────────────────────────────────────
    percentage = float(form_data.get("ishihara_percentage", 0))
    severity   = form_data.get("ishihara_severity", "Normal")

    # ── Kemampuan Identifikasi Warna ──────────────────────────────────────────
    color_ability = int(form_data.get("color_ability_total", 21))

    # ── RIASEC ────────────────────────────────────────────────────────────────
    r_score = int(form_data.get("R", 15))
    i_score = int(form_data.get("I", 15))
    a_score = int(form_data.get("A", 15))
    s_score = int(form_data.get("S", 15))
    e_score = int(form_data.get("E", 15))
    c_score = int(form_data.get("C", 15))

    # ── Karier ────────────────────────────────────────────────────────────────
    career_label                     = form_data.get("karier", "")
    model_career, job_zone, color_req = resolve_career(career_label)

    # ── Data Diri ─────────────────────────────────────────────────────────────
    usia              = int(form_data.get("usia", 20))
    jk                = str(form_data.get("jk", "L"))
    pendidikan        = str(form_data.get("pendidikan", "SMA"))
    riwayat_keluarga  = str(form_data.get("riwayat_keluarga", "Tidak"))
    alat_bantu        = int(form_data.get("alat_bantu", 0))
    penyakit_mata     = int(form_data.get("penyakit_mata", 0))

    # ── Bangun raw dict sesuai nama kolom training data ───────────────────────
    raw = {
        "Usia"                            : usia,
        "JK"                              : jk,
        "Pendidikan"                      : pendidikan,
        "Riwayat_Keluarga"               : riwayat_keluarga,
        "Persentase nilai identifikasi warna": percentage,
        "Tingkat Keparahan"               : severity,
        "Kemampuan identifikasi Warna"    : color_ability,
        "R"                               : r_score,
        "I"                               : i_score,
        "A"                               : a_score,
        "S"                               : s_score,
        "E"                               : e_score,
        "C"                               : c_score,
        "Alat_Bantu_Penglihatan"          : alat_bantu,
        "Penyakit_Mata_Lain"              : penyakit_mata,
        "Karier"                          : model_career,
        "JobZone"                         : job_zone,
        "ColorReq"                        : color_req,
    }

    # ── Susun ulang sesuai feature_list (PENTING!) ────────────────────────────
    feature_dict = {}
    missing = []
    for feat in feature_list:
        if feat in raw:
            feature_dict[feat] = raw[feat]
        else:
            missing.append(feat)
            feature_dict[feat] = 0  # Fallback

    if missing:
        logger.warning(f"Fitur berikut tidak ditemukan di raw dict: {missing}")

    logger.info(f"Feature dict final: {feature_dict}")
    return feature_dict


# ────────────────────────────────────────────────────────────────────────────────
# SUMMARY (untuk ditampilkan di halaman result)
# ────────────────────────────────────────────────────────────────────────────────

def build_summary(form_data: dict, ishihara_images: list) -> dict:
    """
    Bangun ringkasan jawaban pengguna untuk ditampilkan di halaman hasil.
    """
    COLOR_LABELS = {
        "merah" : "Merah",
        "hijau" : "Hijau",
        "biru"  : "Biru",
        "kuning": "Kuning",
        "orange": "Orange",
        "ungu"  : "Ungu",
        "coklat": "Coklat",
    }
    SCALE_LABELS = {1: "Sangat Sulit", 2: "Sulit", 3: "Netral", 4: "Mudah", 5: "Sangat Mudah"}
    RIASEC_LABELS = {
        1: "Sangat Tidak Sesuai", 2: "Tidak Sesuai", 3: "Netral",
        4: "Sesuai", 5: "Sangat Sesuai"
    }

    # Ishihara detail
    ishihara_detail = []
    for img in ishihara_images:
        no       = img["no"]
        user_ans = form_data.get(f"ishihara_{no}", "-")
        correct  = img["answer"]
        try:
            is_correct = int(str(user_ans).strip()) == correct
        except Exception:
            is_correct = False
        ishihara_detail.append({
            "no"        : no,
            "user_ans"  : user_ans,
            "correct"   : correct,
            "is_correct": is_correct,
        })

    # Kemampuan warna detail
    color_detail = []
    for key, label in COLOR_LABELS.items():
        val = int(form_data.get(f"color_{key}", 3))
        color_detail.append({
            "warna": label,
            "skor" : val,
            "label": SCALE_LABELS.get(val, str(val)),
        })

    return {
        "nama"            : form_data.get("nama", "-"),
        "usia"            : form_data.get("usia", "-"),
        "jk"              : "Laki-laki" if form_data.get("jk") == "L" else "Perempuan",
        "pendidikan"      : form_data.get("pendidikan", "-"),
        "riwayat_keluarga": form_data.get("riwayat_keluarga", "-"),
        "alat_bantu"      : "Ya" if int(form_data.get("alat_bantu", 0)) else "Tidak",
        "penyakit_mata"   : "Ya" if int(form_data.get("penyakit_mata", 0)) else "Tidak",
        "ishihara_detail" : ishihara_detail,
        "color_detail"    : color_detail,
        "riasec"          : {
            dim: int(form_data.get(dim, 15))
            for dim in ["R", "I", "A", "S", "E", "C"]
        },
        "karier_pilihan"  : form_data.get("karier", "-"),
    }
