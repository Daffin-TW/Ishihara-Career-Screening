"""
Audit + validasi sistem rekomendasi RIASEC.

Jalankan: python tests/test_recommender.py
Cetak laporan Top 10: python tests/test_recommender.py --report
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils.recommender import (
    RIASEC_DIMENSIONS,
    attach_reasons,
    build_reason,
    career_interest_fit,
    cosine_similarity,
    dominant_dimensions,
    is_flat_profile,
    load_occupations,
    pearson_similarity,
    rank_occupations,
)

DATA = os.path.join(BASE_DIR, "src", "data")
RIASEC_PATH = os.path.join(DATA, "occupation_riasec.csv")
IMPORTANCE_PATH = os.path.join(DATA, "occupation_importance.csv")
MASTER_PATH = os.path.join(DATA, "all_occupations.csv")

OCCUPATIONS = load_occupations(RIASEC_PATH, IMPORTANCE_PATH, MASTER_PATH)

PROFILES = {
    "Artistic": {d: (25 if d == "A" else 5) for d in RIASEC_DIMENSIONS},
    "Investigative": {d: (25 if d == "I" else 5) for d in RIASEC_DIMENSIONS},
    "Social": {d: (25 if d == "S" else 5) for d in RIASEC_DIMENSIONS},
    "Conventional": {d: (25 if d == "C" else 5) for d in RIASEC_DIMENSIONS},
    "Realistic": {d: (25 if d == "R" else 5) for d in RIASEC_DIMENSIONS},
    "Enterprising": {d: (25 if d == "E" else 5) for d in RIASEC_DIMENSIONS},
    "Balanced": {d: 15 for d in RIASEC_DIMENSIONS},
}


def _rank(profile, **kwargs):
    return rank_occupations(profile, OCCUPATIONS, limit=10, **kwargs)


# ── Integritas dataset ────────────────────────────────────────────────────────

def test_dataset_integrity():
    assert len(OCCUPATIONS) > 900, len(OCCUPATIONS)
    codes = [o["code"] for o in OCCUPATIONS]
    names = [o["occupation"].lower() for o in OCCUPATIONS]
    assert len(codes) == len(set(codes)), "kode O*NET duplikat"
    assert len(names) == len(set(names)), "nama okupasi duplikat"
    for occ in OCCUPATIONS:
        assert set(occ["scores"]) == set(RIASEC_DIMENSIONS), occ["code"]
        assert all(v is not None for v in occ["scores"].values()), occ["code"]


def test_similarity_bounds_and_zero_variance():
    profile = PROFILES["Artistic"]
    for occ in OCCUPATIONS[:50]:
        p = pearson_similarity(profile, occ["scores"])
        c = cosine_similarity(profile, occ["scores"])
        assert p is not None and -0.01 <= p <= 100.01, (occ["code"], p)
        assert c is not None and 0 <= c <= 100.01, (occ["code"], c)
    flat = {d: 4.0 for d in RIASEC_DIMENSIONS}
    assert pearson_similarity(profile, flat) is None
    assert pearson_similarity(PROFILES["Balanced"], OCCUPATIONS[0]["scores"]) is None


def test_pearson_self_similarity_is_100():
    occ = OCCUPATIONS[0]
    assert pearson_similarity(occ["scores"], occ["scores"]) == 100.0
    mirrored = {d: -occ["scores"][d] for d in RIASEC_DIMENSIONS}
    assert pearson_similarity(mirrored, occ["scores"]) == 0.0


def test_flat_profile_returns_no_ranking():
    result = _rank(PROFILES["Balanced"])
    assert result["balanced"] is True
    assert result["items"] == []
    assert is_flat_profile(PROFILES["Balanced"])


# ── Ranking sesuai profil dominan ─────────────────────────────────────────────

def test_ranking_is_sorted_by_similarity():
    for profile in PROFILES.values():
        if is_flat_profile(profile):
            continue
        items = _rank(profile)["items"]
        assert len(items) == 10, len(items)
        sims = [i["similarity"] for i in items]
        assert sims == sorted(sims, reverse=True), sims


def test_dominant_dimension_leads_ranking():
    # Okupasi peringkat atas harus punya dimensi dominan = dominan pengguna,
    # dan IH O*NET-nya memuat dimensi tersebut.
    for peak, label in (("A", "Artistic"), ("I", "Investigative"), ("S", "Social"),
                        ("C", "Conventional"), ("R", "Realistic"), ("E", "Enterprising")):
        items = _rank(PROFILES[label])["items"]
        hits = sum(
            1 for item in items
            if peak in item["dominant"] or peak in item["ih"]
        )
        assert hits >= 8, (peak, hits, [i["occupation"] for i in items])


def test_artistic_case_from_report():
    # Kasus yang dilaporkan: A=25, sisanya 5 -> rekomendasi wajib kreatif.
    items = _rank(PROFILES["Artistic"])["items"]
    names = " | ".join(i["occupation"] for i in items)
    assert "Graphic Designers" in names, names
    assert any("Animators" in i["occupation"] for i in items), names
    for item in items:
        assert "A" in item["dominant"] or "A" in item["ih"], item


def test_balanced_profile_no_crash():
    result = _rank(PROFILES["Balanced"], user_percentage=100)
    assert result["balanced"] is True
    assert result["items"] == []


def test_pearson_vs_cosine_overlap():
    # Metode alternatif tidak harus identik, tetapi harus berbagi sebagian
    # besar okupasi teratas untuk profil yang jelas dominan.
    p = _rank(PROFILES["Artistic"], method="pearson")["items"]
    c = _rank(PROFILES["Artistic"], method="cosine")["items"]
    overlap = len({i["code"] for i in p} & {i["code"] for i in c})
    assert overlap >= 5, overlap


# ── Pemisahan RIASEC vs warna ────────────────────────────────────────────────

def test_color_does_not_change_riasec_ranking():
    low = _rank(PROFILES["Artistic"], user_percentage=0)["items"]
    high = _rank(PROFILES["Artistic"], user_percentage=100)["items"]
    assert [i["code"] for i in low] == [i["code"] for i in high]
    assert [i["similarity"] for i in low] == [i["similarity"] for i in high]


def test_color_status_values():
    items = _rank(PROFILES["Artistic"], user_percentage=0)["items"]
    for item in items:
        assert item["color"]["status"] in ("meets", "below", "unknown")
        if item["color"]["status"] == "below":
            assert item["color"]["requirement"] > 0


def test_reason_mentions_similarity_and_color():
    item = _rank(PROFILES["Artistic"], user_percentage=100)["items"][0]
    reason = build_reason(item)
    assert str(item["similarity"]) in reason
    assert "warna" in reason.lower()


def test_attached_reasons():
    items = attach_reasons(_rank(PROFILES["Social"])["items"])
    assert all(i["reason"] for i in items)


# ── Kecocokan karier pilihan ────────────────────────────────────────────────

def test_career_interest_fit():
    fit = career_interest_fit(
        PROFILES["Artistic"], OCCUPATIONS, "[Seni & Kreatif] Desain Grafis"
    )
    assert fit is not None and fit >= 80, fit
    missing = career_interest_fit(PROFILES["Artistic"], OCCUPATIONS, "[Tidak Ada]")
    assert missing is None


# ── Laporan ──────────────────────────────────────────────────────────────────

def print_report():
    for name, profile in PROFILES.items():
        result = _rank(profile, user_percentage=100)
        print(f"\n=== {name} ===")
        if result["balanced"]:
            print("  profil seimbang:", result["note"])
            continue
        for rank, item in enumerate(result["items"], 1):
            print(
                f"  {rank:2d}. {item['occupation'][:48]:50s} "
                f"sim={item['similarity']:5.1f}%  "
                f"IH={'/'.join(item['ih']) or '-':7s} "
                f"JZ={item['job_zone']}  warna={item['color']['status']}"
            )


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report()
        sys.exit(0)
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok  {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    if failures:
        sys.exit(1)
    print("semua cek lulus")
