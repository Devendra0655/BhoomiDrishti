from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

DISTRICTS = ['Akola', 'Amravati', 'Bhandara', 'Buldhana', 'Chandrapur',
             'Gadchiroli', 'Gondia', 'Nagpur', 'Wardha', 'Washim', 'Yavatmal']

CANDIDATE_YEARS = [2013, 2015, 2018, 2019]  # 2013 represents the "2012-13" drought (only year present in restricted 2013-2022 data)

CONFIRMED = {
    2013: {
        'Buldhana': "Step 6 ref doc - 2012-13 Maharashtra drought, worst-hit districts",
    },
    2015: {
        'Amravati': "Step 6 ref doc - 2015 drought, worst-affected districts named",
        'Wardha': "Step 6 ref doc - 2015 drought, worst-affected districts named",
        'Nagpur': "Step 6 ref doc - 2015 drought, worst-affected districts named",
        'Yavatmal': "Step 6 ref doc - 2015 drought, worst-affected districts named",
        'Buldhana': "Step 6 ref doc - 2015 drought, worst-affected districts named",
        'Akola': "Step 6 ref doc - 2015 drought, water scarcity districts",
        'Chandrapur': "Step 6 ref doc - 2015 drought, water scarcity districts",
        'Gondia': "Step 6 ref doc - 2015 drought, water scarcity districts",
        'Bhandara': "Step 6 ref doc - 2015 drought, water scarcity districts",
    },
    2018: {
        'Yavatmal': "Step 6 ref doc - 2018-19 drought, tehsils named in state order",
        'Washim': "Step 6 ref doc - 2018-19 drought, drought-declared district",
    },
    2019: {
        'Yavatmal': "Step 6 ref doc - 2018-19 drought, tehsils named in state order",
        'Washim': "Step 6 ref doc - 2018-19 drought, drought-declared district",
    },
}

rows = []
for year in CANDIDATE_YEARS:
    for district in DISTRICTS:
        if district in CONFIRMED.get(year, {}):
            rows.append({
                'DISTRICT_STD': district,
                'year': year,
                'drought_label': 1,
                'label_confidence': 'confirmed',
                'source_note': CONFIRMED[year][district],
            })
        else:
            rows.append({
                'DISTRICT_STD': district,
                'year': year,
                'drought_label': 0,
                'label_confidence': 'default_zero',
                'source_note': 'not individually named in sources checked',
            })

labels = pd.DataFrame(rows)

out_path = BASE_DIR / "data/processed/drought_labels.csv"
labels.to_csv(out_path, index=False)

print(f"Saved {len(labels)} rows to {out_path}")
print(f"\nLabel distribution:")
print(labels['drought_label'].value_counts())
print(f"\nConfidence distribution:")
print(labels['label_confidence'].value_counts())
print(f"\nFull table:")
print(labels.to_string(index=False))