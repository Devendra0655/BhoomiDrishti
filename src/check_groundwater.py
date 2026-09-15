import pandas as pd
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "data" / "raw" / "cgwb_groundwater" / "cgwb_groundwater_raw.csv"

df = pd.read_csv(path)
print("Total rows:", len(df))
print("Unique states:", sorted(df['state_name'].dropna().unique().tolist()))
maharashtra = df[df['state_name'] == 'Maharashtra']
print("\nMaharashtra districts:", sorted(maharashtra['district_name'].dropna().unique().tolist()))
vidarbha_districts = [
    'Amravati', 'Yavatmal', 'Wardha', 'Nagpur', 'Akola',
    'Buldhana', 'Washim', 'Bhandara', 'Gondia', 'Chandrapur', 'Gadchiroli'
]

vidarbha_gw = maharashtra[maharashtra['district_name'].isin(vidarbha_districts)]
print("\nVidarbha groundwater rows:", len(vidarbha_gw))
print("Districts found:", sorted(vidarbha_gw['district_name'].unique().tolist()))

output_path = path.parent / "vidarbha_groundwater.csv"
vidarbha_gw.to_csv(output_path, index=False)
print("Saved to:", output_path)