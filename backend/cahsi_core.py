from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
import shap

BASE_DIR = Path(__file__).resolve().parent.parent
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

# Human-readable windows for the /crop-calendar endpoint, per the PRD's 3-stage format.
# Orange has no sowing stage (perennial, Mrig bahar cycle) - flowering window used instead.
CROP_CALENDAR_WINDOWS = {
    'Cotton':  {'sowing_window': 'June — July', 'critical_stage': 'September — October',
                'harvest_window': 'November — January',
                'critical_stage_guidance': 'सध्या फुलोऱ्याचा व बोंड तयार होण्याचा काळ — पाण्याची विशेष काळजी घ्या.'},
    'Soybean': {'sowing_window': 'June — July', 'critical_stage': 'August — September',
                'harvest_window': 'September — October',
                'critical_stage_guidance': 'फुलोरा व शेंगा भरण्याचा काळ — ओलावा सातत्याने राखा.'},
    'Tur':     {'sowing_window': 'June — July', 'critical_stage': 'September — November',
                'harvest_window': 'December — January',
                'critical_stage_guidance': 'फुलोरा व शेंगा भरण्याचा काळ — पाण्याचा ताण टाळा.'},
    'Wheat':   {'sowing_window': 'October — November', 'critical_stage': 'January',
                'harvest_window': 'February — March',
                'critical_stage_guidance': 'फुलोऱ्याचा काळ — नियमित हलके सिंचन आवश्यक आहे.'},
    'Orange':  {'sowing_window': 'Flowering: June — July (Mrig Bahar)', 'critical_stage': 'June — July',
                'harvest_window': 'September — March (Ambiya + Mrig crop)',
                'critical_stage_guidance': 'फुलोऱ्याचा काळ — पाण्याचा तुटवडा टाळा, ही सर्वात संवेदनशील अवस्था आहे.'},
}

DRIVER_LABELS = {
    'CAHSI_lag1': 'recent overall stress trend', 'CAHSI_lag2': 'recent overall stress trend',
    'CAHSI_lag3': 'recent overall stress trend', 'CAHSI_roll3': 'recent overall stress trend',
    'CAHSI_prioryr': 'comparison to same period last year',
    'spi3_lag1': 'recent rainfall deficit (SPI)', 'spi3_lag2': 'recent rainfall deficit (SPI)',
    'spi3_lag3': 'recent rainfall deficit (SPI)', 'spi3_roll3': 'recent rainfall deficit (SPI)',
    'spi3_prioryr': 'rainfall compared to last year',
    'ndvi_anomaly_lag1': 'declining vegetation health (NDVI)', 'ndvi_anomaly_lag2': 'declining vegetation health (NDVI)',
    'ndvi_anomaly_lag3': 'declining vegetation health (NDVI)', 'ndvi_anomaly_roll3': 'declining vegetation health (NDVI)',
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
_validation_history = pd.read_csv(BASE_DIR / "data/processed/objective_iv_lead_time.csv")


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


def _get_row(district, as_of_date=None):
    df = _build_full_feature_table()
    dist_rows = df[df['DISTRICT_STD'] == district].dropna(subset=[f'{c}_lag3' for c in FEATURE_COLS])
    if as_of_date:
        target = pd.Timestamp(as_of_date)
        dist_rows = dist_rows[dist_rows['date'] <= target]
    if dist_rows.empty:
        return None
    return dist_rows.iloc[[-1]]


def get_cahsi_prediction(district, crop, as_of_date=None):
    """Returns dict with cahsi_score, severity, as_of_date, horizon, or an 'error' key."""
    cfg = CROP_WINDOWS.get(crop)
    if cfg is None:
        return {'error': f'Unknown crop: {crop}'}
    if cfg['districts'] and district not in cfg['districts']:
        return {'error': f'{crop} is not grown in {district}'}

    row = _get_row(district, as_of_date)
    if row is None:
        return {'error': f'No data available for {district}' + (f' on or before {as_of_date}' if as_of_date else '')}

    current_month = int(row['date'].dt.month.iloc[0])
    if current_month not in cfg['months']:
        return {'error': f'{crop} is not in-season in {district} on {row["date"].iloc[0].date()}'}

    delta_pred = _model.predict(row[FEATURES])[0]
    cahsi_pred = float(row['CAHSI'].iloc[0] + delta_pred)

    thresh_row = _thresholds[_thresholds['crop'] == crop].iloc[0]
    severity = classify(cahsi_pred, thresh_row['severe_cutoff_CAHSI'], thresh_row['moderate_cutoff_CAHSI'])

    return {
        'district': district, 'crop': crop,
        'cahsi_score': round(cahsi_pred, 3), 'severity': severity,
        'as_of_date': str(row['date'].iloc[0].date()), 'horizon': 't+1',
        'cahsi_lag1': round(float(row['CAHSI_lag1'].iloc[0]), 3),
        'cahsi_lag2': round(float(row['CAHSI_lag2'].iloc[0]), 3),
        'cahsi_lag3': round(float(row['CAHSI_lag3'].iloc[0]), 3),
        '_row': row,
    }


def get_shap_driver(row):
    shap_row = _explainer(row[FEATURES])
    top_feature = FEATURES[int(np.argmax(np.abs(shap_row.values[0])))]
    return DRIVER_LABELS.get(top_feature, top_feature)


def get_crop_stage(crop, as_of_date=None):
    if as_of_date:
        month = pd.Timestamp(as_of_date).month
    else:
        row = _get_row(next(iter(CROP_WINDOWS[crop]['districts'] or ['Nagpur'])), as_of_date)
        month = int(row['date'].dt.month.iloc[0]) if row is not None else 1
    return CROP_STAGE_BY_MONTH.get(crop, {}).get(month, 'growth')


def get_crop_calendar(crop, as_of_date=None):
    cfg = CROP_WINDOWS.get(crop)
    if cfg is None:
        return {'error': f'Unknown crop: {crop}'}

    windows = CROP_CALENDAR_WINDOWS[crop]
    stage = get_crop_stage(crop, as_of_date)

    return {
        'crop': crop,
        'sowing_window': windows['sowing_window'],
        'critical_stage': windows['critical_stage'],
        'critical_stage_guidance': windows['critical_stage_guidance'],
        'harvest_window': windows['harvest_window'],
        'current_stage': stage,
    }


def get_validation_history(district, crop):
    """Read-only lookup into objective_iv_lead_time.csv, filtered to district/crop.
    No computation - just filter and shape the existing rows. Sorted by
    lead_time_weeks descending so the strongest evidence of accuracy is first.
    Returns an empty list (not an error) when no record exists - frontend hides
    the panel rather than showing an empty/error state."""
    rows = _validation_history[
        (_validation_history['DISTRICT_STD'] == district) &
        (_validation_history['crop'] == crop)
    ].sort_values('lead_time_weeks', ascending=False)

    if rows.empty:
        return []

    return rows[['year', 'declaration_date', 'first_severe_date', 'lead_time_weeks', 'status']].to_dict(orient='records')