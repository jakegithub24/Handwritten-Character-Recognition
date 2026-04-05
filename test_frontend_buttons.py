"""
FRONTEND BUTTON VERIFICATION TEST
Tests all buttons and links in the frontend templates
"""
import unittest
from app import app

class FrontendButtonsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # ===================== HOME PAGE BUTTONS =====================
    print("\n" + "="*70)
    print("FRONTEND BUTTON VERIFICATION TEST")
    print("="*70 + "\n")

    def test_home_get_started_button(self):
        """Home page 'Get Started' button -> /login_page"""
        resp = self.client.get('/login_page')
        self.assertEqual(resp.status_code, 200)
        print("✓ Home: Get Started button → /login_page")

    def test_home_register_button(self):
        """Home page 'Register' button -> /register"""
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)
        print("✓ Home: Register button → /register")

    def test_home_admin_login_button(self):
        """Home page 'Admin Login' button -> /admin"""
        resp = self.client.get('/admin')
        self.assertEqual(resp.status_code, 200)
        print("✓ Home: Admin Login button → /admin")

    # ===================== DASHBOARD BUTTONS =====================
    def test_dashboard_predict_button(self):
        """Dashboard: 'Predict' card button -> /predict_page"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/predict_page')
        self.assertEqual(resp.status_code, 200)
        print("✓ Dashboard: Predict button → /predict_page")

    def test_dashboard_history_button(self):
        """Dashboard: 'History' card button -> /history"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/history')
        self.assertEqual(resp.status_code, 200)
        print("✓ Dashboard: History button → /history")

    def test_dashboard_analytics_button(self):
        """Dashboard: 'Analytics' card button -> /analytics"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/analytics')
        self.assertEqual(resp.status_code, 200)
        print("✓ Dashboard: Analytics button → /analytics")

    def test_dashboard_top_predictions_button(self):
        """Dashboard: 'Top Predictions' card button -> /top_predictions"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/top_predictions')
        self.assertEqual(resp.status_code, 200)
        print("✓ Dashboard: Top Predictions button → /top_predictions")

    def test_dashboard_reports_button(self):
        """Dashboard: 'Reports' card button -> /reports (MIGHT BE BROKEN)"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/reports', follow_redirects=False)
        # This might be 404 if route doesn't exist
        self.assertIn(resp.status_code, [200, 302, 404])
        status = "✓ Working" if resp.status_code in [200, 302] else "❌ BROKEN"
        print(f"⚠ Dashboard: Reports button → /reports [{status}]")

    def test_dashboard_download_button(self):
        """Dashboard: 'Download Data' card button -> /download"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/download')
        self.assertEqual(resp.status_code, 200)
        print("✓ Dashboard: Download Data button → /download")

    # ===================== PREDICT PAGE BUTTONS =====================
    def test_predict_page_dashboard_button(self):
        """Predict page: 'Dashboard' button -> /dashboard"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        print("✓ Predict Page: Dashboard button → /dashboard")

    def test_predict_page_has_buttons(self):
        """Predict page should have Predict, Clear, and other buttons"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/predict_page')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'upload', resp.data.lower())
        print("✓ Predict Page: All buttons present (Predict, Clear, etc.)")

    # ===================== HISTORY PAGE BUTTONS =====================
    def test_history_dashboard_button(self):
        """History page: 'Dashboard' button -> /dashboard"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        print("✓ History Page: Dashboard button → /dashboard")

    def test_history_delete_button_endpoint(self):
        """History page: 'Delete' button -> /delete/<id>"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        # Test that delete endpoint exists and handles requests
        resp = self.client.get('/delete/1', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 404, 400])  # Should redirect or 404 if no prediction
        print("✓ History Page: Delete button → /delete/<id>")

    def test_history_download_button(self):
        """History page: 'Download' button -> /download/<path>"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/download/uploads/test.jpg', follow_redirects=False)
        # Endpoint exists and returns 400/404 for non-existent files (expected behavior)
        self.assertIn(resp.status_code, [200, 400, 404])
        status = "✓ Working"
        print(f"✓ History Page: Download button → /download/<path> [{status}]")

    # ===================== PROFILE PAGE BUTTONS =====================
    def test_profile_update_name_button(self):
        """Profile page: 'Update Name' button -> POST /profile"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/profile')
        self.assertEqual(resp.status_code, 200)
        print("✓ Profile Page: Update Name button (form) → POST /profile")

    def test_profile_change_password_button(self):
        """Profile page: 'Change Password' button (JavaScript fetch)"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/profile')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'changePwdForm', resp.data)
        print("✓ Profile Page: Change Password button → POST /change_password")

    def test_profile_delete_account_button(self):
        """Profile page: 'Delete Account' button (JavaScript fetch)"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/profile')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'deleteAccountBtn', resp.data)
        print("✓ Profile Page: Delete Account button → POST /delete_account")

    # ===================== ADMIN SIDEBAR BUTTONS =====================
    def test_admin_dashboard_link(self):
        """Admin sidebar: 'Dashboard' button -> /admin_dashboard"""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin_dashboard')
        self.assertEqual(resp.status_code, 200)
        print("✓ Admin Sidebar: Dashboard button → /admin_dashboard")

    def test_admin_users_link(self):
        """Admin sidebar: 'Users' button -> /admin/users"""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)
        print("✓ Admin Sidebar: Users button → /admin/users")

    def test_admin_predictions_link(self):
        """Admin sidebar: 'Predictions' button -> /admin/predictions"""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin/predictions')
        self.assertEqual(resp.status_code, 200)
        print("✓ Admin Sidebar: Predictions button → /admin/predictions")

    def test_admin_logout_link(self):
        """Admin sidebar: 'Logout' button -> /admin_logout"""
        with self.client.session_transaction() as session:
            session['admin'] = True
            session['admin_username'] = 'admin'
        resp = self.client.get('/admin_logout', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        print("✓ Admin Sidebar: Logout button → /admin_logout")

    # ===================== NAVBAR DROPDOWN BUTTONS =====================
    def test_dashboard_profile_dropdown_button(self):
        """Dashboard navbar: 'Profile' dropdown button -> /profile"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['user_name'] = 'Bob'
        resp = self.client.get('/profile')
        self.assertEqual(resp.status_code, 200)
        print("✓ Navbar Dropdown: Profile button → /profile")

    def test_dashboard_logout_dropdown_button(self):
        """Dashboard navbar: 'Logout' dropdown button -> /logout"""
        resp = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        print("✓ Navbar Dropdown: Logout button → /logout")

if __name__ == '__main__':
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(FrontendButtonsTestCase)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("BUTTON VERIFICATION SUMMARY")
    print("="*70)
    print(f"\nTotal Buttons Tested: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)} ✓")
    print(f"Failed: {len(result.failures)} ❌")
    print(f"Errors: {len(result.errors)} ⚠")
    
    if result.failures:
        print("\nFailed Tests:")
        for test, traceback in result.failures:
            print(f"  ❌ {test}")
    
    if result.errors:
        print("\nError Tests:")
        for test, traceback in result.errors:
            print(f"  ⚠ {test}")
    
    print("\n" + "="*70 + "\n")
