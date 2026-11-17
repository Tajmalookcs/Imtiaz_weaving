import json
import tempfile
import time
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from billing.services import LineInput, approve_invoice, create_invoice, next_invoice_number
from django.urls import reverse

from core import licence
from core.models import Company, Customer, Membership, Product
from core.testing import DEMO_PASSWORD, DEVELOPER_PASSWORD, licence_bytes, unlock_developer_pages, use_test_licensing
from fbr.models import FbrCredential
from fbr.sending import send_invoice


def make(name, ntn):
    return Company.objects.create(business_name=name, ntn=f"{ntn}-1", province="PUNJAB", address="A", invoice_prefix="AG")


class DemoProductTests(TestCase):
    def test_adds_labelled_samples_once(self):
        company = make("A", "1234567")
        out = StringIO()
        call_command("add_demo_products", stdout=out)
        self.assertIn("Added 12", out.getvalue())
        call_command("add_demo_products", stdout=StringIO())
        products = Product.objects.filter(company=company)
        self.assertEqual(products.count(), 12)
        for product in products:
            self.assertTrue(product.name.startswith("Demo "))
            product.full_clean()

    def test_needs_a_company(self):
        with self.assertRaises(CommandError):
            call_command("add_demo_products", stdout=StringIO())

    def test_several_companies_need_a_name(self):
        a = make("A", "1234567")
        b = make("B", "7654321")
        with self.assertRaises(CommandError):
            call_command("add_demo_products", stdout=StringIO())
        call_command("add_demo_products", company="b", stdout=StringIO())
        self.assertEqual(b.products.count(), 12)
        self.assertEqual(a.products.count(), 0)


class DemoDataTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.company = make("A", "1234567")
        self.user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=self.user, company=self.company, role="admin")

    def test_full_set_once_and_every_status_shows(self):
        call_command("add_demo_data", stdout=StringIO())
        call_command("add_demo_data", stdout=StringIO())
        self.assertEqual(self.company.products.count(), 12)
        # 7 demo buyers and the fixed UN-REGISTERED BUYER.
        self.assertEqual(self.company.customers.count(), 8)
        self.assertEqual(self.company.invoices.count(), 11)
        counts = {s: self.company.invoices.filter(status=s).count() for s in ["saved", "waiting", "held", "accepted", "rejected"]}
        self.assertEqual(counts, {"saved": 4, "waiting": 2, "held": 2, "accepted": 2, "rejected": 1})
        for customer in self.company.customers.filter(is_fixed=False):
            self.assertTrue(customer.name.startswith("Demo "))
            customer.full_clean()
        for invoice in self.company.invoices.all():
            self.assertTrue(invoice.is_demo)
            if invoice.fbr_invoice_number:
                self.assertTrue(invoice.fbr_invoice_number.startswith("DEMO-IRN-"))
            self.assertGreater(invoice.grand_total, 0)

    def test_screens_open_with_demo_data(self):
        call_command("add_demo_data", stdout=StringIO())
        self.client.force_login(self.user)
        for url in ["/", "/invoices/", "/invoices/new/", "/products/", "/customers/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        for invoice in self.company.invoices.all():
            self.assertEqual(self.client.get(f"/invoices/{invoice.pk}/").status_code, 200)
        self.assertContains(self.client.get("/"), "4 invoices need your approval")

    def test_new_invoice_after_demo_gets_next_number(self):
        call_command("add_demo_data", stdout=StringIO())
        self.assertEqual(next_invoice_number(self.company), "AG-000012")


class PageExpiredTests(TestCase):
    def test_stale_form_gets_a_clear_page_and_saves_nothing(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        company = make("A", "1234567")
        user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=user, company=company, role="admin")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.post("/company/", {"business_name": "CHANGED"})
        self.assertContains(response, "This page has expired", status_code=403)
        company.refresh_from_db()
        self.assertEqual(company.business_name, "A")


class BackupTests(TestCase):
    def test_refuses_inside_project_and_empty_install(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.conf import settings
        from django.test import override_settings

        with self.assertRaisesMessage(CommandError, "outside the project"):
            call_command("backup_data", str(Path(settings.BASE_DIR) / "backups"), stdout=StringIO())
        with TemporaryDirectory() as tmp:
            missing = {**settings.DATABASES["default"], "NAME": Path(tmp) / "none.sqlite3"}
            with override_settings(DATABASES={"default": missing}):
                with self.assertRaisesMessage(CommandError, "nothing to back up"):
                    call_command("backup_data", tmp, stdout=StringIO())


class SingleInstallTests(TestCase):
    def test_multi_company_and_user_screens_are_gone(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=user, company=make("A", "1234567"), role="admin")
        self.client.force_login(user)
        for path in ["/company/new/", "/users/", "/users/new/", "/switch-company/"]:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        html = self.client.get("/").content.decode()
        self.assertNotIn("Add another company", html)
        self.assertNotIn('name="company"', html)


class DemoAndRegistrationTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.key = use_test_licensing(self)
        self.company = make("A", "1234567")
        self.user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=self.user, company=self.company, role="admin")
        self.client.force_login(self.user)
        self.product = Product.objects.create(company=self.company, name="P", hs_code="9404.9000", uom="KG", sale_type="S",
                                              rate_label="18%", rate_percent=Decimal("18"), price_per_piece=Decimal("10"))
        self.customer = Customer.objects.create(company=self.company, name="B", kind="registered", ntn_cnic="7654321", province="SINDH", address="K")

    def _invoice(self):
        return create_invoice(company=self.company, customer=self.customer, invoice_date=date(2026, 11, 2),
                              lines=[LineInput(self.product, "kg", "1", "", "10")])

    def _age_demo(self, days):
        self.company.refresh_from_db()
        today = timezone.localdate()
        self.company.demo_started_on = today - timedelta(days=days)
        self.company.demo_last_seen = today
        self.company.save()

    def _upload(self, raw):
        return self.client.post("/registration/", {"licence": SimpleUploadedFile("licence.json", raw)}, follow=True)

    def _register(self):
        return self._upload(licence_bytes(self.key, self.company.ntn))

    # ---- The 15 days

    def test_demo_counts_down_and_stops_on_day_15(self):
        self.assertEqual(licence.status(self.company).days_left, 15)
        self._age_demo(14)
        state = licence.status(self.company)
        self.assertEqual((state.days_left, state.expired), (1, False))
        self._age_demo(15)
        self.assertTrue(licence.status(self.company).expired)

    def test_after_the_demo_invoices_stop_but_data_stays_open(self):
        invoice = self._invoice()
        self._age_demo(15)
        for path in ["/invoices/new/", f"/invoices/{invoice.pk}/edit/", f"/invoices/{invoice.pk}/debit-note/"]:
            self.assertRedirects(self.client.get(path), "/registration/", msg_prefix=path)
        self.assertRedirects(self.client.post(f"/invoices/{invoice.pk}/approve/"), "/registration/")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "saved")
        for path in ["/", "/invoices/", f"/invoices/{invoice.pk}/", f"/invoices/{invoice.pk}/print/", "/register/", "/customers/", "/products/", "/registration/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_moving_the_date_back_stops_the_demo(self):
        self.company.demo_started_on = timezone.localdate() - timedelta(days=20)
        self.company.demo_last_seen = timezone.localdate() + timedelta(days=5)
        self.company.save()
        state = licence.status(self.company)
        self.assertTrue(state.clock_moved_back)
        self.assertTrue(state.expired)
        self.assertContains(self.client.get("/"), "date has moved back")

    def test_sending_stops_after_the_demo(self):
        invoice = approve_invoice(self._invoice(), self.user, "SN001")
        self._age_demo(15)
        with patch("fbr.client.requests.request") as request:
            result = send_invoice(invoice)
        self.assertFalse(result.ok)
        self.assertIn("demo has ended", result.message)
        request.assert_not_called()

    # ---- DEMO marking

    def test_demo_copy_marks_print_and_screen(self):
        invoice = self._invoice()
        html = self.client.get(f"/invoices/{invoice.pk}/print/").content.decode()
        self.assertIn('<div class="stamp" aria-hidden="true">DEMO</div>', html)
        self.assertIn("DEMO VERSION.", html)
        self.assertContains(self.client.get(f"/invoices/{invoice.pk}/"), '<span class="demo-tag">DEMO</span>')

    def test_registered_copy_has_no_demo_marks(self):
        invoice = self._invoice()
        self._register()
        html = self.client.get(f"/invoices/{invoice.pk}/print/").content.decode()
        self.assertNotIn("DEMO VERSION", html)
        self.assertIn("PENDING FBR", html)
        self.assertNotContains(self.client.get(f"/invoices/{invoice.pk}/"), "demo-tag")

    # ---- Registration

    def test_right_file_ends_the_demo_even_after_it_expired(self):
        self._age_demo(30)
        self.assertContains(self._register(), "registered to Test Company")
        state = licence.status(self.company)
        self.assertTrue(state.registered)
        self.assertFalse(state.expired)
        self.assertEqual(self.client.get("/invoices/new/").status_code, 200)

    def test_bad_files_are_refused(self):
        other_key = Ed25519PrivateKey.generate()
        good = json.loads(licence_bytes(self.key, self.company.ntn))
        changed = {**good, "payload": {**good["payload"], "ntn": "7654321-0"}}
        for name, raw, text in [
            ("not json", b"hello", "a registration file"),
            ("empty", b"{}", "a registration file"),
            ("list", b"[]", "a registration file"),
            ("made with another key", licence_bytes(other_key, self.company.ntn), "registration file isn"),
            ("changed after signing", json.dumps(changed).encode(), "registration file isn"),
            ("another client's", licence_bytes(self.key, "7654321-0"), "not this company"),
            ("too large", b" " * (licence.MAX_FILE_BYTES + 1), "too large"),
        ]:
            self.assertContains(self._upload(raw), text, msg_prefix=name)
            self.assertFalse(licence.status(self.company).registered, name)
            self.assertFalse((self.licence_folder / "licence.json").exists(), name)

    def test_no_file_chosen(self):
        self.assertContains(self.client.post("/registration/", follow=True), "Choose the registration file")

    def test_a_damaged_installed_file_returns_to_demo(self):
        self._register()
        (self.licence_folder / "licence.json").write_bytes(b"broken")
        self.assertFalse(licence.status(self.company).registered)

    # ---- Production

    def test_production_needs_registration_then_a_token_and_a_tick(self):
        unlock_developer_pages(self.client)
        cred = FbrCredential(company=self.company, environment="production")
        cred.token = "prod-token-abcdefgh"
        cred.save()
        self.client.post("/fbr/mode/", {"mode": "production", "confirm": "yes"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.fbr_mode, "sandbox")
        self._register()
        self.client.post("/fbr/mode/", {"mode": "production"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.fbr_mode, "sandbox")
        self.client.post("/fbr/mode/", {"mode": "production", "confirm": "yes"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.fbr_mode, "production")

    def test_a_demo_copy_never_sends_to_production(self):
        invoice = approve_invoice(self._invoice(), self.user, "")
        self.company.fbr_mode = "production"
        self.company.save()
        invoice.refresh_from_db()
        with patch("fbr.client.requests.request") as request:
            result = send_invoice(invoice)
        self.assertFalse(result.ok)
        self.assertIn("registered copy", result.message)
        request.assert_not_called()

    def test_sandbox_setting_works_during_the_demo(self):
        unlock_developer_pages(self.client)
        self.assertContains(self.client.get("/fbr/"), "The sandbox works during the demo")

    # ---- Developer password

    def _edit(self, **changes):
        data = {"business_name": "A", "ntn": self.company.ntn, "province": "PUNJAB", "address": "A", "invoice_prefix": ""}
        data.update(changes)
        return self.client.post("/company/", data, follow=True)

    def test_company_details_need_the_developer_password(self):
        response = self.client.get("/company/")
        self.assertContains(response, "Only the developer can open this page")
        self.assertNotContains(response, 'name="business_name"')
        self.assertContains(self.client.post("/company/", {"developer_password": "wrong"}), "That password is wrong")
        self._edit(business_name="CHANGED")
        self.company.refresh_from_db()
        self.assertEqual(self.company.business_name, "A")
        self.assertContains(self.client.post("/company/", {"developer_password": DEMO_PASSWORD}, follow=True), 'name="business_name"')
        self._edit(business_name="CHANGED")
        self.company.refresh_from_db()
        self.assertEqual(self.company.business_name, "CHANGED")

    def test_unlock_ends_with_time_and_on_logout(self):
        self.client.post("/company/", {"developer_password": DEMO_PASSWORD})
        session = self.client.session
        session["developer_unlocked_until"] = time.time() - 1
        session.save()
        self.assertContains(self.client.get("/company/"), "Only the developer can open this page")
        self.client.post("/company/", {"developer_password": DEMO_PASSWORD})
        self.client.post("/logout/")
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/company/"), "Only the developer can open this page")

    def test_registration_replaces_the_demo_password(self):
        self._register()
        self.assertContains(self.client.post("/company/", {"developer_password": DEMO_PASSWORD}), "That password is wrong")
        self.assertContains(self.client.post("/company/", {"developer_password": DEVELOPER_PASSWORD}, follow=True), 'name="business_name"')

    def test_registered_ntn_cannot_be_changed(self):
        self._register()
        self.client.post("/company/", {"developer_password": DEVELOPER_PASSWORD})
        self.assertContains(self._edit(ntn="7654321-0"), "needs a new registration file")
        self.company.refresh_from_db()
        self.assertEqual(self.company.ntn, "1234567-1")

    # ---- Last invoice number

    def test_last_number_is_open_until_the_first_invoice(self):
        self.assertContains(self.client.get("/invoices/new/"), "Last invoice number from before this app")
        self.client.post("/invoices/start-number/", {"last_invoice_number": "118"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.last_invoice_number, 118)
        self.assertContains(self.client.get("/invoices/new/"), "AG-000119")
        self._invoice()
        self.assertNotContains(self.client.get("/invoices/new/"), "Last invoice number from before this app")
        self.client.post("/invoices/start-number/", {"last_invoice_number": "500"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.last_invoice_number, 118)

    def test_bad_last_number_is_refused(self):
        for bad in ["", "abc", "-1", "1.5"]:
            self.assertContains(self.client.post("/invoices/start-number/", {"last_invoice_number": bad}, follow=True), "whole number", msg_prefix=bad)
        self.company.refresh_from_db()
        self.assertEqual(self.company.last_invoice_number, 0)


class FirstRunPasswordTests(TestCase):
    DATA = {"business_name": "A", "ntn": "1234567-1", "province": "PUNJAB", "address": "Addr", "invoice_prefix": "",
            "username": "owner", "password": "Str0ng-pass-99"}

    def test_setup_needs_the_password_and_starts_the_demo(self):
        use_test_licensing(self)
        self.assertContains(self.client.post("/setup/", {**self.DATA, "developer_password": "wrong"}), "That password is wrong")
        self.assertFalse(Company.objects.exists())
        response = self.client.post("/setup/", {**self.DATA, "developer_password": DEMO_PASSWORD}, follow=True)
        self.assertContains(response, "Demo: 15 days left")
        company = Company.objects.get()
        self.assertEqual(company.demo_started_on, timezone.localdate())
        self.assertEqual(company.invoice_prefix, "")

    def test_unprepared_copy_cannot_be_set_up(self):
        use_test_licensing(self, prepared=False)
        self.assertContains(self.client.get("/setup/"), "isn't ready to set up")
        self.assertContains(self.client.post("/setup/", {**self.DATA, "developer_password": "anything"}), "isn't ready to set up")
        self.assertFalse(Company.objects.exists())


class LicensingCommandTests(TestCase):
    def test_commands_make_files_the_app_accepts(self):
        use_test_licensing(self, prepared=False)
        company = make("A", "1234567")
        with tempfile.TemporaryDirectory() as keys, patch("core.management.commands.setup_licensing.getpass", side_effect=["demo-password-long-enough"] * 2):
            call_command("setup_licensing", keys_dir=keys, stdout=StringIO())
            self.assertTrue((Path(keys) / "licence_private.pem").exists())
            self.assertFalse((self.licence_folder / "licence_private.pem").exists())
            self.assertTrue(licence.check_developer_password("demo-password-long-enough"))
            out = Path(keys) / "licence_client.json"
            with patch("core.management.commands.setup_licensing.getpass", side_effect=["client-password-long-enough"] * 2):
                call_command("make_licence", keys_dir=keys, ntn="1234567-1", name="A", out=str(out), stdout=StringIO())
            raw = out.read_bytes()
        self.assertNotIn(b"client-password-long-enough", raw)
        licence.install(company, raw)
        self.assertTrue(licence.status(company).registered)
        self.assertTrue(licence.check_developer_password("client-password-long-enough", company))

    def test_second_run_keeps_the_same_key(self):
        use_test_licensing(self, prepared=False)
        with tempfile.TemporaryDirectory() as keys, patch("core.management.commands.setup_licensing.getpass", side_effect=["demo-password-long-enough"] * 4):
            call_command("setup_licensing", keys_dir=keys, stdout=StringIO())
            first = (Path(keys) / "licence_private.pem").read_bytes()
            call_command("setup_licensing", keys_dir=keys, stdout=StringIO())
            self.assertEqual((Path(keys) / "licence_private.pem").read_bytes(), first)

    def test_refuses_keys_inside_the_project_and_short_or_different_passwords(self):
        use_test_licensing(self, prepared=False)
        with self.assertRaises(CommandError):
            call_command("setup_licensing", keys_dir=str(Path(settings.BASE_DIR) / "keys"), stdout=StringIO())
        for answers in (["short"], ["demo-password-long-enough", "different-password-long"]):
            with tempfile.TemporaryDirectory() as keys, patch("core.management.commands.setup_licensing.getpass", side_effect=answers):
                with self.assertRaises(CommandError):
                    call_command("setup_licensing", keys_dir=keys, stdout=StringIO())
                self.assertFalse((Path(keys) / "licence_private.pem").exists())

    def test_licence_needs_a_proper_ntn_and_key(self):
        with tempfile.TemporaryDirectory() as keys:
            with self.assertRaises(CommandError):
                call_command("make_licence", keys_dir=keys, ntn="123", name="A", out="x", stdout=StringIO())
            with self.assertRaises(CommandError):
                call_command("make_licence", keys_dir=keys, ntn="1234567-1", name="A", out="x", stdout=StringIO())


class StrnFormatTests(TestCase):
    def test_saved_without_dashes_and_shown_with_them(self):
        from core.forms import CustomerForm
        from core.templatetags.humanize_money import strn

        company = make("A", "1234567")
        form = CustomerForm(
            {"name": "B", "kind": "registered", "ntn_cnic": "7654321", "strn": "00-11-2222-333-44", "province": "PUNJAB", "address": "Addr"},
            company=company,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["strn"], "0011222233344")
        self.assertEqual(strn("0011222233344"), "00-11-2222-333-44")
        self.assertEqual(strn("not13digits"), "not13digits")
        self.assertEqual(strn(""), "")


class SeedDataTests(TestCase):
    DATA = {
        "products": [{
            "name": "REAL", "hs_code": "0000.0001", "uom": "KG", "pack_unit": "SET PACK", "sale_type": "Sale type A",
            "rate_label": "1%", "rate_percent": 1, "further_tax_percent": 2, "price_per_piece": 10,
        }],
        "buyers": [{"name": "REAL BUYER", "kind": "registered", "ntn_cnic": "7654321", "strn": "00-11-2222-333-44", "province": "PUNJAB"}],
        "test_products": [{
            "name": "TEST ONE", "hs_code": "0000.0002", "uom": "KG", "sale_type": "Sale type B",
            "rate_label": "1%", "rate_percent": 1, "further_tax_percent": 2, "price_per_piece": 100,
        }],
        "test_buyers": [{"name": "TEST BUYER", "kind": "unregistered", "province": "PUNJAB"}],
        "test_invoices": [
            {"scenario": "SN001", "buyer": "REAL BUYER", "product": "TEST ONE", "quantity": "100", "price": "100"},
            {"scenario": "SN002", "buyer": "TEST BUYER", "product": "TEST ONE", "quantity": "100", "price": "100"},
            {"scenario": "SN005", "buyer": "TEST BUYER", "product": "TEST ONE", "quantity": "1", "price": "1"},
        ],
    }

    def setUp(self):
        import json
        import tempfile
        from pathlib import Path

        from django.contrib.auth import get_user_model

        self.company = make("A", "1234567")
        self.company.sandbox_scenarios = "SN001, SN002"
        self.company.save()
        user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=user, company=self.company, role="admin")
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "seed.json"
        self.path.write_text(json.dumps(self.DATA))

    def run_seed(self, **options):
        out = StringIO()
        call_command("add_seed_data", file=str(self.path), stdout=out, **options)
        return out.getvalue()

    def test_adds_everything_once_and_sends_nothing(self):
        from fbr.models import FbrApiLog

        first = self.run_seed()
        self.assertIn("Added 2 products, 2 buyers and 2 test invoices", first)
        self.assertIn("Skipped SN005", first)
        self.assertIn("Added 0 products, 0 buyers and 0 test invoices", self.run_seed())
        invoices = self.company.invoices.order_by("number")
        self.assertEqual(invoices.count(), 2)
        self.assertEqual({i.status for i in invoices}, {"saved"})
        self.assertEqual({i.scenario_id for i in invoices}, {"SN001", "SN002"})
        self.assertEqual(self.company.invoices.get(scenario_id="SN001").total_further_tax, 0)
        self.assertEqual(self.company.invoices.get(scenario_id="SN002").total_further_tax, 200)
        self.assertEqual(self.company.customers.get(name="REAL BUYER").strn, "0011222233344")
        self.assertEqual(FbrApiLog.objects.count(), 0)

    def test_keeps_a_record_that_already_exists(self):
        from core.models import Customer

        Customer.objects.create(company=self.company, name="REAL BUYER", kind="registered", ntn_cnic="1111111", province="SINDH")
        self.run_seed()
        self.assertEqual(self.company.customers.get(name="REAL BUYER").ntn_cnic, "1111111")

    def test_real_only_adds_no_test_records(self):
        self.assertIn("Added 1 products, 1 buyers and 0 test invoices", self.run_seed(real_only=True))
        self.assertFalse(self.company.products.filter(name="TEST ONE").exists())

    def test_production_mode_adds_no_test_records(self):
        self.company.fbr_mode = "production"
        self.company.save()
        output = self.run_seed()
        self.assertIn("no test records", output)
        self.assertEqual(self.company.invoices.count(), 0)

    def test_bad_data_adds_nothing(self):
        import json

        data = {**self.DATA, "buyers": [{"name": "X", "kind": "registered", "ntn_cnic": "12", "province": "PUNJAB"}]}
        self.path.write_text(json.dumps(data))
        with self.assertRaises(CommandError):
            self.run_seed()
        self.assertEqual(self.company.products.count(), 0)


class NtnFormatTests(TestCase):
    def test_invoices_show_the_seven_digit_ntn(self):
        from core.templatetags.humanize_money import ntn

        self.assertEqual(ntn("1234567-1"), "1234567")
        self.assertEqual(ntn("1234567"), "1234567")
        self.assertEqual(ntn("1234567890123"), "1234567890123")
        self.assertEqual(ntn(""), "")


class ProductRedesignTests(TestCase):
    """The product form: rate text made from the rate, units and sale types as dropdowns, FBR values shown."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.company = make("A", "1234567")
        user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=user, company=self.company, role="admin")
        self.client.force_login(user)
        from core.testing import register_copy
        register_copy(self, self.company)

    def _product(self, **extra):
        fields = dict(company=self.company, name="COTTON MIXED FABRIC", hs_code="5211.1100", uom="Meter",
                      sale_type="Processing/Conversion of Goods", rate_percent=Decimal("18"), price_per_piece=Decimal("47.60"))
        fields.update(extra)
        return Product.objects.create(**fields)

    def test_rate_text_is_made_from_the_rate(self):
        self.assertEqual(self._product().rate_label, "18%")
        self.assertEqual(self._product(name="B", rate_percent=Decimal("17.50")).rate_label, "17.5%")
        self.assertEqual(self._product(name="C", rate_percent=Decimal("0.25")).rate_label, "0.25%")
        self.assertEqual(self._product(name="D", rate_percent=Decimal("0"), sale_type="Goods at zero-rate").rate_label, "0%")

    def test_exempt_goods_go_as_exempt(self):
        self.assertEqual(self._product(sale_type="Exempt goods", rate_percent=Decimal("0")).rate_label, "Exempt")

    def test_typed_rate_text_is_replaced_unless_kept(self):
        self.assertEqual(self._product(rate_label="anything").rate_label, "18%")
        kept = self._product(name="SN017", rate_label="18% and Rs. 80 per Liter", keep_rate_text=True)
        kept.rate_percent = Decimal("118")
        kept.save()
        self.assertEqual(kept.rate_label, "18% and Rs. 80 per Liter")

    def test_seed_keeps_only_special_rate_text(self):
        from core.management.commands.add_seed_data import _add_product

        plain, _ = _add_product(self.company, {"name": "P", "hs_code": "0000.0000", "uom": "Meter", "sale_type": "S",
                                               "rate_label": "18%", "rate_percent": 18, "price_per_piece": 1,
                                               "description_for_fbr": "old", "pack_unit": "SET PACK"})
        special, _ = _add_product(self.company, {"name": "Q", "hs_code": "2710.1240", "uom": "Liter", "sale_type": "Goods (FED in ST Mode)",
                                                 "rate_label": "18% and Rs. 80 per Liter", "rate_percent": 118, "price_per_piece": 100})
        self.assertFalse(plain.keep_rate_text)
        self.assertTrue(special.keep_rate_text)
        self.assertEqual(special.rate_label, "18% and Rs. 80 per Liter")

    def test_form_fields_are_in_the_agreed_order(self):
        from core.forms import ProductForm

        self.assertEqual(list(ProductForm(company=self.company).fields), [
            "name", "hs_code", "uom", "sale_type", "rate_percent", "further_tax_percent", "fed_percent",
            "price_per_piece", "sro_schedule_no", "sro_item_serial_no", "is_active",
        ])

    def test_units_and_sale_types_are_dropdowns_from_the_starter_lists(self):
        from core.forms import ProductForm
        from fbr.constants import STARTER_SALE_TYPES, STARTER_UOMS

        form = ProductForm(company=self.company)
        self.assertEqual([c[0] for c in form.fields["uom"].widget.choices][1:], STARTER_UOMS)
        self.assertEqual([c[0] for c in form.fields["sale_type"].widget.choices][1:], STARTER_SALE_TYPES)

    def test_downloaded_fbr_list_replaces_the_starter_list(self):
        from core.forms import ProductForm
        from fbr.models import RefList

        RefList.objects.create(name="uom", data=[{"uoM_ID": 1, "description": "Pair"}, {"uoM_ID": 2, "description": "Meter"}])
        form = ProductForm(company=self.company)
        self.assertEqual([c[0] for c in form.fields["uom"].widget.choices][1:], ["Meter", "Pair"])

    def test_a_saved_unit_not_in_the_list_stays_available(self):
        from core.forms import ProductForm

        form = ProductForm(instance=self._product(uom="Dozen"), company=self.company)
        self.assertIn("Dozen", [c[0] for c in form.fields["uom"].widget.choices])

    def test_saving_the_form_makes_the_rate_text(self):
        data = {"name": "PURE COTTON FABRIC", "hs_code": "5208.1200", "uom": "Meter", "sale_type": "Processing/Conversion of Goods",
                "rate_percent": "18", "further_tax_percent": "0", "fed_percent": "0", "price_per_piece": "41.54", "is_active": "on"}
        self.client.post(reverse("product_new"), data)
        product = Product.objects.get(name="PURE COTTON FABRIC")
        self.assertEqual((product.rate_label, product.fixed_notified_value), ("18%", Decimal("0")))

    def test_form_page_shows_what_fbr_gets(self):
        page = self.client.get(reverse("product_edit", args=[self._product().pk]))
        self.assertContains(page, "Rate sent to FBR")
        self.assertContains(page, '<output id="ratePreview" >18%</output>', html=False)
        self.assertContains(page, "Fixed or notified retail price sent to FBR")
        self.assertContains(page, "Retail price per unit")
        self.assertNotContains(page, "Description for FBR")
        self.assertNotContains(page, "SET PACK")

    def test_product_list_shows_fbr_columns(self):
        self._product(further_tax_percent=Decimal("4"))
        page = self.client.get(reverse("product_list"))
        for text in ["Rate to FBR", "Further tax", "FED", "Retail price<br>per unit", "SRO", "18%", "4%", "Rs 47.60"]:
            self.assertContains(page, text)

    def test_no_captions_and_plain_text_boxes(self):
        page = self.client.get(reverse("product_edit", args=[self._product().pk])).content.decode()
        self.assertNotIn('class="form-text"', page)
        self.assertIn("Only if this sale falls under an SRO", page)
        for name in ["rate_percent", "further_tax_percent", "fed_percent", "price_per_piece"]:
            self.assertIn(f'type="text" name="{name}"', page)
            self.assertNotIn(f'type="number" name="{name}"', page)

    def test_new_product_starts_with_further_tax_4(self):
        from core.forms import ProductForm

        self.assertEqual(ProductForm(company=self.company)["further_tax_percent"].value(), "4")
        existing = self._product(further_tax_percent=Decimal("0"))
        self.assertEqual(Decimal(str(ProductForm(instance=existing, company=self.company)["further_tax_percent"].value())), Decimal("0"))

    def test_letters_in_a_number_box_are_refused(self):
        from core.forms import ProductForm

        form = ProductForm({"name": "X", "hs_code": "5211.1100", "uom": "Meter", "sale_type": "Processing/Conversion of Goods",
                            "rate_percent": "abc", "further_tax_percent": "4", "fed_percent": "0", "price_per_piece": "1"}, company=self.company)
        self.assertIn("rate_percent", form.errors)

    def test_agreed_pairs_share_a_row(self):
        import re

        page = self.client.get(reverse("product_edit", args=[self._product().pk])).content.decode()
        rows = re.findall(r'<div class="form-pair">(.*?)\n  </div>', page, flags=re.S)
        expected = [
            ("id_hs_code", "id_uom"), ("id_rate_percent", "ratePreview"), ("id_further_tax_percent", "id_fed_percent"),
            ("id_price_per_piece", "Fixed or notified retail price sent to FBR"), ("id_sro_schedule_no", "id_sro_item_serial_no"),
        ]
        self.assertEqual(len(rows), len(expected))
        for row, (left, right) in zip(rows, expected):
            self.assertIn(left, row)
            self.assertIn(right, row)


class FixedUnregisteredBuyerTests(TestCase):
    """Every company has one fixed UN-REGISTERED BUYER."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.company = make("A", "1234567")
        user = get_user_model().objects.create_user("owner", password="x")
        Membership.objects.create(user=user, company=self.company, role="admin")
        self.client.force_login(user)
        from core.testing import register_copy
        register_copy(self, self.company)

    def fixed(self):
        return Customer.objects.get(company=self.company, is_fixed=True)

    def test_new_company_gets_it(self):
        buyer = self.fixed()
        self.assertEqual((buyer.name, buyer.kind, buyer.ntn_cnic, buyer.province, buyer.address, buyer.is_active),
                         ("UN-REGISTERED BUYER", "unregistered", "", "PUNJAB", "Faisalabad", True))

    def test_only_one_even_when_asked_again(self):
        from core.models import ensure_fixed_buyer

        ensure_fixed_buyer(self.company)
        ensure_fixed_buyer(self.company)
        self.assertEqual(Customer.objects.filter(company=self.company, name="UN-REGISTERED BUYER").count(), 1)

    def test_it_comes_first_in_the_invoice_buyer_list(self):
        Customer.objects.create(company=self.company, name="AAA MILLS", kind="registered", ntn_cnic="7654321", province="PUNJAB", address="X")
        page = self.client.get(reverse("invoice_new"))
        self.assertEqual(list(page.context["customers"])[0].name, "UN-REGISTERED BUYER")

    def test_name_type_and_availability_cant_change_but_address_can(self):
        buyer = self.fixed()
        self.client.post(reverse("customer_edit", args=[buyer.pk]), {
            "name": "OTHER", "kind": "registered", "ntn_cnic": "7654321", "province": "SINDH", "address": "Karachi",
        })
        buyer.refresh_from_db()
        self.assertEqual((buyer.name, buyer.kind, buyer.ntn_cnic, buyer.is_active), ("UN-REGISTERED BUYER", "unregistered", "", True))
        self.assertEqual((buyer.province, buyer.address), ("SINDH", "Karachi"))

    def test_customer_list_tags_it_fixed(self):
        self.assertContains(self.client.get(reverse("customer_list")), '<span class="status ok">Fixed</span>')

    def test_further_tax_applies_on_its_invoices(self):
        from billing.services import LineInput, create_invoice

        product = Product.objects.create(company=self.company, name="P", hs_code="5211.1100", uom="Meter",
                                         sale_type="Processing/Conversion of Goods", rate_percent=Decimal("18"),
                                         further_tax_percent=Decimal("4"), price_per_piece=Decimal("100"))
        inv = create_invoice(company=self.company, customer=self.fixed(), invoice_date=date(2026, 11, 14),
                             lines=[LineInput(product, "metre", "10", "", "100")])
        self.assertEqual(inv.total_further_tax, Decimal("40.00"))


class PasswordChangeTests(TestCase):
    """Each user can change their own password and stays signed in."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.company = make("A", "1234567")
        self.user = get_user_model().objects.create_user("owner", password="Old-pass-2026")
        Membership.objects.create(user=self.user, company=self.company, role="admin")
        self.client.force_login(self.user)
        from core.testing import register_copy
        register_copy(self, self.company)

    def test_link_is_in_the_menu(self):
        self.assertContains(self.client.get(reverse("dashboard")), reverse("password_change"))

    def test_change_with_the_right_current_password(self):
        page = self.client.post(reverse("password_change"), {
            "old_password": "Old-pass-2026", "new_password1": "Weaving-Nov-2026", "new_password2": "Weaving-Nov-2026"}, follow=True)
        self.assertContains(page, "Your password has been changed.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Weaving-Nov-2026"))
        # Still signed in.
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_wrong_current_password_changes_nothing(self):
        self.client.post(reverse("password_change"), {
            "old_password": "wrong", "new_password1": "Weaving-Nov-2026", "new_password2": "Weaving-Nov-2026"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-pass-2026"))

    def test_new_passwords_must_match(self):
        page = self.client.post(reverse("password_change"), {
            "old_password": "Old-pass-2026", "new_password1": "Weaving-Nov-2026", "new_password2": "Weaving-Nov-2027"})
        self.assertEqual(page.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-pass-2026"))

    def test_signed_out_users_are_sent_to_log_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 302)


class LoginScreenTests(TestCase):
    def test_remember_box_and_its_script(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user("owner", password="x")
        page = self.client.get(reverse("login"))
        self.assertContains(page, 'id="remember"')
        self.assertContains(page, "Remember my user name and password on this computer")
        self.assertContains(page, "js/login.js")

    def test_closing_the_browser_signs_out(self):
        from django.conf import settings

        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
