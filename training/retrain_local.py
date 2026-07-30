"""
retrain_local.py - Retrain model di environment lokal untuk kompatibilitas versi XGBoost.
"""
import os
import json
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
DATA_PATH = os.path.join(BASE_DIR, "BWP300DATA.xlsx")
MODEL_DIR = os.path.join(PROJECT_DIR, "src", "model")
BEST_PARAMS_PATH = os.path.join(MODEL_DIR, "best_params.json")

print(f"Python/XGBoost/sklearn env:")
import sys, xgboost, sklearn
print(f"  Python:   {sys.version}")
print(f"  XGBoost:  {xgboost.__version__}")
print(f"  sklearn:  {sklearn.__version__}")

print(f"\nLoading data from: {DATA_PATH}")
df = pd.read_excel(DATA_PATH)
print(f"Shape: {df.shape}")

X = df.drop(columns=['Label'])
y = df['Label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
)

categorical_features = ['JK', 'Pendidikan', 'Riwayat_Keluarga', 'Tingkat Keparahan', 'ColorReq', 'Karier']

label_encoders = {}
for col in categorical_features:
    le = LabelEncoder()
    le.fit(X_train[col])
    X_train[col] = le.transform(X_train[col])
    X_test[col] = X_test[col].apply(
        lambda v: v if v in le.classes_ else le.classes_[0]
    )
    X_test[col] = le.transform(X_test[col])
    label_encoders[col] = le

target_encoder = LabelEncoder()
y_train_enc = target_encoder.fit_transform(y_train)
y_test_enc = target_encoder.transform(y_test)

print(f"\nTarget classes: {target_encoder.classes_}")

smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=1)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train_enc)
print(f"After SMOTE: {X_train_res.shape[0]} samples")

with open(BEST_PARAMS_PATH, "r") as f:
    best_params = json.load(f)

print(f"\nBest params: {best_params}")

final_model = XGBClassifier(**best_params)
final_model.fit(X_train_res, y_train_res)

from sklearn.metrics import accuracy_score, f1_score
y_pred = final_model.predict(X_test)
acc = accuracy_score(y_test_enc, y_pred) * 100
f1 = f1_score(y_test_enc, y_pred, average='macro')
print(f"\nTest Accuracy: {acc:.2f}%")
print(f"Test F1 Macro: {f1:.4f}")

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

feature_list = X_train.columns.tolist()
with open(feature_list_path, "w") as f:
    json.dump(feature_list, f, indent=2)
print(f"Feature list saved: {feature_list_path}")

print("\nVerifying load...")
m = joblib.load(model_path)
e = joblib.load(encoders_path)
print(f"Model type: {type(m)}")
print(f"Encoders type: {type(e)}")
print("All OK!")
