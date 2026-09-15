import os
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
client = Groq(api_key=os.environ["GROQ_API_KEY"])

FEATURE_COLS = ['CAHSI', 'ndvi_anomaly', 'spi3']

CROP_WINDOWS = {
    'Cotton':  {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Soybean': {'months': [6,7,8,9,10],          'districts': None},
    'Tur':     {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Wheat':   {'months': [10,11,12,1,2,3],      'districts': None},
    'Orange':  {'months': [6,7,8,9,10,11],       'districts': ['Nagpur', 'Amravati']},
}

CROP_STAGE_BY_MONTH = {
    'Cotton':  {6:'sowing',7:'sowing',8:'flowering/boll formation',9:'flowering/boll formation',
                10:'boll formation',11:'harvest',12:'harvest',1:'harvest'},
    'Soybean': {6:'sowing',7:'sowing',8:'flowering/pod formation',9:'pod formation',10:'harvest'},
    'Tur':     {6:'sowing',7:'sowing',8:'vegetative',9:'flowering',10:'flowering',
                11:'pod formation',12:'harvest',1:'harvest'},
    'Wheat':   {10:'sowing',11:'sowing',12:'vegetative growth',1:'flowering',2:'grain filling',3:'harvest'},
    'Orange':  {6:'flowering (Mrig bahar)',7:'flowering (Mrig bahar)',8:'fruit set',
                9:'fruit development',10:'fruit development',11:'fruit development'},
}

DRIVER_LABELS = {
    'CAHSI_lag1': 'recent overall stress trend', 'CAHSI_lag2': 'recent overall stress trend',
    'CAHSI_lag3': 'recent overall stress trend', 'CAHSI_roll3': 'recent overall stress trend',
    'CAHSI_prioryr': 'comparison to same period last year',
    'spi3_lag1': 'recent rainfall deficit', 'spi3_lag2': 'recent rainfall deficit',
    'spi3_lag3': 'recent rainfall deficit', 'spi3_roll3': 'recent rainfall deficit',
    'spi3_prioryr': 'rainfall compared to last year',
    'ndvi_anomaly_lag1': 'declining vegetation health', 'ndvi_anomaly_lag2': 'declining vegetation health',
    'ndvi_anomaly_lag3': 'declining vegetation health', 'ndvi_anomaly_roll3': 'declining vegetation health',
    'ndvi_anomaly_prioryr': 'vegetation compared to last year',
    'doy_sin': 'seasonal timing', 'doy_cos': 'seasonal timing',
}

FEATURES = [f'{c}_lag{l}' for c in FEATURE_COLS for l in (1, 2, 3)] \
    + [f'{c}_roll3' for c in FEATURE_COLS] \
    + [f'{c}_prioryr' for c in FEATURE_COLS] \
    + ['doy_sin', 'doy_cos', 'DISTRICT_STD']

_model = xgb.XGBRegressor()
_model.load_model(str(BASE_DIR / 'data/processed/xgboost_cahsi_delta_t1.json'))
_explainer = shap.TreeExplainer(_model)
_thresholds = pd.read_csv(BASE_DIR / "data/processed/crop_thresholds.csv")


def _build_full_feature_table():
    df = pd.read_csv(BASE_DIR / "data/processed/cahsi_period_level.csv")
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['DISTRICT_STD', 'date']).reset_index(drop=True)
    df['doy_period'] = df['date'].dt.dayofyear

    for col in FEATURE_COLS:
        g = df.groupby('DISTRICT_STD')[col]
        for lag in (1, 2, 3):
            df[f'{col}_lag{lag}'] = g.shift(lag)
        df[f'{col}_roll3'] = g.transform(lambda s: s.shift(1).rolling(3).mean())

    prior_cols = ['DISTRICT_STD', 'year', 'doy_period'] + FEATURE_COLS
    prior = df[prior_cols].rename(columns={c: f'{c}_prioryr' for c in FEATURE_COLS})
    prior['year'] = prior['year'] + 1
    df = df.merge(prior, on=['DISTRICT_STD', 'year', 'doy_period'], how='left')

    df['doy_sin'] = np.sin(2 * np.pi * df['doy_period'] / 365.25)
    df['doy_cos'] = np.cos(2 * np.pi * df['doy_period'] / 365.25)
    df['DISTRICT_STD'] = df['DISTRICT_STD'].astype('category')
    return df


def classify(value, severe_cutoff, moderate_cutoff):
    if value <= severe_cutoff:
        return 'Severe'
    elif value <= moderate_cutoff:
        return 'Moderate'
    return 'Low'


def get_advisory(district, crop, as_of_date=None):
    """as_of_date: optional 'YYYY-MM-DD' string. Defaults to the latest available period."""
    cfg = CROP_WINDOWS[crop]
    if cfg['districts'] and district not in cfg['districts']:
        return f"{crop} is not grown in {district}; no advisory available."

    df = _build_full_feature_table()
    dist_rows = df[df['DISTRICT_STD'] == district].dropna(subset=[f'{c}_lag3' for c in FEATURE_COLS])

    if as_of_date:
        target = pd.Timestamp(as_of_date)
        dist_rows = dist_rows[dist_rows['date'] <= target]
        if dist_rows.empty:
            return f"No data available on or before {as_of_date} for {district}."
        row = dist_rows.iloc[[-1]]
    else:
        if dist_rows.empty:
            return f"Insufficient data to generate advisory for {district}."
        row = dist_rows.iloc[[-1]]

    current_month = row['date'].dt.month.iloc[0]
    if current_month not in cfg['months']:
        return f"{crop} is not in-season in {district} on {row['date'].iloc[0].date()}; no active advisory."

    delta_pred = _model.predict(row[FEATURES])[0]
    cahsi_pred = row['CAHSI'].iloc[0] + delta_pred

    thresh_row = _thresholds[_thresholds['crop'] == crop].iloc[0]
    severity = classify(cahsi_pred, thresh_row['severe_cutoff_CAHSI'], thresh_row['moderate_cutoff_CAHSI'])

    shap_row = _explainer(row[FEATURES])
    top_feature = FEATURES[np.argmax(np.abs(shap_row.values[0]))]
    driver = DRIVER_LABELS.get(top_feature, top_feature)

    stage = CROP_STAGE_BY_MONTH.get(crop, {}).get(current_month, 'current growth stage')

    system_prompt = (
        "You are an agricultural advisor writing short, practical advisories for farmers "
        "in Vidarbha, Maharashtra, in Marathi. Write exactly 3-4 short lines, no markdown, "
        "no English words, keep each line under 20 words."
    )
    user_prompt = (
        f"District: {district}\nCrop: {crop}\nSeverity: {severity} (CAHSI={cahsi_pred:.2f})\n"
        f"Crop stage: {stage}\nMain driver: {driver}\n\nWrite a short Marathi advisory for the farmer."
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.4,
    )
    return {
        'district': district, 'crop': crop, 'date_used': str(row['date'].iloc[0].date()),
        'severity': severity, 'cahsi_predicted': round(float(cahsi_pred), 3),
        'stage': stage, 'driver': driver,
        'advisory_marathi': response.choices[0].message.content,
    }


if __name__ == "__main__":
    print("=== Latest available (calm case) ===")
    print(get_advisory('Washim', 'Wheat'))

    print("\n=== Historical demo: Yavatmal/Cotton, October 2018 (known Severe) ===")
    print(get_advisory('Yavatmal', 'Cotton', as_of_date='2018-10-16'))