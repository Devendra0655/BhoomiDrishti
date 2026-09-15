from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import cahsi_core
from advisory_llm import generate_advisory

app = FastAPI(title="BhoomiDrishti API")

# Dev-friendly CORS. Restrict allow_origins to the real PWA domain before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cahsi/{district}/{crop}")
def cahsi(district: str, crop: str, as_of_date: str | None = None):
    result = cahsi_core.get_cahsi_prediction(district, crop, as_of_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    result.pop("_row")
    return result


@app.get("/advisory/{district}/{crop}")
def advisory(district: str, crop: str, as_of_date: str | None = None):
    result = cahsi_core.get_cahsi_prediction(district, crop, as_of_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    row = result.pop("_row")
    driver = cahsi_core.get_shap_driver(row)
    stage = cahsi_core.get_crop_stage(crop, as_of_date)

    reason_text, advisory_text = generate_advisory(
        district, crop, result["severity"], result["cahsi_score"], stage, driver
    )

    return {
        "district": district,
        "crop": crop,
        "top_driver": driver,
        "reason_text": reason_text,
        "advisory_text": advisory_text,
        "last_updated": result["as_of_date"],
    }


@app.get("/crop-calendar/{crop}")
def crop_calendar(crop: str, as_of_date: str | None = None):
    result = cahsi_core.get_crop_calendar(crop, as_of_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/validation-history/{district}/{crop}")
def validation_history(district: str, crop: str):
    return cahsi_core.get_validation_history(district, crop)