from django import forms
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from . import licence
from fbr.constants import STARTER_SALE_TYPES, STARTER_UOMS

from .models import Company, Customer, Product


def _use_fbr_list(form, field, name):
    """Suggest FBR's downloaded values on a field, while still allowing typing."""
    from fbr.refs import values

    options = values(name)
    if options:
        form.fields[field].widget.attrs["list"] = f"dl-{field}"
        form.datalists = {**getattr(form, "datalists", {}), f"dl-{field}": options}


class StrnMixin:
    """STRN is saved as digits only. The dashes are added only when it is shown."""

    def clean_strn(self):
        return self.cleaned_data["strn"].replace("-", "").replace(" ", "")


class StyledMixin:
    """Apply the Bootstrap classes used across the app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
            if isinstance(widget, forms.Textarea):
                widget.attrs["rows"] = 2


class CompanyForm(StrnMixin, StyledMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = ["business_name", "ntn", "cnic", "strn", "province", "address", "phone", "invoice_prefix"]

    def clean_ntn(self):
        ntn = self.cleaned_data["ntn"]
        registered = licence.installed(self.instance)
        if registered and registered["ntn"] != ntn:
            raise forms.ValidationError("This copy is registered to this NTN. A new NTN needs a new registration file.")
        return ntn

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _use_fbr_list(self, "province", "provinces")


class ProductForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "hs_code", "uom", "sale_type", "rate_percent", "further_tax_percent", "fed_percent",
            "price_per_piece", "sro_schedule_no", "sro_item_serial_no", "is_active",
        ]
        labels = {"name": "Product name", "price_per_piece": "Retail price per unit"}
        # The owner asked for no captions under the boxes on this form.
        help_texts = {f: "" for f in fields}

    NUMBER_FIELDS = ("rate_percent", "further_tax_percent", "fed_percent", "price_per_piece")

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        _use_fbr_list(self, "hs_code", "hs_codes")
        self._dropdown("uom", "uom", STARTER_UOMS)
        self._dropdown("sale_type", "transaction_types", STARTER_SALE_TYPES)
        for name in self.NUMBER_FIELDS:
            # Plain text boxes with no up and down arrows. The field still accepts numbers only.
            self.fields[name].widget = forms.TextInput(attrs={"class": "form-control", "inputmode": "decimal", "autocomplete": "off"})
        if not self.instance.pk:
            self.initial["uom"] = "Meter"
            self.initial["sale_type"] = "Processing/Conversion of Goods"
            # Further tax on sales to unregistered buyers, as on the client's January 2026 invoices.
            self.initial["further_tax_percent"] = "4"

    def _dropdown(self, field, list_name, starter):
        """FBR's downloaded list once it's there, otherwise the starter list. A saved value always stays."""
        from fbr.refs import values

        options = values(list_name) or list(starter)
        current = getattr(self.instance, field, "") or ""
        if current and current not in options:
            options = [current] + options
        self.fields[field].widget = forms.Select(
            choices=[("", "Choose")] + [(o, o) for o in options], attrs={"class": "form-select"})

    def fbr_preview(self):
        """What FBR gets for the parts that aren't typed, shown read-only on the form."""
        if self.instance.keep_rate_text:
            rate = self.instance.rate_label
        else:
            rate = Product.rate_text(self["rate_percent"].value() or 0, self["sale_type"].value() or "")
        return {"rate": rate, "fixed": self.instance.fixed_notified_value, "kept": self.instance.keep_rate_text}

    def clean_name(self):
        from billing.services import no_inch_sign

        name = no_inch_sign(self.cleaned_data["name"])
        clash = Product.objects.filter(company=self.company, name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("A product with this name already exists.")
        return name


class CustomerForm(StrnMixin, StyledMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "kind", "ntn_cnic", "strn", "province", "country", "address", "phone", "is_active"]

    LOCKED_ON_FIXED = ("name", "kind", "ntn_cnic", "strn", "country", "is_active")

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        _use_fbr_list(self, "province", "provinces")
        if self.instance.is_fixed:
            # Only the address, province and phone of the fixed buyer can be changed.
            for name in self.LOCKED_ON_FIXED:
                self.fields[name].disabled = True

    def clean_name(self):
        name = self.cleaned_data["name"]
        clash = Customer.objects.filter(company=self.company, name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("A customer with this name already exists.")
        return name

    def clean(self):
        data = super().clean()
        kind = data.get("kind")
        ntn = data.get("ntn_cnic")
        if kind == Customer.Kind.REGISTERED and not ntn and "ntn_cnic" not in self.errors:
            self.add_error("ntn_cnic", "Enter the NTN or CNIC for a registered buyer.")
        # PRAL error 0058: self-invoicing is rejected.
        if ntn and ntn in (self.company.fbr_registration, self.company.cnic):
            self.add_error("ntn_cnic", "The buyer can't have the same NTN or CNIC as your company.")
        if kind == Customer.Kind.FOREIGN:
            if not data.get("country"):
                self.add_error("country", "Enter the buyer's country.")
        elif kind:
            if not data.get("province"):
                self.add_error("province", "Enter the buyer's province.")
            if not data.get("address"):
                self.add_error("address", "Enter the buyer's address.")
        return data


class DeveloperPasswordForm(StyledMixin, forms.Form):
    developer_password = forms.CharField(widget=forms.PasswordInput, label="Developer password")

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

    def clean_developer_password(self):
        password = self.cleaned_data["developer_password"]
        if not licence.check_developer_password(password, self.company):
            raise forms.ValidationError("That password is wrong.")
        return password


class StartNumberForm(forms.Form):
    last_invoice_number = forms.IntegerField(min_value=0, max_value=99999999)


class FirstRunForm(CompanyForm):
    developer_password = forms.CharField(widget=forms.PasswordInput, label="Developer password",
                                         help_text="The developer enters this once, to set up this copy.")
    username = forms.CharField(max_length=150, label="Your username")
    password = forms.CharField(widget=forms.PasswordInput, label="Your password",
                               help_text="At least 8 characters, not only numbers.")

    class Meta(CompanyForm.Meta):
        pass

    field_order = ["developer_password"]

    def clean_developer_password(self):
        password = self.cleaned_data["developer_password"]
        if not licence.check_developer_password(password):
            raise forms.ValidationError("That password is wrong.")
        return password

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class PasswordChangeForm(StyledMixin, DjangoPasswordChangeForm):
    """Each user changes only their own password: the current one, then the new one twice."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Current password"
        self.fields["new_password1"].label = "New password"
        self.fields["new_password2"].label = "New password again"
        self.fields["new_password1"].help_text = "At least 8 characters, not too common, and not only numbers."
