from fastapi import FastAPI, Query
from typing import Optional

from main import invoke as run_invoke


app = FastAPI(title="FCT Car Finder API")


@app.get("/")
def find_car(
    car_type: Optional[str] = Query(
        default=None, description="Car make/model to search"
    ),
    license_plate: Optional[str] = Query(
        default=None, description="Optional license plate"
    ),
):
    # If car_type is empty or missing, return a friendly message
    if not car_type or car_type.strip() == "":
        return {"message": "Please provide a non-empty car_type query parameter."}

    result = run_invoke(car_type.strip(), (license_plate or "").strip())
    return result
