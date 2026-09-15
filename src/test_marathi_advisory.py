import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = (
    "You are an agricultural advisor writing short, practical advisories for farmers "
    "in Vidarbha, Maharashtra, in Marathi. Write 3-4 lines, clear and actionable, "
    "no English words, no markdown formatting."
)

TEST_CASES = [
    {"district": "Yavatmal", "crop": "Cotton", "severity": "Severe",
     "cahsi": -0.63, "stage": "flowering/boll formation", "driver": "low rainfall (SPI-3) over the past month"},
    {"district": "Nagpur", "crop": "Orange", "severity": "Moderate",
     "cahsi": -0.31, "stage": "flowering (Mrig bahar)", "driver": "declining soil moisture trend"},
    {"district": "Washim", "crop": "Wheat", "severity": "Low",
     "cahsi": 0.15, "stage": "vegetative growth", "driver": "normal rainfall and groundwater levels"},
]

for case in TEST_CASES:
    user_prompt = (
        f"District: {case['district']}\nCrop: {case['crop']}\nSeverity: {case['severity']} "
        f"(CAHSI={case['cahsi']})\nCrop stage: {case['stage']}\nMain driver: {case['driver']}\n\n"
        f"Write a short Marathi advisory for the farmer."
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    print(f"\n=== {case['district']} / {case['crop']} / {case['severity']} ===")
    print(response.choices[0].message.content)