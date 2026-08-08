"""
retrain_local.py - Retrain model dengan 17 fitur baru (sesuai form & feature_list.json).
Transformasi data training lama (BWP300DATA.xlsx) ke format label baru secara otomatis.
"""
import os
import json
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

RANDOM_STATE = 42
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

from utils.preprocessor import CAREER_MAPPING

DATA_PATH = os.path.join(BASE_DIR, "BWP300DATA.xlsx")
MODEL_DIR = os.path.join(PROJECT_DIR, "src", "model")
BEST_PARAMS_PATH = os.path.join(MODEL_DIR, "best_params.json")

print(f"Python/XGBoost/sklearn env:")
import xgboost, sklearn
print(f"  Python:   {sys.version}")
print(f"  XGBoost:  {xgboost.__version__}")
print(f"  sklearn:  {sklearn.__version__}")

print(f"\nLoading data from: {DATA_PATH}")
df = pd.read_excel(DATA_PATH)
print(f"Original shape: {df.shape}")
print(f"Original columns: {df.columns.tolist()}")

# ── 1. Transformasi kolom ke format baru ────────────────────────────────

JK_MAP = {'L': 'Laki-laki', 'P': 'Perempuan'}
PENDIDIKAN_MAP = {
    'SMA': 'SMA / SMK / Sederajat',
    'D3': 'Diploma (D1-D4)',
    'S1': 'Sarjana (S1)',
    'S2': 'Pascasarjana (S2/S3)',
}
KARIER_MAP = {
    'Dokter': '[Kesehatan] Kedokteran',
    'Perawat': '[Kesehatan] Keperawatan',
    'Polisi': '[Keselamatan & Transportasi] Kepolisian',
    'Pilot': '[Keselamatan & Transportasi] Penerbangan',
    'Guru': '[Sosial & Humaniora] Pendidikan / Mengajar',
    'Akuntan': '[Bisnis & Administrasi] Akuntansi',
    'Desainer Grafis': '[Seni & Kreatif] Desain Grafis',
    'Programmer': '[Teknologi Informasi] Informatika / Ilmu Komputer',
    'Data Analyst': '[Teknologi Informasi] Data Science / Kecerdasan Buatan',
    'Make Up Artist': '[Seni & Kreatif] Multimedia / Film',
}
ALAT_BANTU_MAP = {0: 'Tidak', 1: 'Ya'}
PENYAKIT_MATA_MAP = {0: 'Tidak ada', 1: 'Ada'}


def usia_to_range(u):
    if u <= 25:
        return "17-25 tahun"
    elif u <= 35:
        return "26-35 tahun"
    elif u <= 45:
        return "36-45 tahun"
    else:
        return "> 45 tahun"


df['Usia'] = df['Usia'].apply(usia_to_range)
df['JK'] = df['JK'].map(JK_MAP)
df['Pendidikan'] = df['Pendidikan'].map(PENDIDIKAN_MAP)
df['Karier'] = df['Karier'].map(KARIER_MAP)
df['Peng. Kacamata'] = df['Alat_Bantu_Penglihatan'].map(ALAT_BANTU_MAP)
df['Kondisi Mata'] = df['Penyakit_Mata_Lain'].map(PENYAKIT_MATA_MAP)
df['JobZone'] = df['JobZone'].astype(str)

# ColorReq: derive from career using CAREER_MAPPING (numeric score)
df['ColorReq'] = df['Karier'].map(lambda c: int(CAREER_MAPPING.get(c, ("4", 25))[1]))

# ── 2. Pilih hanya 17 fitur baru ─────────────────────────────────────────

FEATURE_LIST = [
    "Usia", "JK", "Pendidikan", "Riwayat_Keluarga",
    "Persentase nilai identifikasi warna", "Kemampuan identifikasi Warna",
    "R", "I", "A", "S", "E", "C",
    "Karier", "JobZone", "ColorReq", "Peng. Kacamata", "Kondisi Mata",
]

df = df[FEATURE_LIST + ['Label']]
print(f"\nTransformed shape: {df.shape}")
print(f"Transformed columns: {df.columns.tolist()}")
print(f"Sample data:\n{df.head(3)}")

# ── 3. Split train/test ──────────────────────────────────────────────────

X = df.drop(columns=['Label'])
y = df['Label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
)

# ── 4. Encode categorical columns secara otomatis ────────────────────────

cat_cols = X_train.select_dtypes(include=['object']).columns.tolist()
print(f"\nCategorical columns detected: {cat_cols}")

label_encoders = {}
for col in cat_cols:
    le = LabelEncoder()
    le.fit(X_train[col])
    X_train[col] = le.transform(X_train[col])
    X_test[col] = X_test[col].apply(
        lambda v, c=col: v if v in le.classes_ else le.classes_[0]
    )
    X_test[col] = le.transform(X_test[col])
    label_encoders[col] = le

target_encoder = LabelEncoder()
y_train_enc = target_encoder.fit_transform(y_train)
y_test_enc = target_encoder.transform(y_test)

print(f"\nTarget classes: {target_encoder.classes_}")
for col, le in label_encoders.items():
    print(f"  {col}: {le.classes_}")

# ── 5. SMOTE & Training ─────────────────────────────────────────────────

smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=1)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train_enc)
print(f"\nAfter SMOTE: {X_train_res.shape[0]} samples")

with open(BEST_PARAMS_PATH, "r") as f:
    best_params = json.load(f)
print(f"Best params: {best_params}")

final_model = XGBClassifier(**best_params)
final_model.fit(X_train_res, y_train_res)

from sklearn.metrics import accuracy_score, f1_score
y_pred = final_model.predict(X_test)
acc = accuracy_score(y_test_enc, y_pred) * 100
f1 = f1_score(y_test_enc, y_pred, average='macro')
print(f"\nTest Accuracy: {acc:.2f}%")
print(f"Test F1 Macro: {f1:.4f}")

# ── 6. Simpan artifacts ─────────────────────────────────────────────────

os.makedirs(MODEL_DIR, exist_ok=True)

model_path = os.path.join(MODEL_DIR, "model_production.pkl")
encoders_path = os.path.join(MODEL_DIR, "encoders.pkl")
feature_list_path = os.path.join(MODEL_DIR, "feature_list.json")

joblib.dump(final_model, model_path)
print(f"\nModel saved: {model_path}")

encoder_pack = {
    'label_encoders': label_encoders,
    'target_encoder': target_encoder,
}
joblib.dump(encoder_pack, encoders_path)
print(f"Encoders saved: {encoders_path}")

with open(feature_list_path, "w") as f:
    json.dump(FEATURE_LIST, f, indent=2)
print(f"Feature list saved: {feature_list_path}")

# ── 7. Verify ───────────────────────────────────────────────────────────

print("\nVerifying load...")
m = joblib.load(model_path)
e = joblib.load(encoders_path)
print(f"Model type: {type(m)}")
print(f"Encoders type: {type(e)}")
print("All OK!")
