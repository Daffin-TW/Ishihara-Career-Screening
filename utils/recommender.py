"""
utils/recommender.py – Rekomendasi pekerjaan berbasis RIASEC O*NET.

Alur dipisah tegas:
  1. RIASEC  -> ranking okupasi berdasarkan kemiripan profil minat (utama).
  2. Warna   -> status kelayakan per okupasi (informasi tambahan), TIDAK
                mengubah urutan ranking RIASEC.

Sumber data:
  - src/data/occupation_riasec.csv  : O*NET Career Interest Types (OI 1-7, IH)
  - src/data/occupation_importance.csv : tuntutan Visual Color Discrimination
  - src/data/all_occupations.csv    : master Job Zone / nama okupasi
"""
import csv
import logging
import os

logger = logging.getLogger(__name__)

RIASEC_DIMENSIONS = ("R", "I", "A", "S", "E", "C")
RIASEC_NAMES = {
    "R": "Realistic",
    "I": "Investigative",
    "A": "Artistic",
    "S": "Social",
    "E": "Enterprising",
    "C": "Conventional",
}

# Ambang "minat selaras" untuk label kualitatif (bukan filter).
RIASEC_ALIGNED_FIT = 65.0
# Ambang minimum similarity agar okupasi layak tampil di daftar utama.
RIASEC_MIN_SIMILARITY = 50.0

_TRANSLATION_MAP = None


def get_occupation_translation(name: str) -> str:
    """Terjemahkan nama okupasi bahasa Inggris ke bahasa Indonesia."""
    global _TRANSLATION_MAP
    if _TRANSLATION_MAP is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "src", "data", "occupations_id.json",
        )
        if os.path.exists(path):
            try:
                import json
                with open(path, encoding="utf-8") as f:
                    _TRANSLATION_MAP = json.load(f)
            except Exception as e:
                logger.error(f"Gagal membaca occupations_id.json: {e}")
                _TRANSLATION_MAP = {}
        else:
            _TRANSLATION_MAP = {}
    return _TRANSLATION_MAP.get(name, name)


# ── Kemiripan profil ──────────────────────────────────────────────────────────

def pearson_similarity(user_scores: dict, occupation_scores: dict):
    """
    Pearson correlation 6 dimensi, dipetakan ke 0-100: ((r + 1) / 2) * 100.

    Mengukur kemiripan BENTUK pola minat, bukan besar skor. Mengembalikan
    None bila salah satu profil datar (varians 0) karena r tak terdefinisi.
    """
    u = [float(user_scores.get(d, 0) or 0) for d in RIASEC_DIMENSIONS]
    o = [float(occupation_scores.get(d, 0) or 0) for d in RIASEC_DIMENSIONS]

    mean_u = sum(u) / len(u)
    mean_o = sum(o) / len(o)
    uc = [v - mean_u for v in u]
    oc = [v - mean_o for v in o]

    denom = (sum(v * v for v in uc) ** 0.5) * (sum(v * v for v in oc) ** 0.5)
    if denom == 0:
        return None

    r = sum(a * b for a, b in zip(uc, oc)) / denom
    return round(((r + 1.0) / 2.0) * 100.0, 2)


def cosine_similarity(user_scores: dict, occupation_scores: dict):
    """Cosine similarity 6 dimensi pada skala 0-100. Pembanding evaluasi."""
    u = [float(user_scores.get(d, 0) or 0) for d in RIASEC_DIMENSIONS]
    o = [float(occupation_scores.get(d, 0) or 0) for d in RIASEC_DIMENSIONS]
    norm_u = sum(v * v for v in u) ** 0.5
    norm_o = sum(v * v for v in o) ** 0.5
    if norm_u == 0 or norm_o == 0:
        return None
    return round(100.0 * sum(a * b for a, b in zip(u, o)) / (norm_u * norm_o), 2)


def dominant_dimensions(scores: dict, top_n: int = 2):
    """Kode dimensi dengan skor tertinggi (tie dipecah urut R,I,A,S,E,C)."""
    ordered = sorted(
        RIASEC_DIMENSIONS,
        key=lambda d: (-float(scores.get(d, 0) or 0), RIASEC_DIMENSIONS.index(d)),
    )
    return ordered[:top_n]


def is_flat_profile(scores: dict) -> bool:
    values = {float(scores.get(d, 0) or 0) for d in RIASEC_DIMENSIONS}
    return len(values) <= 1


# ── Pemuatan & integrasi data ─────────────────────────────────────────────────

def _read_csv(path):
    if not path or not os.path.exists(path):
        logger.error(f"Dataset tidak ditemukan: {path}")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _to_float(value):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_job_zone(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return max(int(part) for part in raw.split("-"))
    except ValueError:
        return None


def load_occupations(riasec_path, importance_path=None, master_path=None) -> list:
    """
    Gabungkan dataset okupasi memakai kode O*NET-SOC (bukan nama).

    Returns list of dict:
        {code, occupation, category, R..C, ih:[..], job_zone,
         color_importance, color_level, has_full_riasec}
    """
    riasec_rows = _read_csv(riasec_path)
    importance = {r.get("Code", "").strip(): r for r in _read_csv(importance_path)}
    master = {r.get("Code", "").strip(): r for r in _read_csv(master_path)}

    occupations = []
    seen_codes = set()
    seen_names = set()
    skipped_incomplete = 0
    duplicates = 0

    for row in riasec_rows:
        code = (row.get("Code") or "").strip()
        name = (row.get("Occupation") or "").strip().strip('"')
        if not code or not name:
            continue
        if code in seen_codes:
            duplicates += 1
            continue

        scores = {d: _to_float(row.get(d)) for d in RIASEC_DIMENSIONS}
        if any(v is None for v in scores.values()):
            skipped_incomplete += 1
            continue
        if all(v == 0 for v in scores.values()):
            skipped_incomplete += 1
            continue

        name_key = name.lower()
        if name_key in seen_names:
            duplicates += 1
            continue
        seen_names.add(name_key)
        seen_codes.add(code)

        color = importance.get(code, {})
        master_row = master.get(code, {})
        category = (row.get("OccupationCategory") or "").strip() or (
            color.get("OccupationCategory") or ""
        ).strip()
        # Bersihkan kategori kesehatan yang salah label (bukan kode 29/31)
        if category.startswith("[Kesehatan]") and not code.startswith(("29", "31")):
            category = ""

        occupations.append({
            "code": code,
            "occupation": name,
            "occupation_id": get_occupation_translation(name),
            "category": category,
            "scores": {d: scores[d] for d in RIASEC_DIMENSIONS},
            "ih": [d for d in (
                (row.get("IH1") or "").strip(),
                (row.get("IH2") or "").strip(),
                (row.get("IH3") or "").strip(),
            ) if d in RIASEC_DIMENSIONS],
            "job_zone": _parse_job_zone(master_row.get("Job Zone")) or _parse_job_zone(color.get("Job Zone")),
            "color_importance": _to_float(color.get("Importance")),
            "color_level": _to_float(color.get("Level")),
        })

    if duplicates:
        logger.warning(f"Lewati {duplicates} okupasi duplikat.")
    if skipped_incomplete:
        logger.warning(f"Lewati {skipped_incomplete} okupasi dengan profil RIASEC tidak lengkap.")
    logger.info(f"Memuat {len(occupations)} okupasi untuk rekomendasi.")
    return occupations


# ── Status warna (informasi terpisah, bukan filter ranking) ───────────────────

def color_status(occupation: dict, user_percentage) -> dict:
    """
    Bandingkan tuntutan warna okupasi dengan skor pengguna.
    Status: 'meets' | 'below' | 'unknown'. Tidak memengaruhi ranking RIASEC.
    """
    requirement = occupation.get("color_importance")
    if requirement is None or user_percentage is None:
        return {"status": "unknown", "requirement": None, "gap": None}

    gap = round(float(user_percentage) - float(requirement), 2)
    return {
        "status": "meets" if requirement <= float(user_percentage) else "below",
        "requirement": round(float(requirement), 2),
        "gap": gap,
    }


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_occupations(
    user_scores: dict,
    occupations: list,
    method: str = "pearson",
    limit: int = 10,
    min_similarity=None,
    user_percentage=None,
) -> dict:
    """
    Urutkan okupasi berdasarkan kemiripan profil RIASEC.

    Returns dict: {'balanced': bool, 'method': str, 'items': [...], 'skipped': int}
    """
    metric = cosine_similarity if method == "cosine" else pearson_similarity

    if is_flat_profile(user_scores):
        return {
            "balanced": True,
            "method": method,
            "items": [],
            "skipped": 0,
            "note": "Profil minat seimbang pada enam dimensi; skor RIASEC tidak "
                    "dapat membedakan okupasi secara sahih.",
        }

    ranked = []
    skipped = 0
    for occ in occupations:
        similarity = metric(user_scores, occ["scores"])
        if similarity is None:
            skipped += 1
            continue
        if min_similarity is not None and similarity < min_similarity:
            continue
        ranked.append({
            "code": occ["code"],
            "occupation": occ["occupation"],
            "occupation_id": occ.get("occupation_id", get_occupation_translation(occ["occupation"])),
            "category": occ["category"],
            "job_zone": occ["job_zone"],
            "scores": occ["scores"],
            "ih": occ["ih"],
            "dominant": dominant_dimensions(occ["scores"]),
            "similarity": similarity,
            "matched_dimensions": dominant_dimensions(user_scores),
            "color": color_status(occ, user_percentage),
        })

    ranked.sort(key=lambda r: (-r["similarity"], r["occupation"].lower()))
    return {
        "balanced": False,
        "method": method,
        "items": ranked[:limit],
        "skipped": skipped,
        "note": None,
    }


def build_reason(item: dict) -> str:
    """Alasan singkat & jujur mengapa okupasi muncul (bukan klaim peluang kerja)."""
    user_dims = "/".join(item["matched_dimensions"])
    occ_dims = "/".join(item["dominant"])
    reason = (
        f"Pola minat Anda ({user_dims}) paling mendekati profil okupasi ini "
        f"({occ_dims}) dengan skor kemiripan {item['similarity']}%."
    )
    color = item.get("color") or {}
    if color.get("status") == "meets":
        reason += f" Tuntutan warna {color['requirement']} terpenuhi oleh skor Anda."
    elif color.get("status") == "below":
        reason += (
            f" Namun tuntutan warna {color['requirement']} masih di atas skor Anda; "
            "jadikan target bertahap, bukan kesimpulan kelayakan."
        )
    elif color.get("status") == "unknown":
        reason += " Data tuntutan warna okupasi ini belum tersedia."
    return reason


def attach_reasons(rows: list) -> list:
    for row in rows:
        row["reason"] = build_reason(row)
    return rows


# ── Kompatibilitas: kecocokan karier pilihan (profil kategori) ────────────────

def category_profile(occupations: list, category: str) -> dict:
    """Rata-rata profil RIASEC okupasi dalam satu kategori karier."""
    items = [o for o in occupations if o["category"] == category]
    if not items:
        return {}
    return {
        d: sum(o["scores"][d] for o in items) / len(items)
        for d in RIASEC_DIMENSIONS
    }


def career_interest_fit(user_scores: dict, occupations: list, category: str):
    """Kemiripan minat pengguna dengan kategori karier yang dipilih (0-100)."""
    profile = category_profile(occupations, category)
    if not profile:
        return None
    return pearson_similarity(user_scores, profile)
