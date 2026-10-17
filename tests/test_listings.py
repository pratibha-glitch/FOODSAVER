import unittest
import os
import tempfile
from datetime import datetime, timedelta
from app import app
from database import init_db

class TestListings(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        app.config['DATABASE_PATH'] = self.db_path
        app.config['TESTING'] = True
        init_db(self.db_path)
        self.client = app.test_client()

        # Login as staff
        self.client.post('/api/auth/login', json={
            'identifier': 'staff_north',
            'password': 'StaffPassword123!'
        })

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_create_available_requires_safety_checklist(self):
        # Attempt to publish as 'available' without checklist
        deadline = (datetime.now() + timedelta(hours=3)).isoformat()
        resp = self.client.post('/api/staff/listings', json={
            'food_name': 'Paneer Butter Masala',
            'category': 'curry_gravy',
            'quantity_value': 5.0,
            'quantity_unit': 'kg',
            'quantity_source': 'measured',
            'location_id': 1,
            'operational_deadline': deadline,
            'status': 'available',
            'safety_checklist_confirmed': 0  # Missing checklist!
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be published as 'available'", resp.get_json()['error'])

    def test_create_available_with_safety_checklist_success(self):
        deadline = (datetime.now() + timedelta(hours=3)).isoformat()
        resp = self.client.post('/api/staff/listings', json={
            'food_name': 'Vegetable Biryani',
            'category': 'cooked_rice',
            'quantity_value': 8.0,
            'quantity_unit': 'kg',
            'quantity_source': 'measured',
            'location_id': 1,
            'operational_deadline': deadline,
            'status': 'available',
            'safety_checklist_confirmed': 1
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('listing_id', data)

    def test_cancel_listing_requires_reason(self):
        # Create a listing first
        deadline = (datetime.now() + timedelta(hours=3)).isoformat()
        create_resp = self.client.post('/api/staff/listings', json={
            'food_name': 'Dal Fry',
            'category': 'curry_gravy',
            'quantity_value': 3.0,
            'quantity_unit': 'kg',
            'quantity_source': 'measured',
            'location_id': 1,
            'operational_deadline': deadline,
            'status': 'available',
            'safety_checklist_confirmed': 1
        })
        listing_id = create_resp.get_json()['listing_id']

        # Cancel with empty reason
        cancel_resp = self.client.post(f'/api/listings/{listing_id}/cancel', json={'reason': ''})
        self.assertEqual(cancel_resp.status_code, 400)

        # Cancel with valid reason
        cancel_resp2 = self.client.post(f'/api/listings/{listing_id}/cancel', json={'reason': 'Accidental duplicate entry by mess supervisor.'})
        self.assertEqual(cancel_resp2.status_code, 200)

    def test_get_listing_details_endpoint(self):
        # Fetch details for seeded listing 1
        resp = self.client.get('/api/listings/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('listing', data)
        self.assertIn('audit_logs', data)
        self.assertIn('urgency', data['listing'])
        self.assertEqual(data['listing']['id'], 1)

if __name__ == '__main__':
    unittest.main()
