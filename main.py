from dotenv import load_dotenv
from tools import (
    analyze_image_is_car,
    extract_image_links_and_snippets,
    get_rdw_data,
    check_kenteken,
    extract_license_plate_from_image,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from openai import BadRequestError


load_dotenv()


REFLECT = "reflect"
GENERATE = "generate"
limit = 10

def answer_node(state: dict) -> dict:

    messages = state.get("messages", [])
    car_type = (
        messages[0].content if messages and hasattr(messages[0], "content") else ""
    )
    license_plate = state.get("license_plate", "")
    if check_kenteken(license_plate) == True:
        rdw_data = get_rdw_data(license_plate=license_plate)
        if rdw_data == [] or not isinstance(rdw_data, dict):
            rdw_data = {"year": "", "color": ""}

        car_type = f"{car_type} {license_plate}".strip()
        print(car_type)

    attempts = state.get("attempts", 0)
    image_counter = state.get("image_counter", 0)

    print("\n" + ">" * 60)
    print(f"[GENERATE] Attempt #{attempts + 1}")
    print(f"[GENERATE] Search query: '{car_type}'")
    print(f"[GENERATE] Image counter: {image_counter}")
    print(f"[GENERATE] Fetching images...")

    results = extract_image_links_and_snippets(car_type=car_type)

    print(f"[GENERATE] Found {len(results)} image results")

    if results and image_counter < len(results):
        image_link = results[image_counter]["link"]
        print(f"[GENERATE] Selected image #{image_counter + 1}: {image_link}")
    else:
        image_link = ""
        print(f"[GENERATE] ⚠ No more images available")

    # Extract and validate license plate from image if available
    license_plate_match = None
    if image_link and license_plate:
        print(f"[GENERATE] Extracting license plate from image...")
        extracted_plate = extract_license_plate_from_image(image_link)

        # Normalize both plates for comparison (remove dashes, uppercase)
        normalized_provided = license_plate.replace("-", "").strip().upper()
        normalized_extracted = extracted_plate.replace("-", "").strip().upper()

        license_plate_match = normalized_provided == normalized_extracted

        print(f"[GENERATE] Provided license plate: '{license_plate}'")
        print(f"[GENERATE] Extracted license plate: '{extracted_plate}'")
        print(f"[GENERATE] License plate match: {license_plate_match}")

        if not license_plate_match:
            print(f"[GENERATE] ⚠ License plate mismatch!")

    print(">" * 60 + "\n")

    return {
        **state,
        "image_url": image_link,
        "attempts": attempts + 1,
        "car_type": car_type,
        "license_plate_match": license_plate_match,
    }


def reflection_node(state: dict) -> dict:
    raw_car_type = state.get("raw_car_type", "")
    image_url = state.get("image_url", "")
    attempts = state.get("attempts", 0)
    image_counter = state.get("image_counter", 0)

    print("\n" + "=" * 60)
    print(f"[REFLECTION] Attempt #{attempts}")
    print(f"[REFLECTION] Checking image {image_counter + 1}")
    print(f"[REFLECTION] Car type to match: '{raw_car_type}'")
    print(f"[REFLECTION] Image URL: {image_url}")

    # Check if image_url is empty (no results from API)
    if not image_url or image_url.strip() == "":
        print(f"[REFLECTION] ⚠ No image URL available. Skipping analysis.")
        print("=" * 60 + "\n")
        return {
            **state,
            "is_car": False,
            "car_type": "no image available",
            "image_counter": image_counter,
        }

    print(f"[REFLECTION] Analyzing image...")

    try:
        is_car_result = analyze_image_is_car(image_url, raw_car_type)
        is_car = is_car_result.get("is_car", False)
        detected_car_type = is_car_result.get("car_type", "not a car")
    except BadRequestError as e:
        # Handle invalid image URL errors (e.g., can't download from Instagram)
        print(f"[REFLECTION] ⚠ Error analyzing image: {e}")
        print(f"[REFLECTION] Image URL cannot be processed. Moving to next image...")
        is_car_result = {"is_car": False, "car_type": "image download failed"}
        is_car = False
        detected_car_type = "image download failed"

    print(f"[REFLECTION] Result: is_car = {is_car}")
    print(f"[REFLECTION] Detected car type: '{detected_car_type}'")

    # Increment image_counter if it's not a car
    if not is_car:
        image_counter += 1
        print(f"[REFLECTION] Image does not match. Moving to next image...")
        print(f"[REFLECTION] Image counter incremented to: {image_counter}")
    else:
        print(f"[REFLECTION] ✓ Image matches the car type! Success!")

    print("=" * 60 + "\n")

    return {**state, **is_car_result, "image_counter": image_counter}


def should_continue(state: dict) -> str:
    attempts = state.get("attempts", 0)
    is_car = state.get("is_car", False)
    license_plate = state.get("license_plate", "")
    license_plate_match = state.get("license_plate_match")

    print("\n" + "-" * 60)
    print(f"[DECISION] Attempts: {attempts}, Is car: {is_car}")
    if license_plate:
        print(f"[DECISION] License plate match: {license_plate_match}")

    # If it's a car, check license plate match if license plate was provided
    if is_car:
        # If license plate was provided, also check if it matches
        if license_plate:
            if license_plate_match:
                print(
                    f"[DECISION] ✓ Found matching car with matching license plate! Ending search."
                )
                print("-" * 60 + "\n")
                return END
            else:
                print(
                    f"[DECISION] ⚠ Car matches but license plate doesn't. Continuing search..."
                )
        else:
            print(f"[DECISION] ✓ Found matching car! Ending search.")
            print("-" * 60 + "\n")
            return END

    # If we've tried 8 times, stop
    if attempts >= limit:
        print(f"[DECISION] ✗ Maximum attempts ({attempts}) reached. Stopping.")
        print("-" * 60 + "\n")
        return END

    # Try again by going back to answer node
    print(f"[DECISION] Continuing to next attempt...")
    print("-" * 60 + "\n")
    return GENERATE


graph = StateGraph(dict)
graph.add_node(GENERATE, answer_node)
graph.add_node(REFLECT, reflection_node)

# Set up edges
graph.set_entry_point(GENERATE)
graph.add_edge(GENERATE, REFLECT)
graph.add_conditional_edges(REFLECT, should_continue)

app = graph.compile()


def invoke(car_type: str, license_plate: str = "") -> dict:
    """Invoke the LangGraph app with provided parameters and return the result.

    Args:
        car_type: The car type search query.
        license_plate: Optional license plate to enrich the query.

    Returns:
        The state dictionary returned by the graph execution.
    """
    return app.invoke(
        {
            "messages": [HumanMessage(content=car_type or "")],
            "license_plate": license_plate or "",
        }
    )
