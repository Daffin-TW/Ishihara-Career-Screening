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

# Mapping: label pilihan karier → (job_zone, color_req_score)
# ColorReq adalah O*NET Visual Color Discrimination Level score (0–100)
CAREER_MAPPING = {
    # ── Kesehatan ──────────────────────────────────────────────────────────────
    "[Kesehatan] Kedokteran"              : ("5", 37),
    "[Kesehatan] Keperawatan"             : ("4", 41),
    "[Kesehatan] Farmasi"                 : ("5", 41),
    "[Kesehatan] Laboratorium"            : ("4", 52),

    # ── Teknik ─────────────────────────────────────────────────────────────────
    "[Teknik] Teknik Mesin"               : ("4", 41),
    "[Teknik] Teknik Elektro"             : ("4", 43),
    "[Teknik] Teknik Sipil"               : ("4", 37),
    "[Teknik] Teknik Industri"            : ("4", 39),

    # ── Teknologi Informasi ────────────────────────────────────────────────────
    "[Teknologi Informasi] Informatika / Ilmu Komputer" : ("4", 29),
    "[Teknologi Informasi] Data Science / Kecerdasan Buatan": ("4", 16),

    # ── Seni & Kreatif ─────────────────────────────────────────────────────────
    "[Seni & Kreatif] Desain Grafis"      : ("4", 54),
    "[Seni & Kreatif] Multimedia / Film"  : ("3", 46),
    "[Seni & Kreatif] Seni Rupa"          : ("3", 75),
    "[Seni & Kreatif] Make Up Artist"     : ("3", 63),
    "[Seni & Kreatif] Tata Boga"           : ("3", 43),

    # ── Sosial & Humaniora ─────────────────────────────────────────────────────
    "[Sosial & Humaniora] Pendidikan / Mengajar" : ("4", 29),
    "[Sosial & Humaniora] Psikologi"             : ("5", 29),
    "[Sosial & Humaniora] Hukum"                 : ("5", 21),
    "[Sosial & Humaniora] Ilmu Komunikasi"     : ("4", 29),

    # ── Bisnis & Administrasi ──────────────────────────────────────────────────
    "[Bisnis & Administrasi] Bisnis / Manajemen" : ("4", 25),
    "[Bisnis & Administrasi] Akuntansi"           : ("4", 23),
    "[Bisnis & Administrasi] Administrasi"        : ("3", 21),

    # ── Keselamatan & Transportasi ────────────────────────────────────────────
    "[Keselamatan & Transportasi] Penerbangan"          : ("4", 48),
    "[Keselamatan & Transportasi] Kelautan"             : ("3", 43),
    "[Keselamatan & Transportasi] Transportasi / Logistik": ("4", 32),
    "[Keselamatan & Transportasi] Kepolisian"           : ("3", 41),
    "[Keselamatan & Transportasi] TNI / Militer"        : ("3", 41),
    "[Keselamatan & Transportasi] Pemadam Kebakaran"    : ("3", 50),
}

# Daftar pilihan karier untuk dropdown (tampilan)
CAREER_CHOICES = list(CAREER_MAPPING.keys())

# Pilihan pendidikan
PENDIDIKAN_CHOICES = ["SMA / SMK / Sederajat", "Diploma (D1-D4)", "Sarjana (S1)", "Pascasarjana (S2/S3)"]

# Pilihan jenis kelamin
JK_CHOICES = [("Laki-laki", "Laki-laki"), ("Perempuan", "Perempuan")]


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
    Konversi label karier (dari dropdown) ke:
    - job_zone (str)
    - color_req (int) – O*NET Color Discrimination Level

    Parameters
    ----------
    career_label : str – pilihan dari dropdown (misal: "[Kesehatan] Kedokteran")

    Returns
    -------
    tuple: (job_zone: str, color_req: int)
    """
    if career_label in CAREER_MAPPING:
        return CAREER_MAPPING[career_label]
    else:
        logger.warning(
            f"Karier '{career_label}' tidak ditemukan di mapping. "
            f"Menggunakan default: zone=4, color_req=25"
        )
        return ("4", 25)


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
    career_label           = form_data.get("karier", "")
    job_zone, color_req    = resolve_career(career_label)

    # ── Data Diri ─────────────────────────────────────────────────────────────
    usia             = str(form_data.get("usia", "17-25 tahun"))
    jk               = str(form_data.get("jk", "Laki-laki"))
    pendidikan       = str(form_data.get("pendidikan", "SMA / SMK / Sederajat"))
    riwayat_keluarga = str(form_data.get("riwayat_keluarga", "Tidak"))
    peng_kacamata    = str(form_data.get("peng_kacamata", "Tidak"))
    kondisi_mata     = str(form_data.get("kondisi_mata", "Tidak ada"))

    # ── Bangun raw dict sesuai nama kolom training data (17 feature) ──────────
    raw = {
        "Usia"                            : usia,
        "JK"                              : jk,
        "Pendidikan"                      : pendidikan,
        "Riwayat_Keluarga"               : riwayat_keluarga,
        "Persentase nilai identifikasi warna": percentage,
        "Kemampuan identifikasi Warna"    : color_ability,
        "R"                               : r_score,
        "I"                               : i_score,
        "A"                               : a_score,
        "S"                               : s_score,
        "E"                               : e_score,
        "C"                               : c_score,
        "Karier"                          : career_label,
        "JobZone"                         : job_zone,
        "ColorReq"                        : color_req,
        "Peng. Kacamata"                  : peng_kacamata,
        "Kondisi Mata"                    : kondisi_mata,
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
        "jk"              : form_data.get("jk", "Laki-laki"),
        "pendidikan"      : form_data.get("pendidikan", "-"),
        "riwayat_keluarga": form_data.get("riwayat_keluarga", "-"),
        "peng_kacamata"   : form_data.get("peng_kacamata", "Tidak"),
        "kondisi_mata"    : form_data.get("kondisi_mata", "Tidak ada"),
        "ishihara_detail" : ishihara_detail,
        "color_detail"    : color_detail,
        "riasec"          : {
            dim: int(form_data.get(dim, 15))
            for dim in ["R", "I", "A", "S", "E", "C"]
        },
        "karier_pilihan"  : form_data.get("karier", "-"),
    }
