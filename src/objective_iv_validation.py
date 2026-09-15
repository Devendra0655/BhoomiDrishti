from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

severity = pd.read_csv(BASE_DIR / "data/processed/cahsi_crop_severity.csv")
severity['date'] = pd.to_datetime(severity['date'])
labels = pd.read_csv(BASE_DIR / "data/processed/drought_labels.csv")

DECLARATION_DATES = {
    ('Buldhana', 2015): pd.Timestamp('2015-11-09'),
    ('Amravati', 2015): pd.Timestamp('2016-03-25'),
    ('Wardha', 2015): pd.Timestamp('2016-03-25'),
    ('Nagpur', 2015): pd.Timestamp('2016-03-25'),
    ('Yavatmal', 2015): pd.Timestamp('2016-03-25'),
    ('Akola', 2015): pd.Timestamp('2016-03-25'),
    ('Chandrapur', 2015): pd.Timestamp('2016-03-25'),
    ('Gondia', 2015): pd.Timestamp('2016-03-25'),
    ('Bhandara', 2015): pd.Timestamp('2016-03-25'),
    ('Yavatmal', 2018): pd.Timestamp('2018-10-31'),
    ('Washim', 2018): pd.Timestamp('2018-10-31'),
    ('Yavatmal', 2019): pd.Timestamp('2019-02-22'),
    ('Washim', 2019): pd.Timestamp('2019-02-22'),
}

# 2019 is a continuation of the 2018 drought event (Feb 2019 expansion, not a fresh Kharif cycle),
# so its search window is anchored to the 2018 Kharif season, not June 2019.
SEASON_START = {
    2015: pd.Timestamp('2015-06-01'),
    2018: pd.Timestamp('2018-06-01'),
    2019: pd.Timestamp('2018-06-01'),
}

VALIDATION_CROP = {}
for d in ['Akola','Amravati','Bhandara','Buldhana','Chandrapur','Gadchiroli',
          'Gondia','Nagpur','Wardha','Washim','Yavatmal']:
    VALIDATION_CROP[d] = ['Cotton']
VALIDATION_CROP['Nagpur'].append('Orange')
VALIDATION_CROP['Amravati'].append('Orange')

confirmed = labels[(labels['drought_label'] == 1) & (labels['year'].isin([2015, 2018, 2019]))]

results = []
for _, row in confirmed.iterrows():
    district, year = row['DISTRICT_STD'], row['year']
    decl_date = DECLARATION_DATES.get((district, year))
    if decl_date is None:
        results.append({'DISTRICT_STD': district, 'year': year, 'crop': None,
                         'status': 'no declaration date available'})
        continue

    season_start = SEASON_START[year]

    for crop in VALIDATION_CROP[district]:
        crop_data = severity[(severity['DISTRICT_STD'] == district) & (severity['crop'] == crop)]
        window = crop_data[(crop_data['date'] >= season_start) & (crop_data['date'] <= decl_date + pd.Timedelta(days=60))]
        severe_hits = window[window['severity'] == 'Severe'].sort_values('date')

        if severe_hits.empty:
            results.append({'DISTRICT_STD': district, 'year': year, 'crop': crop,
                             'declaration_date': decl_date.date(), 'first_severe_date': None,
                             'lead_time_weeks': None, 'status': 'no Severe period found in window'})
            continue

        first_severe = severe_hits.iloc[0]['date']
        lead_days = (decl_date - first_severe).days
        results.append({
            'DISTRICT_STD': district, 'year': year, 'crop': crop,
            'declaration_date': decl_date.date(), 'first_severe_date': first_severe.date(),
            'lead_time_weeks': round(lead_days / 7, 1),
            'status': 'ahead of declaration' if lead_days > 0 else 'at/after declaration',
        })

results_df = pd.DataFrame(results)
out_path = BASE_DIR / "data/processed/objective_iv_lead_time.csv"
results_df.to_csv(out_path, index=False)

print(f"Saved {len(results_df)} rows to {out_path}\n")
print(results_df.to_string(index=False))