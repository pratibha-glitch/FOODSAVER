import unittest
import os
import tempfile
from app import app
from database import init_db
import models

class TestClaims(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        app.config['DATABASE_PATH'] = self.db_path
        app.config['TESTING'] = True
        init_db(self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_unverified_volunteer_cannot_claim(self):
        # volunteer_pending is unverified (is_verified = 0)
        self.client.post('/api/auth/login', json={
            'identifier': 'volunteer_pending',
            'password': 'VolunteerPassword123!'
        })

        resp = self.client.post('/api/volunteer/listings/1/claim')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('pending administrator verification', resp.get_json()['error'])

    def test_verified_volunteer_claim_success(self):
        # volunteer_priya is verified
        self.client.post('/api/auth/login', json={
            'identifier': 'volunteer_priya',
            'password': 'VolunteerPassword123!'
        })

        resp = self.client.post('/api/volunteer/listings/1/claim')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        with app.app_context():
            listing = models.get_listing_by_id(1)
            self.assertEqual(listing['status'], 'claimed')
            self.assertEqual(listing['claimed_by_volunteer_id'], 4)

    def test_duplicate_claim_prevention_concurrency(self):
        with app.app_context():
            # First volunteer claims listing 1
            success1, msg1 = models.claim_listing(1, volunteer_id=4)
            self.assertTrue(success1)

            # Second volunteer tries to claim the same listing 1 concurrently
            success2, msg2 = models.claim_listing(1, volunteer_id=5)
            self.assertFalse(success2)
            self.assertIn("cannot be claimed because its current status is 'claimed'", msg2)

    def test_full_collection_lifecycle(self):
        with app.app_context():
            # 1. Claim
            success, _ = models.claim_listing(1, volunteer_id=4)
            self.assertTrue(success)

            # 2. Start pickup
            success, _ = models.start_pickup_progress(1, volunteer_id=4)
            self.assertTrue(success)
            listing = models.get_listing_by_id(1)
            self.assertEqual(listing['status'], 'pickup_in_progress')

            # 3. Confirm collection with actual collected quantity
            success, _ = models.complete_collection(1, user_id=4, actual_quantity_value=7.2, actual_quantity_unit='kg')
            self.assertTrue(success)
            
            # 4. Verify collected record
            listing_final = models.get_listing_by_id(1)
            self.assertEqual(listing_final['status'], 'collected')
            self.assertEqual(listing_final['actual_collected_quantity_value'], 7.2)
            self.assertEqual(listing_final['actual_collected_quantity_unit'], 'kg')

if __name__ == '__main__':
    unittest.main()
