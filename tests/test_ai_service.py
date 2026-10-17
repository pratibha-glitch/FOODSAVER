import unittest
import os
import jsonschema
from services.ai_vision import AI_FOOD_SCHEMA, analyze_food_photo

class TestAiService(unittest.TestCase):
    def test_schema_valid_sample(self):
        valid_payload = {
            "food_name": "Cooked Rice & Dal",
            "category": "cooked_rice",
            "visible_items_or_containers_count": None,
            "approximate_quantity_range": "Approx. 4-8 portions (container estimate)",
            "quantity_unit_suggestion": "kg",
            "confidence_score": 0.85,
            "confidence_reasoning": "Visible grain structure and deep metal chafing dish.",
            "fields_requiring_staff_input": ["exact measured mass", "cooking time", "temperature check"],
            "storage_recommendation": "Maintain hot holding >60C"
        }
        # Should not raise
        jsonschema.validate(instance=valid_payload, schema=AI_FOOD_SCHEMA)

    def test_schema_rejects_invalid_category(self):
        invalid_payload = {
            "food_name": "Mysterious Food",
            "category": "unknown_invalid_category",
            "visible_items_or_containers_count": None,
            "approximate_quantity_range": None,
            "confidence_score": 0.5,
            "confidence_reasoning": "Low visibility",
            "fields_requiring_staff_input": []
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_payload, schema=AI_FOOD_SCHEMA)

    def test_local_heuristic_analysis_on_preset_photo(self):
        preset_path = os.path.join('static', 'uploads', 'preset_dal_rice.jpg')
        if os.path.exists(preset_path):
            result = analyze_food_photo(preset_path)
            self.assertTrue(result['success'])
            data = result['data']
            self.assertIn('food_name', data)
            self.assertIn('category', data)
            self.assertIn('confidence_reasoning', data)
            self.assertIn('fields_requiring_staff_input', data)
            # Must be marked as AI suggestion / local mode
            self.assertFalse(data['is_live_api'])

if __name__ == '__main__':
    unittest.main()
