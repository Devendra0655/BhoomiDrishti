from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

cahsi = pd.read_csv(BASE_DIR / "data/processed/cahsi_period_level.csv")
cahsi['date'] = pd.to_datetime(cahsi['date'])
cahsi['month'] = cahsi['date'].dt.month

CROP_WINDOWS = {
    'Cotton':  {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Soybean': {'months': [6,7,8,9,10], 'districts': None},
    'Tur':     {'months': [6,7,8,9,10,11,12,1], 'districts': None},
    'Wheat':   {'months': [10,11,12,1,2,3], 'districts': None},
    'Orange':  {'months': [6,7,8,9,10,11], 'districts': ['Nagpur', 'Amravati']},
}

PERCENTILE_BANDS = {'Severe': 0.15, 'Moderate': 0.35}

results = []
threshold_table = []

for crop, cfg in CROP_WINDOWS.items():
    subset = cahsi[cahsi['month'].isin(cfg['months'])]
    if cfg['districts']:
        subset = subset[subset['DISTRICT_STD'].isin(cfg['districts'])]

    severe_cutoff = subset['CAHSI'].quantile(PERCENTILE_BANDS['Severe'])
    moderate_cutoff = subset['CAHSI'].quantile(PERCENTILE_BANDS['Moderate'])

    def classify(v):
        if v <= severe_cutoff:
            return 'Severe'
        elif v <= moderate_cutoff:
            return 'Moderate'
        return 'Low'

    subset = subset.copy()
    subset['crop'] = crop
    subset['severity'] = subset['CAHSI'].apply(classify)
    results.append(subset)

    threshold_table.append({
        'crop': crop,
        'n_periods': len(subset),
        'districts_used': cfg['districts'] or 'all 11',
        'severe_cutoff_CAHSI': severe_cutoff,
        'moderate_cutoff_CAHSI': moderate_cutoff,
        'literature_cross_check': 'not available - CAHSI is novel, no prior calibration exists to check against',
    })

crop_classified = pd.concat(results, ignore_index=True)
crop_classified.to_csv(BASE_DIR / "data/processed/cahsi_crop_severity.csv", index=False)

thresholds_df = pd.DataFrame(threshold_table)
thresholds_df.to_csv(BASE_DIR / "data/processed/crop_thresholds.csv", index=False)

print("Threshold table:")
print(thresholds_df.to_string(index=False))

print("\nSeverity distribution per crop:")
print(crop_classified.groupby(['crop', 'severity']).size().unstack(fill_value=0))

print("\nSevere periods in confirmed drought years (2015/2018/2019), per crop:")
drought_check = crop_classified[crop_classified['year'].isin([2015, 2018, 2019])]
print(drought_check.groupby(['crop', 'severity']).size().unstack(fill_value=0))