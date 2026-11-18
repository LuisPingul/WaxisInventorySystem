from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile
from config.security import sanitize_csv_cell
from forecasting.models import AIProcurementAlert
from inventory.models import Ingredient
from procurement.models import ProcurementRequest
from suppliers.models import Supplier


class VibeSecSecurityTestSuite(TestCase):
    """
    Automated security verification suite enforcing VibeSec-Skill controls:
      1. Security Headers & Cache-Control on authenticated responses
      2. CSRF / Method Enforcement (@require_POST on all state-changing endpoints)
      3. Vertical & Horizontal Role-Based Access Control (RBAC)
      4. Account Lifecycle Session Revocation on user deactivation
      5. XSS Attribute Validation & CSV Formula Injection Sanitization
    """

    def setUp(self):
        self.dev_user = User.objects.create_user(username="dev_sec", password="StrongPassword!123")
        Profile.objects.update_or_create(user=self.dev_user, defaults={"role": Profile.Role.DEVELOPER})

        self.owner_user = User.objects.create_user(username="owner_sec", password="StrongPassword!123")
        Profile.objects.update_or_create(user=self.owner_user, defaults={"role": Profile.Role.OWNER})

        self.manager_user = User.objects.create_user(username="mgr_sec", password="StrongPassword!123")
        Profile.objects.update_or_create(user=self.manager_user, defaults={"role": Profile.Role.MANAGER})

        self.crew_user = User.objects.create_user(username="crew_sec", password="StrongPassword!123")
        Profile.objects.update_or_create(user=self.crew_user, defaults={"role": Profile.Role.CREW})

        self.supplier = Supplier.objects.create(
            company_name="Waxi Safe Foods",
            contact_person="Juan",
            phone="09171234567",
            category=Supplier.Category.MEAT,
        )
        self.ingredient = Ingredient.objects.create(
            name="Chicken Breast",
            category=Ingredient.Category.CHILLED,
            quantity=Decimal("20.00"),
            unit="kg",
            minimum_stock=Decimal("5.00"),
            maximum_stock=Decimal("40.00"),
            unit_cost=Decimal("220.00"),
            supplier_fk=self.supplier,
        )
        self.pr = ProcurementRequest.objects.create(
            ingredient=self.ingredient,
            supplier=self.supplier,
            requested_quantity=Decimal("15.00"),
            requested_by=self.manager_user,
        )
        self.alert = AIProcurementAlert.objects.create(
            ingredient=self.ingredient,
            suggested_quantity=Decimal("15.00"),
            risk=AIProcurementAlert.Risk.HIGH,
            reason="Test stockout risk",
        )

    def test_security_headers_and_authenticated_no_store_cache(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertIn("Permissions-Policy", response)

        self.client.force_login(self.owner_user)
        auth_resp = self.client.get(reverse("dashboard:home"))
        self.assertIn("no-store", auth_resp["Cache-Control"])

    def test_state_changing_endpoints_reject_get_requests(self):
        self.client.force_login(self.owner_user)
        post_only_urls = [
            reverse("accounts:logout"),
            reverse("accounts:toggle_user", args=[self.crew_user.pk]),
            reverse("procurement_approve", args=[self.pr.pk]),
            reverse("procurement_reject", args=[self.pr.pk]),
            reverse("procurement_ordered", args=[self.pr.pk]),
            reverse("procurement_delivered", args=[self.pr.pk]),
            reverse("forecasting:alert_approve", args=[self.alert.pk]),
            reverse("forecasting:alert_reject", args=[self.alert.pk]),
            reverse("suppliers:toggle", args=[self.supplier.pk]),
        ]
        for url in post_only_urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 405)

    def test_vertical_access_control_blocks_crew_from_management_endpoints(self):
        self.client.force_login(self.crew_user)
        restricted_urls = [
            reverse("ingredient_detail", args=[self.ingredient.pk]),
            reverse("inventory_search_partial"),
            reverse("reports"),
            reverse("dashboard:ai_summary"),
            reverse("accounts:users"),
            reverse("suppliers:list"),
        ]
        for url in restricted_urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 403)

    def test_owner_cannot_escalate_to_or_disable_developer(self):
        self.client.force_login(self.owner_user)

        # 1. Owner cannot disable Developer via toggle_user
        resp = self.client.post(reverse("accounts:toggle_user", args=[self.dev_user.pk]))
        self.assertEqual(resp.status_code, 403)
        self.dev_user.refresh_from_db()
        self.assertTrue(self.dev_user.is_active)

        # 2. Owner cannot forge POST to create a DEVELOPER account
        create_resp = self.client.post(
            reverse("accounts:create_user"),
            {
                "username": "rogue_dev",
                "first_name": "Rogue",
                "last_name": "Dev",
                "email": "rogue@example.com",
                "password": "StrongPassword!123",
                "role": Profile.Role.DEVELOPER,
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="rogue_dev").exists())

    def test_deactivating_user_immediately_revokes_active_sessions(self):
        crew_client = Client()
        crew_client.force_login(self.crew_user)
        crew_session_key = crew_client.session.session_key
        self.assertTrue(Session.objects.filter(session_key=crew_session_key).exists())

        # Owner disables crew_user
        self.client.force_login(self.owner_user)
        resp = self.client.post(reverse("accounts:toggle_user", args=[self.crew_user.pk]))
        self.assertEqual(resp.status_code, 302)

        self.crew_user.refresh_from_db()
        self.assertFalse(self.crew_user.is_active)
        self.assertFalse(Session.objects.filter(session_key=crew_session_key).exists())

    def test_xss_radar_id_validation_and_csv_formula_sanitization(self):
        self.client.force_login(self.manager_user)
        xss_payload = '"><script>alert(1)</script>'
        resp = self.client.get(reverse("forecasting:procurement_radar"), {"radar_id": xss_payload})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn('id="procurement-radar"', body)

        # CSV Formula Injection checks
        self.assertEqual(sanitize_csv_cell("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")
        self.assertEqual(sanitize_csv_cell("+SUM(A1:A2)"), "'+SUM(A1:A2)")
        self.assertEqual(sanitize_csv_cell("@IMPORTXML()"), "'@IMPORTXML()")
        self.assertEqual(sanitize_csv_cell("Normal Ingredient"), "Normal Ingredient")
