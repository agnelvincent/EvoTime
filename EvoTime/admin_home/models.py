from django.db import models
from django.utils.timezone import now
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal


def validate_discount_percentage(value):
    """Ensure the discount percentage is between 1 and 100."""
    if value <= 0 or value > 100:
        raise ValidationError("Discount percentage must be between 1 and 100.")


def validate_min_cart_value(value):
    """Ensure the minimum cart value is non-negative."""
    if value < 0:
        raise ValidationError("Minimum cart value cannot be negative.")


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[validate_discount_percentage],
        help_text="Percentage off the cart subtotal."
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional cap on the discount. E.g. 50% coupon capped at ₹200 max."
    )
    min_cart_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[validate_min_cart_value],
        help_text="Minimum cart subtotal required to use this coupon."
    )
    start_date = models.DateField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # ── Validity helpers ───────────────────────────────────────────────────────

    def is_expired(self):
        """True if expiry_date is set and has already passed."""
        return bool(self.expiry_date and self.expiry_date <= timezone.now())

    def has_started(self):
        """True if start_date has been reached (or is today)."""
        return self.start_date <= timezone.now().date()

    def is_valid(self):
        """
        A coupon is considered valid when ALL of the following are true:
          - is_active is True
          - start_date has been reached
          - expiry_date has not yet passed (or is not set)
        """
        return self.is_active and self.has_started() and not self.is_expired()

    # ── Discount calculation ───────────────────────────────────────────────────

    def calculate_discount(self, cart_total):
        """
        Return the discount amount for the given cart_total (Decimal or float).
        Applies max_discount_amount as a ceiling if set.
        Returns Decimal('0') if cart_total < min_cart_value.
        """
        if isinstance(cart_total, float):
            cart_total = Decimal(str(cart_total))
        else:
            cart_total = Decimal(cart_total)

        if cart_total < self.min_cart_value:
            return Decimal('0')

        raw_discount = (self.discount_percentage / Decimal('100')) * cart_total

        # Apply cap if set
        if self.max_discount_amount is not None:
            raw_discount = min(raw_discount, Decimal(self.max_discount_amount))

        return raw_discount.quantize(Decimal('0.01'))

    # ── Model validation ───────────────────────────────────────────────────────

    def clean(self):
        """Validate that expiry_date is in the future and start_date <= expiry_date."""
        if self.expiry_date and self.expiry_date < timezone.now():
            raise ValidationError("Expiry date cannot be in the past.")
        if self.expiry_date and self.start_date:
            from datetime import datetime, timezone as dt_tz
            start_dt = datetime.combine(self.start_date, datetime.min.time()).replace(tzinfo=dt_tz.utc)
            if start_dt > self.expiry_date:
                raise ValidationError("Start date cannot be after expiry date.")

    def __str__(self):
        cap = f" (max ₹{self.max_discount_amount})" if self.max_discount_amount else ""
        return f"{self.code} — {self.discount_percentage}%{cap}"


class UsedCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon')  # One use per user

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code} on {self.used_on:%Y-%m-%d}"