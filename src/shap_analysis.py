from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data/processed/shap"
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

for h in (1, 2):
    actual_col = f'CAHSI_t+{h}'
    subset = df.dropna(subset=FEATURES + [actual_col]).copy()
    test = subset[subset['split'] == 'test']

    model = xgb.XGBRegressor()
    model.load_model(str(BASE_DIR / f'data/processed/xgboost_cahsi_delta_t{h}.json'))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(test[FEATURES])

    print(f"\n=== Horizon t+{h} — mean |SHAP| per feature (top 8) ===")
    mean_abs = pd.Series(np.abs(shap_values.values).mean(axis=0), index=FEATURES).sort_values(ascending=False)
    print(mean_abs.head(8).to_string())

    plt.figure()
    shap.summary_plot(shap_values, test[FEATURES], show=False)
    plt.tight_layout()
    plt.savefig(OUT_DIR / f'shap_summary_t{h}.png', dpi=150)
    plt.close()
    print(f"Saved shap_summary_t{h}.png")

    # Waterfall plots: pick 2015 Yavatmal onset, 2018 Yavatmal/Washim onset, one from test set
    waterfall_targets = []
    for dist, yr, mo, day in [('Yavatmal', 2015, 7, 12), ('Yavatmal', 2018, 10, 16), ('Washim', 2018, 10, 16)]:
        match = subset[(subset['DISTRICT_STD'] == dist) & (subset['date'] == pd.Timestamp(yr, mo, day))]
        if not match.empty:
            waterfall_targets.append((f'{dist}_{yr}{mo:02d}{day:02d}', match.index[0]))

    for label, idx in waterfall_targets[:3]:
        row = df.loc[[idx]]
        row_shap = explainer(row[FEATURES])
        plt.figure()
        shap.plots.waterfall(row_shap[0], show=False)
        plt.tight_layout()
        plt.savefig(OUT_DIR / f'shap_waterfall_t{h}_{label}.png', dpi=150)
        plt.close()
        print(f"Saved shap_waterfall_t{h}_{label}.png")

print("\nDone. Inspect PNGs in data/processed/shap/")