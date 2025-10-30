import random
import os
import json
import re
import ssl
import urllib.parse
import urllib.request
import urllib.error
from dotenv import load_dotenv
from openai import OpenAI


def check_kenteken(kenteken: str) -> bool:
    """Dummy check: return True if it looks like a Dutch plate (6 chars alphanum)."""
    k = kenteken.replace("-", "").strip().upper()
    return len(k) == 6 and k.isalnum()


def analyze_image_is_car(image_url: str, car_type: str) -> dict:
    """Analyze an image URL and check if it matches the specified car type.

    Args:
        image_url: URL of the image to analyze.
        car_type: The expected car type to check for (e.g., "Porsche 718 Cayman", "Nissan 350Z Roadster").

    Returns:
        Dictionary with 'is_car' (bool) indicating if it matches the car_type, and 'car_type' (str).
    """
    load_dotenv()
    # Check if the image URL is reachable and returns a 200 status before continuing
    try:
        req = urllib.request.Request(image_url, method="HEAD")
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
            if resp.status != 200:
                print(f"Image not reachable: {resp.status}")
                return {"is_car": False, "car_type": "image not reachable"}
    except urllib.error.URLError as e:
        print(f"HEAD request failed for image URL: {e}")
        return {"is_car": False, "car_type": "image not reachable"}

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt_text = (
        f"Analyze this image and determine if it shows the specific car type: '{car_type}'. "
        "Consider the make, model, and any other distinguishing features. "
        "Respond with ONLY valid JSON, no markdown or extra text. "
        'Use this exact schema: {"is_car": true/false, "car_type": string}. '
        f'"is_car" should be true only if the image shows a {car_type} (or a very close match). '
        "The car should not be an toy, it should be a real car."
        "If it is not a car, or if it's a different car type, set is_car to false. "
        "If it matches, return the detected car type in the car_type field."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )

    content = response.choices[0].message.content

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = content

    try:
        result = json.loads(json_str)
        is_car = bool(result.get("is_car", False))
        detected_car_type = str(result.get("car_type", "not a car"))
        return {"is_car": is_car, "car_type": detected_car_type}
    except json.JSONDecodeError:
        return {"is_car": False, "car_type": "not a car"}


def extract_image_links_and_snippets(car_type: str) -> list[dict]:
    """Extract all link and snippet nodes from Google Custom Search API response.

    Args:
        car_type: Search query string for the car type.

    Returns:
        List of dictionaries with 'link' and 'snippet' keys.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return []

    base_url = "https://www.googleapis.com/customsearch/v1"
    cx = "857e3825a08534f43"  # Custom Search Engine ID
    params = {"key": api_key, "cx": cx, "q": car_type, "searchType": "image"}

    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, context=ssl_context) as response:
            data = json.loads(response.read().decode())

        items = data.get("items", [])
        result = []

        for item in items:
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            result.append({"link": link, "snippet": snippet})

        return result
    except urllib.error.HTTPError as e:
        print(f"Error fetching Google Images: {e}")
        return []
    except urllib.error.URLError as e:
        print(f"URL Error fetching Google Images: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def get_rdw_data(json_file: str = "rdw.json", license_plate: str = "") -> dict:
    """Fetch year and color from RDW Open Data API.

    Args:
        json_file: Unused parameter (kept for backward compatibility).
        license_plate: Dutch license plate (kenteken) to look up.

    Returns:
        Dictionary with 'year' (first 4 chars of datum_eerste_toelating) and 'color' (eerste_kleur).
    """
    if not license_plate:
        return {"year": "", "color": ""}

    # Clean the license plate (remove dashes, uppercase)
    kenteken = license_plate.replace("-", "").strip().upper()

    # Build the API URL
    base_url = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
    params = {"kenteken": kenteken}
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, context=ssl_context) as response:
            data = json.loads(response.read().decode())

        # Handle both array and single object formats
        if isinstance(data, list):
            if len(data) == 0:
                return {"year": "", "color": ""}
            vehicle_data = data[0]
        else:
            vehicle_data = data

        eerste_kleur = vehicle_data.get("eerste_kleur", "")
        datum_eerste_toelating = vehicle_data.get("datum_eerste_toelating", "")

        # Extract first 4 characters for the year
        year = datum_eerste_toelating[:4] if len(datum_eerste_toelating) >= 4 else ""

        return {"year": year, "color": eerste_kleur}
    except urllib.error.HTTPError as e:
        print(f"Error fetching RDW data: {e}")
        return {"year": "", "color": ""}
    except urllib.error.URLError as e:
        print(f"URL Error fetching RDW data: {e}")
        return {"year": "", "color": ""}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return {"year": "", "color": ""}
    except Exception as e:
        print(f"Unexpected error fetching RDW data: {e}")
        return {"year": "", "color": ""}
