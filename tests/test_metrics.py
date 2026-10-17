import unittest
import os
import tempfile
from app import app
from database import init_db
from services.metrics_service import get_system_metrics

class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        app.config['DATABASE_PATH'] = self.db_path
        app.config['TESTING'] = True
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_unclaimed_listings_not_counted_as_collected(self):
        with app.app_context():
            # Fresh seeded database has 1 available listing (7.5 kg), 1 claimed (35 portions), 1 collected (12.0 kg)
            metrics = get_system_metrics()
            
            # Only the collected listing should be counted in total_kg_collected
            self.assertEqual(metrics['total_kg_collected'], 12.0)
            self.assertEqual(metrics['completed_pickups'], 1)
            self.assertEqual(metrics['active_available_listings'], 1)

    def test_unit_separation(self):
        with app.app_context():
            metrics = get_system_metrics()
            breakdown = metrics['collected_quantity_by_unit']
            
            # kg must be tracked in kg
            self.assertIn('kg', breakdown)
            self.assertEqual(breakdown['kg']['total_quantity'], 12.0)

    def test_defensible_co2_calculation(self):
        with app.app_context():
            # 12.0 kg collected * 2.5 kg CO2-eq/kg = 30.0 kg CO2-eq avoided
            metrics = get_system_metrics()
            co2 = metrics['environmental_impact']['co2_prevented_kg']
            self.assertEqual(co2, 30.0)
            self.assertIn('FAO Food Wastage Footprint methodology', metrics['environmental_impact']['calculation_basis'])

if __name__ == '__main__':
    unittest.main()
