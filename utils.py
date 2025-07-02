import streamlit as st
import pickle
import pandas as pd
import struct
from datetime import date

MODEL_DIR = 'models/'

@st.cache_resource
def load_model_artifacts():
    """Loads the model and preprocessing artifacts from the specified directory."""
    with open(f"{MODEL_DIR}XGB_cancer.pkl", 'rb') as f:
        model = pickle.load(f)
    with open(f"{MODEL_DIR}label_encoders.pkl", 'rb') as f:
        label_encoders = pickle.load(f)
    with open(f"{MODEL_DIR}one_hot_encoders.pkl", 'rb') as f:
        ohe = pickle.load(f)
    with open(f"{MODEL_DIR}scaler.pkl", 'rb') as f:
        scaler = pickle.load(f)
    return {
        'model': model,
        'label_encoders': label_encoders,
        'ohe': ohe,
        'scaler': scaler
    }

def ordinal_encode(df, ordinal_encoders):
    """Applies ordinal encoding to the specified features using the provided encoders."""
    for col, encoder in ordinal_encoders.items():
        if col in df.columns:
            df[col] = encoder.transform(df[col])
    return df

# def label_encode(df, label_encoders):
#     """Applies label encoding to the specified features using the provided encoders."""
#     for col, le in label_encoders.items():
#         if col in df.columns:
#             df[col] = le.transform(df[col])
#     return df

def one_hot_encode(df, ohe_dict):
    """Applies one-hot encoding to the specified features using the provided encoders dict."""
    for col, ohe in ohe_dict.items():
        if col in df.columns:
            transformed = ohe.transform(df[[col]])
            feature_names = ohe.get_feature_names_out([col])
            ohe_df = pd.DataFrame(transformed, columns=feature_names, index=df.index)
            df = df.drop(columns=[col]).join(ohe_df)
    return df

def feature_selection(df):
    """Selects the relevant features for the model."""
    selected_columns = [
        'Age', 'TumorSize', 'CancerStage', 'Metastasis',
        'TumorType_Stomach',
        'TreatmentType_Radiation',
        'Comorbidities_Diabetes, Hepatitis B', 'Comorbidities_Diabetes, Hypertension',
        'Comorbidities_Hypertension, Hepatitis B', 'Comorbidities_No Comorbidities'
    ]
    df_selected = pd.DataFrame(columns=selected_columns)
    for col in selected_columns:
        if col in df.columns:
            df_selected[col] = df[col]
        else:
            df_selected[col] = 0
    return df_selected

def scale_features(df, scaler):
    """Scales the specified features using the provided scaler."""
    numeric_cols = ['Age', 'TumorSize']
    df[numeric_cols] = scaler.transform(df[numeric_cols])
    return df

def preprocess_for_prediction(input_df, artifacts):
    """Preprocess user's input for prediction using the loaded artifacts."""
    input_df = pd.DataFrame(input_df)

    # Apply label encoding
    input_df = ordinal_encode(input_df, artifacts['label_encoders'])
    # Apply one-hot encoding
    input_df = one_hot_encode(input_df, artifacts['ohe'])
    # Select relevant features
    input_df = feature_selection(input_df)
    # Scale numerical features
    input_df = scale_features(input_df, artifacts['scaler'])
    return input_df

def to_float(x):
    """Safely converts various types to float."""
    if isinstance(x, float):
        return x
    if isinstance(x, int):
        return float(x)
    if isinstance(x, bytes):
        try:
            # Try to decode as string first
            return float(x.decode(errors='ignore'))
        except Exception:
            try:
                # Try unpacking as double (8 bytes)
                return struct.unpack('d', x)[0]
            except Exception:
                # Try unpacking as float (4 bytes)
                return struct.unpack('f', x)[0]
    return float(x) if x is not None else 0.0

def highlight_risk(val):
    color = ""
    if val == "High Risk":
        color = "background-color: #ffcccc; color: red"
    elif val == "Medium Risk":
        color = "background-color: #fff9c4; color: #b59f00"
    elif val == "Low Risk":
        color = "background-color: #d0f5d8; color: green"
    return color

def calculate_age(birth_date: date) -> int:
    """
    Calculates the current age of a person given their birth date.
    """
    if not birth_date:
        return 0 # Return 0 or raise an error if the date is missing

    today = date.today()
    
    # This calculation correctly accounts for whether the birthday has occurred this year
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    return age

def get_risk_emoji(predicted_class):
    if predicted_class == "High Risk":
        return "🔴"
    elif predicted_class == "Medium Risk":
        return "🟡"
    else: # Low Risk
        return "🟢"