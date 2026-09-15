from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent.parent

df = pd.read_csv(BASE_DIR / "data/processed/cahsi_period_level.csv")
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['DISTRICT_STD', 'date']).reset_index(drop=True)
df['doy_period'] = df['date'].dt.dayofyear

FEATURE_COLS = ['CAHSI', 'ndvi_anomaly', 'spi3']

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

for h in (1, 2):
    df[f'CAHSI_t+{h}'] = df.groupby('DISTRICT_STD')['CAHSI'].shift(-h)
    df[f'_target_date_{h}'] = df.groupby('DISTRICT_STD')['date'].shift(-h)


def split_of(date):
    if pd.isna(date):
        return None
    if pd.Timestamp('2013-01-01') <= date <= pd.Timestamp('2018-12-31'):
        return 'train'
    if pd.Timestamp('2019-01-01') <= date <= pd.Timestamp('2020-12-31'):
        return 'val'
    if pd.Timestamp('2021-01-01') <= date <= pd.Timestamp('2022-12-31'):
        return 'test'
    return None


df['split'] = df['date'].apply(split_of)
for h in (1, 2):
    tgt_split = df[f'_target_date_{h}'].apply(split_of)
    crossed = (tgt_split != df['split']) & tgt_split.notna() & df['split'].notna()
    df.loc[crossed, f'CAHSI_t+{h}'] = np.nan

df['DISTRICT_STD'] = df['DISTRICT_STD'].astype('category')

FEATURES = [f'{c}_lag{l}' for c in FEATURE_COLS for l in (1, 2, 3)] \
    + [f'{c}_roll3' for c in FEATURE_COLS] \
    + [f'{c}_prioryr' for c in FEATURE_COLS] \
    + ['doy_sin', 'doy_cos', 'DISTRICT_STD']

thresholds = pd.read_csv(BASE_DIR / "data/processed/crop_thresholds.csv")

CROP_WINDOWS = {
    'Cotton':  {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Soybean': {'months': [6,7,8,9,10], 'districts': None},
    'Tur':     {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Wheat':   {'months': [10,11,12,1,2,3], 'districts': None},
    'Orange':  {'months': [6,7,8,9,10,11], 'districts': ['Nagpur', 'Amravati']},
}


def classify(value, severe_cutoff, moderate_cutoff):
    if value <= severe_cutoff:
        return 'Severe'
    elif value <= moderate_cutoff:
        return 'Moderate'
    return 'Low'


results = []

for h in (1, 2):
    actual_col = f'CAHSI_t+{h}'
    subset = df.dropna(subset=FEATURES + [actual_col]).copy()
    test = subset[subset['split'] == 'test'].copy()

    model = xgb.XGBRegressor()
    model.load_model(str(BASE_DIR / f'data/processed/xgboost_cahsi_delta_t{h}.json'))

    delta_pred = model.predict(test[FEATURES])
    test['CAHSI_pred'] = test['CAHSI'].values + delta_pred
    test['target_month'] = (test['date'] + pd.to_timedelta(h * 16, unit='D')).dt.month

    for crop, cfg in CROP_WINDOWS.items():
        row = thresholds[thresholds['crop'] == crop].iloc[0]
        severe_cut, moderate_cut = row['severe_cutoff_CAHSI'], row['moderate_cutoff_CAHSI']

        crop_test = test[test['target_month'].isin(cfg['months'])]
        if cfg['districts']:
            crop_test = crop_test[crop_test['DISTRICT_STD'].isin(cfg['districts'])]

        if crop_test.empty:
            results.append({'horizon': f't+{h}', 'crop': crop, 'n': 0, 'accuracy': None})
            continue

        actual_class = crop_test[actual_col].apply(lambda v: classify(v, severe_cut, moderate_cut))
        pred_class = crop_test['CAHSI_pred'].apply(lambda v: classify(v, severe_cut, moderate_cut))

        accuracy = (actual_class == pred_class).mean()
        results.append({'horizon': f't+{h}', 'crop': crop, 'n': len(crop_test), 'accuracy': accuracy})

results_df = pd.DataFrame(results)
results_df.to_csv(BASE_DIR / "data/processed/crop_classification_accuracy.csv", index=False)
print(results_df.to_string(index=False))