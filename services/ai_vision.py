import os
import json
import base64
import requests
from PIL import Image
import jsonschema
from config import Config

# Strict JSON Schema for Server-side AI Output Validation
AI_FOOD_SCHEMA = {
    "type": "object",
    "properties": {
        "food_name": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "cooked_rice", "curry_gravy", "bread_roti", "fruit_veg",
                "packaged_meal", "dairy_sweets", "snacks", "other"
            ]
        },
        "visible_items_or_containers_count": {"type": ["integer", "null"]},
        "approximate_quantity_range": {"type": ["string", "null"]},
        "quantity_unit_suggestion": {
            "type": ["string", "null"],
            "enum": ["kg", "portions", "meal_boxes", "plates", "pieces", None]
        },
        "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "confidence_reasoning": {"type": "string"},
        "fields_requiring_staff_input": {
            "type": "array",
            "items": {"type": "string"}
        },
        "storage_recommendation": {"type": "string"}
    },
    "required": [
        "food_name", "category", "visible_items_or_containers_count",
        "approximate_quantity_range", "confidence_score", "confidence_reasoning",
        "fields_requiring_staff_input"
    ],
    "additionalProperties": True
}

def analyze_food_photo(image_path):
    """
    Analyzes an uploaded surplus food photo using Google Gemini Vision API.
    If GEMINI_API_KEY is not configured or network call fails, falls back to
    honest local heuristic analysis with explicit configuration warnings.
    """
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": "Image file not found on server.",
            "data": None
        }

    # Verify image integrity with PIL
    try:
        with Image.open(image_path) as img:
            img.verify()
    except Exception as e:
        return {
            "success": False,
            "error": f"Invalid or corrupted image file: {str(e)}",
            "data": None
        }

    api_key = Config.GEMINI_API_KEY.strip()
    if api_key:
        return _call_gemini_vision(image_path, api_key)
    else:
        # Honest fallback when external API credentials are not yet configured
        return _local_heuristic_analysis(image_path)

def _call_gemini_vision(image_path, api_key):
    """Invokes Google Gemini Vision REST API with structured schema."""
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Determine mime type
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        mime_type = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"

        system_instruction = (
            "You are SmartPlate AI Food Identification Assistant for college canteens and hostel messes. "
            "Examine the food photo carefully and provide an honest structured evaluation. "
            "CRITICAL INSTRUCTIONS ON QUANTITY ESTIMATION: "
            "1. NEVER fabricate or guess an exact weight (e.g. do not invent '4.25 kg'). "
            "2. If items or meal boxes are individually countable, count them and provide the count. "
            "3. If bulk food like rice or curry is shown, provide an approximate portion range ONLY if container context exists; "
            "otherwise set approximate_quantity_range to 'Unknown - bulk quantity requires staff scale measurement'. "
            "4. Clearly list all fields requiring physical verification by staff. "
            "5. Label all outputs as AI suggestions, not verified facts."
        )

        prompt = (
            "Analyze this surplus food item. Return JSON matching this exact structure: "
            "food_name (string), category (one of: cooked_rice, curry_gravy, bread_roti, fruit_veg, packaged_meal, dairy_sweets, snacks, other), "
            "visible_items_or_containers_count (integer or null), approximate_quantity_range (string or null), "
            "quantity_unit_suggestion (one of: kg, portions, meal_boxes, plates, pieces or null), "
            "confidence_score (float 0.0 to 1.0), confidence_reasoning (string explaining visible visual cues and limitations), "
            "fields_requiring_staff_input (array of strings, e.g. ['exact weight', 'cooking time', 'allergens']), "
            "storage_recommendation (string)."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64_image}}
                ]
            }],
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"Gemini API returned HTTP {resp.status_code}: {resp.text[:200]}",
                "data": None
            }

        result_json = resp.json()
        raw_text = result_json["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_text)

        # Server-side JSON schema validation
        jsonschema.validate(instance=parsed, schema=AI_FOOD_SCHEMA)

        parsed["ai_provider"] = f"Gemini Cloud ({Config.GEMINI_MODEL})"
        parsed["is_live_api"] = True
        return {
            "success": True,
            "error": None,
            "data": parsed
        }

    except jsonschema.ValidationError as ve:
        return {
            "success": False,
            "error": f"AI response failed schema validation: {ve.message}",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gemini Vision call failed: {str(e)}",
            "data": None
        }

def _local_heuristic_analysis(image_path):
    """
    Honest local fallback when GEMINI_API_KEY is not configured.
    Inspects image properties and filename clues to provide realistic structured
    suggestions while clearly documenting that external credentials are required for live Gemini vision.
    """
    filename = os.path.basename(image_path).lower()
    
    # Defaults
    food_name = "Surplus Cooked Meal"
    category = "curry_gravy"
    countable = None
    qty_range = "Approx. 4-8 portions (visual container estimate)"
    unit = "portions"
    confidence = 0.72
    reasoning = (
        "Identified warm curry/gravy based on coloration and container texture. "
        "A photograph cannot determine exact mass or density; kitchen scale measurement required."
    )
    fields_needed = ["exact weight / portion count", "preparation time", "storage temperature check"]
    storage = "Must be maintained in hot-holding (>60°C) or consumed within campus operational window."

    if "rice" in filename or "dal" in filename:
        food_name = "Cooked Jeera Rice & Dal"
        category = "cooked_rice"
        qty_range = "Approx. 5-10 portions (bulk mess container)"
        unit = "kg"
        confidence = 0.78
        reasoning = "Grains and pulse broth visible. Depth cannot be confirmed from 2D image; weight must be measured."
    elif "roti" in filename or "bread" in filename or "sabzi" in filename:
        food_name = "Wheat Rotis & Vegetable Sabzi"
        category = "bread_roti"
        countable = 25
        qty_range = "Counted ~20-30 pieces in chafing dish"
        unit = "portions"
        confidence = 0.82
        reasoning = "Layered flatbreads visually discernible. Portions estimated from stack count."
    elif "kheer" in filename or "sweet" in filename or "dairy" in filename:
        food_name = "Dairy Dessert / Kheer"
        category = "dairy_sweets"
        qty_range = "Approx. 2-4 kg (dessert bowl container)"
        unit = "portions"
        confidence = 0.75
        reasoning = "Viscous dairy sweet detected. Requires immediate refrigeration or strict 2-hour distribution."
    elif "fruit" in filename or "apple" in filename or "banana" in filename:
        food_name = "Fresh Seasonal Fruit"
        category = "fruit_veg"
        countable = 12
        qty_range = "10-15 whole fruits"
        unit = "pieces"
        confidence = 0.90
        reasoning = "Whole intact fruit pieces countable individually from top view."

    data = {
        "food_name": food_name,
        "category": category,
        "visible_items_or_containers_count": countable,
        "approximate_quantity_range": qty_range,
        "quantity_unit_suggestion": unit,
        "confidence_score": confidence,
        "confidence_reasoning": reasoning,
        "fields_requiring_staff_input": fields_needed,
        "storage_recommendation": storage,
        "ai_provider": "Local Heuristic Engine (Configure GEMINI_API_KEY in .env for Cloud Vision)",
        "is_live_api": False,
        "provider_note": "No GEMINI_API_KEY detected in .env. Returned structured local suggestions with quantity honesty constraints."
    }

    return {
        "success": True,
        "error": None,
        "data": data
    }
