"""Companies, their users, products and customers.

Every business record belongs to one company. Views must always read through
``request.company`` so one client's data can never appear for another.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

# The NTN as FBR prints it, such as 0000000-0. PRAL takes its 7 digits without the check digit.
ntn_validator = RegexValidator(r"^\d{7}-\d$", "Enter the NTN as 0000000-0.")
cnic_validator = RegexValidator(r"^\d{13}$", "Enter 13 digits, with no dashes.")
# PRAL error 0002: buyer is a 13 digit CNIC or a 7 or 9 digit NTN.
buyer_reg_validator = RegexValidator(r"^(\d{7}|\d{9}|\d{13})$", "Enter 7, 9 or 13 digits, with no dashes.")
hs_code_validator = RegexValidator(r"^\d{4}\.\d{4}$", "Use the format 0000.0000.")
# PRAL errors 0088 and 0173: letters and digits, hyphens only between them.
prefix_validator = RegexValidator(r"^[A-Za-z0-9]+$", "Use letters and digits only.")


class Company(models.Model):
    business_name = models.CharField(
        max_length=200, unique=True,
        help_text="Exactly as registered with FBR. This is the name sent to FBR.",
    )
    ntn = models.CharField(
        "NTN", max_length=9, validators=[ntn_validator],
        help_text="Required. Use the format 0000000-0. This is what prints on invoices.",
    )
    cnic = models.CharField(
        "CNIC", max_length=13, blank=True, validators=[cnic_validator],
        help_text="Optional. 13 digits, with no dashes. It doesn't print on invoices.",
    )
    strn = models.CharField("STRN", max_length=20, blank=True)
    province = models.CharField(max_length=60)
    address = models.TextField()
    phone = models.CharField(max_length=60, blank=True)
    invoice_prefix = models.CharField(
        max_length=10, default="", blank=True, validators=[prefix_validator],
        help_text="Leave blank for plain numbers like 119. With AG, numbers look like AG-000001.",
    )
    last_invoice_number = models.PositiveIntegerField(
        default=0, blank=True,
        help_text="The last number you issued before this app. New invoices continue after it.",
    )
    demo_started_on = models.DateField(null=True, blank=True, editable=False)
    demo_last_seen = models.DateField(null=True, blank=True, editable=False)
    sandbox_scenarios = models.CharField(max_length=200, blank=True)
    fbr_mode = models.CharField(max_length=10, default="sandbox", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["business_name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        created = self._state.adding
        super().save(*args, **kwargs)
        if created:
            ensure_fixed_buyer(self)

    @property
    def fbr_registration(self):
        """The 7 digit NTN sent to FBR as sellerNTNCNIC."""
        return self.ntn[:7]


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        OPERATOR = "operator", "Operator"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.OPERATOR)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "company"], name="one_membership_per_company")]
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user} at {self.company} ({self.role})"




class Product(models.Model):
    """Tax details live here so they aren't typed on every invoice."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    hs_code = models.CharField("HS code", max_length=9, validators=[hs_code_validator])
    uom = models.CharField("Unit reported to FBR", max_length=100, help_text="Must be a unit FBR allows for this HS code.")
    sale_type = models.CharField(max_length=150, help_text="The FBR sale type for this product.")
    # The rate text FBR gets. It's made from the rate when the product is saved, except when
    # keep_rate_text is set, as for a sandbox test that needs FBR's special wording.
    rate_label = models.CharField("Rate sent to FBR", max_length=100, blank=True)
    keep_rate_text = models.BooleanField(default=False, editable=False)
    rate_percent = models.DecimalField(
        "Sales tax rate (%)", max_digits=6, decimal_places=2, validators=[MinValueValidator(0)],
    )
    further_tax_percent = models.DecimalField(
        "Further tax rate (%)", max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)],
        help_text="Applied to unregistered buyers only.",
    )
    fed_percent = models.DecimalField(
        "FED rate (%)", max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)],
        help_text="Leave at 0 unless FED applies to this product.",
    )
    # FBR's Fixed / notified value or Retail Price, for Third Schedule goods. Not on the form; always 0 here.
    fixed_notified_value = models.DecimalField(
        "Fixed or notified retail price sent to FBR", max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)],
    )
    sro_schedule_no = models.CharField("SRO schedule no.", max_length=50, blank=True, help_text="Only if this sale falls under an SRO.")
    sro_item_serial_no = models.CharField("SRO item serial no.", max_length=50, blank=True, help_text="Only if this sale falls under an SRO.")
    price_per_piece = models.DecimalField("Retail price per unit", max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField("Available on new invoices", default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_product_name_per_company")]

    def __str__(self):
        return self.name

    @staticmethod
    def rate_text(rate, sale_type):
        """FBR writes Exempt for exempt goods, and the rate with a % sign otherwise, for example 18%."""
        if str(sale_type).strip().lower().startswith("exempt"):
            return "Exempt"
        number = format(Decimal(rate).normalize(), "f")
        return f"{number}%"

    def save(self, *args, **kwargs):
        if not self.keep_rate_text:
            self.rate_label = self.rate_text(self.rate_percent, self.sale_type)
        super().save(*args, **kwargs)

    @property
    def is_kg(self):
        """FBR's unit list spells this unit both ways."""
        return self.uom.strip().lower() in {"kg", "kilogram"}

    @property
    def is_metre(self):
        """Cloth by length. The client's Annex-C reports it to FBR as Meter."""
        return self.uom.strip().lower() in {"meter", "metre"}


class Customer(models.Model):
    class Kind(models.TextChoices):
        REGISTERED = "registered", "Registered"
        UNREGISTERED = "unregistered", "Unregistered"
        FOREIGN = "foreign", "Foreign (export)"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField("Business or person name", max_length=200)
    kind = models.CharField("Buyer type", max_length=15, choices=Kind.choices, default=Kind.REGISTERED)
    ntn_cnic = models.CharField(
        "NTN or CNIC", max_length=13, blank=True, validators=[buyer_reg_validator],
        help_text="Required for registered buyers. 7, 9 or 13 digits, with no dashes.",
    )
    strn = models.CharField("STRN", max_length=30, blank=True, help_text="Sales tax registration number. It prints on the invoice and doesn't go to FBR.")
    province = models.CharField(max_length=60, blank=True, help_text="Required unless the buyer is foreign.")
    country = models.CharField(max_length=60, blank=True, help_text="For foreign buyers.")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField("Available on new invoices", default=True)
    # The fixed UN-REGISTERED BUYER every company has. Its name and type can't change, and it stays available.
    is_fixed = models.BooleanField(default=False, editable=False)
    # FBR's latest answers about this buyer, kept for offline use.
    fbr_reg_type = models.CharField(max_length=30, blank=True, editable=False)
    fbr_status = models.CharField(max_length=30, blank=True, editable=False)
    fbr_checked_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-is_fixed", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_customer_name_per_company")]

    def __str__(self):
        return self.name

    @property
    def fbr_mismatch(self):
        """True when FBR's answer disagrees with the buyer type saved here."""
        answer = self.fbr_reg_type.strip().lower()
        if answer == "registered":
            return self.kind != self.Kind.REGISTERED
        if answer == "unregistered":
            return self.kind == self.Kind.REGISTERED
        return False


FIXED_BUYER_NAME = "UN-REGISTERED BUYER"
FIXED_BUYER_ADDRESS = "Faisalabad"


def ensure_fixed_buyer(company):
    """Every company has one fixed unregistered buyer, first in the buyer list."""
    buyer, created = Customer.objects.get_or_create(
        company=company, name=FIXED_BUYER_NAME,
        defaults={"kind": Customer.Kind.UNREGISTERED, "province": company.province, "address": FIXED_BUYER_ADDRESS},
    )
    changed = {"is_fixed": True, "kind": Customer.Kind.UNREGISTERED, "ntn_cnic": "", "is_active": True}
    if any(getattr(buyer, k) != v for k, v in changed.items()):
        for k, v in changed.items():
            setattr(buyer, k, v)
        buyer.save()
    return buyer
