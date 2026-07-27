"""
utils/predictor.py – Load model XGBoost dan lakukan inferensi
"""
import os
import json
import logging
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Singleton: model & encoder dimuat sekali saja ─────────────────────────────
_model     = None
_encoders  = None
_features  = None


def load_model(app_config):
    """
    Muat model, encoders, dan feature list dari path konfigurasi.
    Dipanggil saat aplikasi pertama kali dijalankan.
    """
    global _model, _encoders, _features

    try:
        model_path    = app_config["MODEL_PATH"]
        encoders_path = app_config["ENCODERS_PATH"]
        features_path = app_config["FEATURE_LIST_PATH"]

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model tidak ditemukan: {model_path}")
        if not os.path.exists(encoders_path):
            raise FileNotFoundError(f"Encoders tidak ditemukan: {encoders_path}")
        if not os.path.exists(features_path):
            raise FileNotFoundError(f"Feature list tidak ditemukan: {features_path}")

        _model    = joblib.load(model_path)
        _encoders = joblib.load(encoders_path)

        with open(features_path, "r", encoding="utf-8") as f:
            _features = json.load(f)

        logger.info("✅ Model, encoders, dan feature list berhasil dimuat.")
        logger.info(f"   Features ({len(_features)}): {_features}")

    except Exception as e:
        logger.error(f"❌ Gagal memuat model: {e}")
        _model    = None
        _encoders = None
        _features = None
        raise


def is_model_loaded():
    """Kembalikan True jika model berhasil dimuat."""
    return _model is not None and _encoders is not None and _features is not None


def get_feature_list():
    """Kembalikan daftar fitur yang digunakan model."""
    return _features or []


def predict(feature_dict: dict) -> dict:
    """
    Lakukan prediksi menggunakan model XGBoost.

    Parameters
    ----------
    feature_dict : dict
        Dictionary fitur dengan kunci sesuai feature_list.json.

    Returns
    -------
    dict
        {
          'label'      : str,   # Label prediksi
          'confidence' : float, # Probabilitas kelas terprediksi (0–100)
          'probabilities': dict # Semua probabilitas per kelas
        }
    """
    if not is_model_loaded():
        raise RuntimeError("Model belum dimuat. Hubungi administrator.")

    # ── 1. Bangun DataFrame dengan urutan fitur sesuai feature_list.json ──────
    df = pd.DataFrame([feature_dict], columns=_features)
    logger.debug(f"Input DataFrame sebelum encoding:\n{df.to_string()}")

    # ── 2. Encoding categorical columns menggunakan encoders.pkl ─────────────
    df_encoded = _encode_features(df)
    logger.debug(f"Input DataFrame setelah encoding:\n{df_encoded.to_string()}")

    # ── 4. Prediksi ───────────────────────────────────────────────────────────
    raw_prediction = _model.predict(df_encoded)[0]
    # Konversi ke string (handle numpy types)
    prediction = str(raw_prediction)

    # ── 5. Probabilitas (jika tersedia) ──────────────────────────────────────
    probabilities = {}
    confidence    = 100.0

    if hasattr(_model, "predict_proba"):
        try:
            proba_array = _model.predict_proba(df_encoded)[0]

            # Ambil nama kelas
            if hasattr(_model, "classes_"):
                classes = [str(c) for c in _model.classes_]
            else:
                # Fallback: buat label generik
                classes = [f"Kelas {i}" for i in range(len(proba_array))]

            probabilities = {
                cls: round(float(prob) * 100, 2)
                for cls, prob in zip(classes, proba_array)
            }
            # Confidence = probabilitas kelas yang diprediksi
            confidence = probabilities.get(prediction, max(probabilities.values()) if probabilities else 100.0)

        except Exception as e:
            logger.warning(f"Gagal menghitung probabilitas: {e}")
            probabilities = {prediction: 100.0}
            confidence    = 100.0

    return {
        "label"        : str(prediction),
        "confidence"   : confidence,
        "probabilities": probabilities,
    }


# ── Internal helper ───────────────────────────────────────────────────────────

def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode kolom kategorikal menggunakan encoders.pkl.

    encoders.pkl diasumsikan berupa dict:
      { 'NamaKolom': LabelEncoder, ... }

    Jika encoders.pkl adalah LabelEncoder tunggal atau tipe lain,
    fungsi ini akan menangani keduanya.
    """
    df_out = df.copy()

    if isinstance(_encoders, dict):
        # Format: {'JK': LabelEncoder, 'Pendidikan': LabelEncoder, ...}
        for col, encoder in _encoders.items():
            if col in df_out.columns:
                try:
                    df_out[col] = encoder.transform(df_out[col].astype(str))
                except ValueError as e:
                    logger.warning(
                        f"Nilai tidak dikenal di kolom '{col}': {df_out[col].values}. "
                        f"Menggunakan kelas pertama sebagai fallback. Error: {e}"
                    )
                    # Fallback: gunakan kelas pertama jika nilai tidak dikenal
                    known_classes = list(encoder.classes_)
                    df_out[col] = df_out[col].apply(
                        lambda v: v if v in known_classes else known_classes[0]
                    )
                    df_out[col] = encoder.transform(df_out[col].astype(str))
    else:
        logger.warning(
            "encoders.pkl bukan dict. Asumsikan tidak ada encoding yang diperlukan."
        )

    return df_out
