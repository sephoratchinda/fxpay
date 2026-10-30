"""API integration tests - run with `python manage.py test`."""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class ApiTests(APITestCase):
    def setUp(self):
        User.objects.create_user("alice", "a@x.com", "password123")
        r = self.client.post("/api/auth/login/", {"username": "alice", "password": "password123"})
        self.token = r.data["access"]

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_register_and_login(self):
        r = self.client.post("/api/auth/register/", {"username": "bob", "email": "b@x.com", "password": "password123"})
        self.assertEqual(r.status_code, 201)
        self.assertIn("access", self.client.post("/api/auth/login/", {"username": "bob", "password": "password123"}).data)

    def test_bad_login(self):
        self.assertEqual(self.client.post("/api/auth/login/", {"username": "alice", "password": "nope"}).status_code, 401)

    def test_protected_requires_jwt(self):
        self.assertEqual(self.client.get("/api/payments/").status_code, 401)

    def test_payment_flow(self):
        self.auth()
        sim = self.client.post("/api/payments/simulate/", {"channel": "swift", "amount": 5000, "from_ccy": "USD", "to_ccy": "EUR"}, format="json")
        self.assertEqual(sim.status_code, 200)
        tx = self.client.post("/api/payments/", {"channel": "swift", "amount": 5000, "from_ccy": "USD", "to_ccy": "EUR", "recipient_name": "ACME"}, format="json")
        self.assertEqual(tx.status_code, 201)
        self.assertEqual(self.client.post(f"/api/payments/{tx.data['id']}/advance/").data["status"], "COMPLETED")
        self.assertEqual(len(self.client.get("/api/payments/").data), 1)

    def test_validation_errors(self):
        self.auth()
        r = self.client.post("/api/payments/simulate/", {"channel": "swift", "amount": -1, "from_ccy": "USD", "to_ccy": "EUR"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/optimizer/compare/", {"amount": 100, "from_ccy": "USD", "to_ccy": "USD"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_card_over_limit_rejected(self):
        self.auth()
        r = self.client.post("/api/payments/", {"channel": "card", "amount": 90000, "from_ccy": "USD", "to_ccy": "EUR"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_users_are_isolated(self):
        self.auth()
        self.client.post("/api/fx/exposures/", {"currency": "EUR", "amount": 1000, "direction": "RECEIVABLE", "due_days": 30}, format="json")
        User.objects.create_user("eve", "e@x.com", "password123")
        tok = self.client.post("/api/auth/login/", {"username": "eve", "password": "password123"}).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        self.assertEqual(self.client.get("/api/fx/exposures/").data, [])

    def test_fx_endpoints(self):
        self.auth()
        self.assertEqual(self.client.post("/api/fx/pnl/", {"amount": 1000, "booked_rate": 1.1, "new_rate": 1.2, "direction": "RECEIVABLE"}, format="json").data["outcome"], "gain")
        self.assertEqual(self.client.post("/api/fx/forward/", {"base": "EUR", "quote": "USD", "amount": 1000, "tenor_days": 90, "save": True}, format="json").status_code, 200)
        self.assertEqual(len(self.client.get("/api/fx/forwards/").data), 1)
        self.assertEqual(self.client.post("/api/fx/scenarios/", {"base": "EUR", "quote": "USD", "days": 60}, format="json").status_code, 200)

    def test_dashboard_with_seed_and_ai(self):
        self.auth()
        self.client.post("/api/demo/seed/")
        d = self.client.get("/api/dashboard/").data
        self.assertEqual(d["kpis"]["transactions"], 25)
        self.assertGreater(d["kpis"]["fx_risk_score"], 0)
        r = self.client.post("/api/ai/recommend/", {"amount": 8000, "from_ccy": "USD", "to_ccy": "INR", "urgency": 1}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.data["risk"]["level"], ["Low", "Medium", "High"])
        self.assertEqual(len(self.client.get("/api/ai/history/").data), 1)
