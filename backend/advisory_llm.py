import os
from dotenv import load_dotenv
from groq import Groq

from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = (
    "You are an agricultural advisor writing short, practical advisories for farmers "
    "in Vidarbha, Maharashtra, in Marathi. Respond in exactly this format, nothing else:\n"
    "REASON: <one short Marathi sentence naming the main driver, under 12 words>\n"
    "ADVISORY: <3-4 short Marathi lines, no markdown, no English words, each line under 20 words>"
)

# Same instructions in English, used only when the app is switched to English (?lang=en).
SYSTEM_PROMPT_EN = (
    "You are an agricultural advisor writing short, practical advisories for farmers "
    "in Vidarbha, Maharashtra, in simple English. Respond in exactly this format, nothing else:\n"
    "REASON: <one short English sentence naming the main driver, under 12 words>\n"
    "ADVISORY: <3-4 short English lines, no markdown, each line under 20 words>"
)


def generate_advisory(district, crop, severity, cahsi_score, stage, driver, lang="mr"):
    user_prompt = (
        f"District: {district}\nCrop: {crop}\nSeverity: {severity} (CAHSI={cahsi_score:.2f})\n"
        f"Crop stage: {stage}\nMain driver: {driver}\n\nRespond in the required format."
    )
    response = _client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    text = response.choices[0].message.content.strip()

    reason_text, advisory_text = "", text
    if "REASON:" in text and "ADVISORY:" in text:
        reason_part = text.split("REASON:")[1].split("ADVISORY:")[0].strip()
        advisory_part = text.split("ADVISORY:")[1].strip()
        reason_text, advisory_text = reason_part, advisory_part

    return reason_text, advisory_text