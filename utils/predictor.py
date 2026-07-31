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


def _safe_load_pkl(file_path):
    """
    Mencoba memuat file .pkl dengan berbagai strategi fallback:
    1. joblib.load
    2. pickle.load (rb)
    3. bz2 / gzip / zipfile + pickle/joblib
    4. xgboost.XGBClassifier / Booster (jika format native XGBoost)
    """
    import pickle
    import gzip
    import bz2
    import zipfile

    # Strategi 1: Standard joblib
    try:
        return joblib.load(file_path)
    except Exception as e1:
        logger.debug(f"joblib.load gagal untuk {file_path}: {e1}")

    # Strategi 2: Standard pickle
    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e2:
        logger.debug(f"pickle.load gagal untuk {file_path}: {e2}")

    # Strategi 3: Native XGBoost model (jika disave dengan save_model / JSON / UBJ / binary model)
    try:
        import xgboost as xgb
        # Coba sebagai XGBClassifier
        model = xgb.XGBClassifier()
        model.load_model(file_path)
        return model
    except Exception as e_xgb1:
        logger.debug(f"XGBClassifier.load_model gagal: {e_xgb1}")

    try:
        import xgboost as xgb
        # Coba sebagai raw Booster
        booster = xgb.Booster()
        booster.load_model(file_path)
        return booster
    except Exception as e_xgb2:
        logger.debug(f"Booster.load_model gagal: {e_xgb2}")

    # Strategi 4: bz2 + pickle / joblib
    try:
        with bz2.open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        pass

    # Strategi 5: gzip + pickle / joblib
    try:
        with gzip.open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        pass

    # Strategi 6: zipfile
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            first_file = z.namelist()[0]
            with z.open(first_file) as f:
                return pickle.load(f)
    except Exception:
        pass

    raise ValueError(
        f"Gagal memuat file pickle '{file_path}'. Format tidak dikenali atau file terkompresi khusus/rusak."
    )


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

        _model    = _safe_load_pkl(model_path)
        _encoders = _safe_load_pkl(encoders_path)

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
          'label'      : str,   # Label prediksi (label target asli, bukan index kelas)
          'confidence' : float, # Probabilitas kelas terprediksi (0–100)
          'probabilities': dict # Semua probabilitas per kelas
        }
    """
    if not is_model_loaded():
        raise RuntimeError("Model belum dimuat. Hubungi administrator.")

    # Target encoder: untuk mengubah index kelas model kembali ke label target asli
    target_encoder = None
    if isinstance(_encoders, dict):
        target_encoder = _encoders.get("target_encoder")

    # ── 1. Bangun DataFrame dengan urutan fitur sesuai feature_list.json ──────
    df = pd.DataFrame([feature_dict], columns=_features)
    logger.debug(f"Input DataFrame sebelum encoding:\n{df.to_string()}")

    # ── 2. Encoding categorical columns menggunakan encoders.pkl ─────────────
    df_encoded = _encode_features(df)
    logger.debug(f"Input DataFrame setelah encoding:\n{df_encoded.to_string()}")

    # ── 3. Prediksi ───────────────────────────────────────────────────────────
    import xgboost as xgb
    proba_array = None

    if isinstance(_model, xgb.Booster):
        dmatrix = xgb.DMatrix(df_encoded, enable_categorical=True)
        preds = _model.predict(dmatrix)
        if preds.ndim > 1:
            raw_prediction = np.argmax(preds[0])
            proba_array = preds[0]
        else:
            raw_prediction = int(preds[0] > 0.5)
            proba_array = [1 - preds[0], preds[0]]
    else:
        raw_prediction = _model.predict(df_encoded)[0]

    prediction = str(raw_prediction)

    # ── 3b. Kembalikan index kelas ke label target asli ─────────────────────
    if target_encoder is not None:
        try:
            prediction = str(target_encoder.inverse_transform([int(raw_prediction)])[0])
        except Exception as e:
            logger.warning(f"Gagal inverse_transform label prediksi: {e}")

    # ── 4. Probabilitas (jika tersedia) ──────────────────────────────────────
    probabilities = {}
    confidence    = 100.0

    if isinstance(_model, xgb.Booster):
        if target_encoder is not None:
            classes = [str(c) for c in target_encoder.classes_][:len(proba_array)]
        else:
            classes = [f"Kelas {i}" for i in range(len(proba_array))]
        probabilities = {cls: round(float(p) * 100, 2) for cls, p in zip(classes, proba_array)}
        confidence = probabilities.get(prediction, max(probabilities.values()) if probabilities else 100.0)

    elif hasattr(_model, "predict_proba"):
        try:
            proba_array = _model.predict_proba(df_encoded)[0]

            if target_encoder is not None:
                classes = [str(c) for c in target_encoder.classes_]
            elif hasattr(_model, "classes_"):
                classes = [str(c) for c in _model.classes_]
            else:
                classes = [f"Kelas {i}" for i in range(len(proba_array))]

            probabilities = {
                cls: round(float(prob) * 100, 2)
                for cls, prob in zip(classes, proba_array)
            }
            confidence = probabilities.get(prediction, max(probabilities.values()) if probabilities else 100.0)

        except Exception as e:
            logger.warning(f"Gagal menghitung probabilitas: {e}")
            probabilities = {prediction: 100.0}
            confidence    = 100.0

    return {
        "label"        : prediction,
        "confidence"   : confidence,
        "probabilities": probabilities,
    }


# ── Internal helper ───────────────────────────────────────────────────────────

def _is_object_like(series: pd.Series) -> bool:
    """True jika kolom berupa string/object (butuh encoding atau kategori)."""
    dt = series.dtype
    return dt == object or isinstance(dt, pd.StringDtype)


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode kolom kategorikal menggunakan encoders.pkl.

    encoders.pkl diasumsikan berupa dict:
      { 'NamaKolom': LabelEncoder, ... }

    Jika encoders.pkl adalah LabelEncoder tunggal atau tipe lain,
    fungsi ini akan menangani keduanya.

    Kolom bertipe object/string yang tidak memiliki encoder akan dikonversi
    ke dtype 'category' agar XGBoost (enable_categorical=True) tetap dapat
    memprosesnya tanpa error.
    """
    df_out = df.copy()

    if isinstance(_encoders, dict):
        # Format notebook: {'label_encoders': {'JK': LE, ...}, 'target_encoder': LE}
        label_encoders = _encoders.get('label_encoders', _encoders)
        for col, encoder in label_encoders.items():
            if col in df_out.columns:
                try:
                    df_out[col] = encoder.transform(df_out[col].astype(str))
                except ValueError as e:
                    logger.warning(
                        f"Nilai tidak dikenal di kolom '{col}': {df_out[col].values}. "
                        f"Menggunakan kelas pertama sebagai fallback. Error: {e}"
                    )
                    known_classes = list(encoder.classes_)
                    df_out[col] = df_out[col].apply(
                        lambda v: v if v in known_classes else known_classes[0]
                    )
                    df_out[col] = encoder.transform(df_out[col].astype(str))
    else:
        logger.warning(
            "encoders.pkl bukan dict. Asumsikan tidak ada encoding yang diperlukan."
        )

    # ── Kolom object/string yang tersisa (tidak ada encoder) → category dtype ──
    remaining_object = [c for c in df_out.columns if _is_object_like(df_out[c])]
    for col in remaining_object:
        logger.warning(
            f"Kolom '{col}' tidak memiliki encoder; dikonversi ke dtype category."
        )
        df_out[col] = df_out[col].astype("category")

    # ── Validasi akhir: log kolom dengan dtype yang tidak didukung XGBoost ────
    bad = [
        c for c in df_out.columns
        if not (pd.api.types.is_numeric_dtype(df_out[c])
                or pd.api.types.is_categorical_dtype(df_out[c]))
    ]
    if bad:
        logger.warning(f"Kolom dengan dtype tidak didukung setelah encoding: {bad}")

    return df_out
