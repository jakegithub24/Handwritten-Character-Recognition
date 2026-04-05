import unittest
import tempfile
import os
from app import app

class FlaskRoutesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_home(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_login_page(self):
        resp = self.client.get('/login_page')
        self.assertEqual(resp.status_code, 200)

    def test_register_get(self):
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_redirect(self):
        resp = self.client.get('/dashboard', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401])

    def test_predict_page_redirect(self):
        resp = self.client.get('/predict_page', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401])

    def test_history_redirect(self):
        resp = self.client.get('/history', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401])

    def test_analytics(self):
        resp = self.client.get('/analytics', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401, 200])

    def test_top_predictions(self):
        resp = self.client.get('/top_predictions', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401, 200])

    def test_profile_redirect(self):
        resp = self.client.get('/profile', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401])

    def test_download_page(self):
        resp = self.client.get('/download')
        self.assertEqual(resp.status_code, 200)

    def test_admin_login(self):
        resp = self.client.get('/admin')
        self.assertEqual(resp.status_code, 200)

    def test_admin_dashboard_redirect(self):
        resp = self.client.get('/admin_dashboard', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401])

    def test_logout(self):
        resp = self.client.get('/logout', follow_redirects=True)
        self.assertIn(resp.status_code, [200, 302])

    # --- Additional Admin and User Route Tests ---
    def test_admin_users(self):
        resp = self.client.get('/admin/users')
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_analytics(self):
        resp = self.client.get('/admin/analytics')
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_reports(self):
        resp = self.client.get('/admin/reports')
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_predictions(self):
        resp = self.client.get('/admin/predictions')
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_settings(self):
        resp = self.client.get('/admin/settings')
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_view_user(self):
        # Try with a likely non-existent user id, should not 500
        resp = self.client.get('/admin/view_user/1')
        self.assertIn(resp.status_code, [200, 302, 404])

    def test_download_report(self):
        resp = self.client.get('/download_report')
        self.assertIn(resp.status_code, [200, 302, 204, 404, 501])

if __name__ == '__main__':
    unittest.main()
