### FCT Car Finder

### What this project does

This project searches for car images on the web based on a car type and optionally enriches the search using Dutch RDW vehicle data when a license plate is provided. It then evaluates returned images with an AI vision model to determine if the image likely shows the requested car type.

### How it works (high level)

- **Inputs**: `car_type` (required), `license_plate` (optional)
- **RDW enrichment**: If `license_plate` looks valid, the RDW API is queried for year and color, which are appended to the search query.
- **Image search**: Google Custom Search (Images) fetches candidate images.
- **AI verification**: An AI model evaluates images to check if they match the requested car type.
- **Output**: The response includes the selected image URL under `image_url` and other state fields.

### Requirements

- **Python**: 3.11+
- **Environment variables**:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`

### Install

1. Create and activate a virtual environment (optional).
2. Install dependencies:

```bash
uv sync
```

### Run the API server

Start the FastAPI server via Uvicorn:

```bash
uvicorn api:app --reload --port 8000
```

### HTTP API usage

- **Endpoint**: `GET /`
- **Query parameters**:
  - `car_type`: string, required (non-empty)
  - `license_plate`: string, optional

### Examples

1) With both parameters:

[http://127.0.0.1:8000/?car_type=Ford%20Mustang%20GT&license_plate=P-304-RL](http://127.0.0.1:8000/?car_type=Ford%20Mustang%20GT&license_plate=P-304-RL)

2) Missing or empty `car_type` (returns a friendly message):

[http://127.0.0.1:8000/?car_type=](http://127.0.0.1:8000/?car_type=)

### Response shape (example)

```json
{
  "image_url": "https://example.com/some-image.jpg",
  "attempts": 1,
  "car_type": "Ford Mustang GT 2015 ZWART P-304-RL",
  "is_car": true
}
```

### Local development

- **Graph and invoke entrypoint**: `main.py` (function `invoke`)
- **HTTP endpoint**: `api.py` (FastAPI)
- **Utilities and external API calls**: `tools.py`

