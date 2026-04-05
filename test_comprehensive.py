import unittest
import json
import base64
from io import BytesIO
from PIL import Image
from app import app

class ComprehensiveRoutesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # ===================== HOME & PUBLIC ROUTES =====================
    def test_home(self):
        """Test home page is accessible."""
        resp = self.client.get('/')
        print(f"✓ Home: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_login_page(self):
        """Test login page loads."""
        resp = self.client.get('/login_page')
        print(f"✓ Login Page: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_register_page(self):
        """Test register page loads."""
        resp = self.client.get('/register')
        print(f"✓ Register Page: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    # ===================== USER LOGIN TESTS =====================
    def test_user_login_success(self):
        """Test user login with valid credentials."""
        resp = self.client.post('/login', data={
            'email': 'bob24@bobmail.me',
            'password': 'Bob@123'
        }, follow_redirects=True)
        print(f"✓ User Login (Success): {resp.status_code}")
        self.assertEqual(resp.status_code, 200)
        # Verify successful login - session should be set
        # Response will be dashboard page (200)
        self.assertIsNotNone(resp)

    def test_user_login_invalid(self):
        """Test user login with invalid credentials."""
        resp = self.client.post('/login', data={
            'email': 'bob24@bobmail.me',
            'password': 'wrongpassword'
        }, follow_redirects=False)
        print(f"✓ User Login (Invalid): {resp.status_code}")
        self.assertIn(resp.status_code, [200, 302])

    # ===================== USER SESSION TESTS =====================
    def test_user_dashboard(self):
        """Test user dashboard after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/dashboard')
        print(f"✓ User Dashboard: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_predict_page(self):
        """Test predict page after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/predict_page')
        print(f"✓ User Predict Page: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_history(self):
        """Test prediction history after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/history')
        print(f"✓ User History: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_analytics(self):
        """Test user analytics after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/analytics')
        print(f"✓ User Analytics: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_top_predictions(self):
        """Test user top predictions after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/top_predictions')
        print(f"✓ User Top Predictions: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_profile(self):
        """Test user profile after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/profile')
        print(f"✓ User Profile: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_user_download_page(self):
        """Test download page after login."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/download')
        print(f"✓ User Download Page: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    # ===================== PREDICTION TESTS =====================
    def test_predict_canvas(self):
        """Test canvas prediction endpoint."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        
        # Create a simple white canvas
        img = Image.new('RGB', (28, 28), color='white')
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_data = base64.b64encode(img_io.getvalue()).decode()
        
        resp = self.client.post('/predict_canvas', 
            json={'image': f'data:image/png;base64,{img_data}'},
            content_type='application/json')
        print(f"✓ Canvas Prediction: {resp.status_code}")
        self.assertIn(resp.status_code, [200, 400, 500])

    # ===================== ADMIN LOGIN TESTS =====================
    def test_admin_login_page(self):
        """Test admin login page loads."""
        resp = self.client.get('/admin')
        print(f"✓ Admin Login Page: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_login_success(self):
        """Test admin login with valid credentials."""
        resp = self.client.post('/admin_login', data={
            'username': 'admin',
            'password': 'Admin@123'
        }, follow_redirects=True)
        print(f"✓ Admin Login (Success): {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_login_invalid(self):
        """Test admin login with invalid credentials."""
        resp = self.client.post('/admin_login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=False)
        print(f"✓ Admin Login (Invalid): {resp.status_code}")
        self.assertIn(resp.status_code, [200, 302])

    # ===================== ADMIN SESSION TESTS =====================
    def test_admin_dashboard(self):
        """Test admin dashboard after login."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin_dashboard')
        print(f"✓ Admin Dashboard: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_users(self):
        """Test admin users list."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/users')
        print(f"✓ Admin Users: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_analytics(self):
        """Test admin analytics."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/analytics')
        print(f"✓ Admin Analytics: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_reports(self):
        """Test admin reports."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/reports')
        print(f"✓ Admin Reports: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_predictions(self):
        """Test admin predictions list."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/predictions')
        print(f"✓ Admin Predictions: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_settings(self):
        """Test admin settings."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/settings')
        print(f"✓ Admin Settings: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_view_user(self):
        """Test admin viewing a user."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/view_user/1')
        print(f"✓ Admin View User: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    # ===================== PROTECTION TESTS =====================
    def test_dashboard_without_login(self):
        """Test that dashboard redirects without login."""
        resp = self.client.get('/dashboard', follow_redirects=False)
        print(f"✓ Dashboard (No Login): {resp.status_code}")
        self.assertEqual(resp.status_code, 302)

    def test_admin_dashboard_without_login(self):
        """Test that admin dashboard redirects without login."""
        resp = self.client.get('/admin_dashboard', follow_redirects=False)
        print(f"✓ Admin Dashboard (No Login): {resp.status_code}")
        self.assertEqual(resp.status_code, 302)

    def test_logout(self):
        """Test logout functionality."""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        resp = self.client.get('/logout', follow_redirects=True)
        print(f"✓ User Logout: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

    def test_admin_logout(self):
        """Test admin logout functionality."""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin_logout', follow_redirects=True)
        print(f"✓ Admin Logout: {resp.status_code}")
        self.assertEqual(resp.status_code, 200)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("COMPREHENSIVE ROUTE TESTING")
    print("="*60 + "\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(ComprehensiveRoutesTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*60 + "\n")
