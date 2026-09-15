from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

BASE_DIR = Path(__file__).resolve().parent.parent

df = pd.read_csv(BASE_DIR / "data/processed/cahsi_period_level.csv")
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['DISTRICT_STD', 'date']).reset_index(drop=True)

df['doy_period'] = df['date'].dt.dayofyear

# gw_anomaly deliberately excluded from lag/rolling/prior-year features: real CGWB
# reporting effectively stops in early 2021, so gw_anomaly is null for ~85% of the
# 2021-2022 test period. Requiring its lags silently collapsed the test set to a
# narrow Jan-Apr 2021 sliver. CAHSI_lag* already carries whatever GW contribution
# existed via the weighted, renormalized formula from assemble_cahsi.py.
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
    df[f'delta_t+{h}'] = df[f'CAHSI_t+{h}'] - df['CAHSI']
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
    df.loc[crossed, [f'CAHSI_t+{h}', f'delta_t+{h}']] = np.nan

df['DISTRICT_STD'] = df['DISTRICT_STD'].astype('category')

FEATURES = [f'{c}_lag{l}' for c in FEATURE_COLS for l in (1, 2, 3)] \
    + [f'{c}_roll3' for c in FEATURE_COLS] \
    + [f'{c}_prioryr' for c in FEATURE_COLS] \
    + ['doy_sin', 'doy_cos', 'DISTRICT_STD']

param_grid = {
    'n_estimators': [200, 400],
    'max_depth': [3, 5],
    'learning_rate': [0.05, 0.1],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0],
}

results = {}
models = {}

for h in (1, 2):
    delta_col = f'delta_t+{h}'
    actual_col = f'CAHSI_t+{h}'
    subset = df.dropna(subset=FEATURES + [delta_col, actual_col])

    train = subset[subset['split'] == 'train']
    val = subset[subset['split'] == 'val']
    test = subset[subset['split'] == 'test']

    print(f"\n=== Horizon t+{h} ({h*16} days / {h*16/7:.1f} weeks) ===")
    print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    model = xgb.XGBRegressor(tree_method='hist', enable_categorical=True, random_state=42)
    search = GridSearchCV(model, param_grid, cv=5, scoring='neg_root_mean_squared_error', n_jobs=-1)
    search.fit(train[FEATURES], train[delta_col])
    best = search.best_estimator_

    print(f"Best params: {search.best_params_}")

    for name, split_data in [('val', val), ('test', test)]:
        delta_pred = best.predict(split_data[FEATURES])
        final_pred = split_data['CAHSI'].values + delta_pred
        actual = split_data[actual_col].values

        rmse = np.sqrt(mean_squared_error(actual, final_pred))
        mae = mean_absolute_error(actual, final_pred)
        r2 = r2_score(actual, final_pred)
        persist_rmse = np.sqrt(mean_squared_error(actual, split_data['CAHSI'].values))
        persist_r2 = r2_score(actual, split_data['CAHSI'].values)

        print(f"  {name}: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}  "
              f"[persistence baseline: RMSE={persist_rmse:.4f}, R2={persist_r2:.4f}]")

        if name == 'test':
            results[h] = {'rmse': rmse, 'mae': mae, 'r2': r2,
                          'persistence_rmse': persist_rmse, 'persistence_r2': persist_r2,
                          'n_test': len(split_data)}

    models[h] = best
    best.save_model(str(BASE_DIR / f'data/processed/xgboost_cahsi_delta_t{h}.json'))

pd.DataFrame(results).T.to_csv(BASE_DIR / "data/processed/xgboost_test_metrics.csv")
print("\nSaved models and metrics.")