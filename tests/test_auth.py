import unittest
import os
import tempfile
from app import app
from database import init_db

class TestAuth(unittest.TestCase):
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

    def test_login_success_admin(self):
        resp = self.client.post('/api/auth/login', json={
            'identifier': 'admin',
            'password': 'AdminPassword123!'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'admin')

    def test_login_invalid_password(self):
        resp = self.client.post('/api/auth/login', json={
            'identifier': 'admin',
            'password': 'WrongPassword!'
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data['success'])

    def test_role_protection_admin_endpoint(self):
        # 1. Unauthenticated request should be 401
        resp = self.client.get('/api/admin/users')
        self.assertEqual(resp.status_code, 401)

        # 2. Login as volunteer
        self.client.post('/api/auth/login', json={
            'identifier': 'volunteer_priya',
            'password': 'VolunteerPassword123!'
        })

        # 3. Volunteer accessing admin endpoint should get 403 Forbidden
        resp2 = self.client.get('/api/admin/users')
        self.assertEqual(resp2.status_code, 403)

    def test_logout(self):
        self.client.post('/api/auth/login', json={
            'identifier': 'volunteer_priya',
            'password': 'VolunteerPassword123!'
        })
        resp = self.client.post('/api/auth/logout')
        self.assertEqual(resp.status_code, 200)
        
        # Me endpoint should now return authenticated: false
        me_resp = self.client.get('/api/auth/me')
        self.assertFalse(me_resp.get_json()['authenticated'])

if __name__ == '__main__':
    unittest.main()
