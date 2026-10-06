from django.conf import settings
from django.db import models
from datetime import datetime, timedelta


class Account(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account",
        null=True, blank=True,
    )
    name = models.CharField(max_length=50, default="Demo")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} - ${self.balance}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="referrals",
    )
    referral_code = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} (ref: {self.referral_code})"


class ChartOverride(models.Model):
    """Admin ka chart manipulation."""
    DIRECTIONS = [("UP", "Show UP (fake rise)"), ("DOWN", "Show DOWN (fake fall)")]

    symbol = models.CharField(max_length=20)
    direction = models.CharField(max_length=4, choices=DIRECTIONS)
    start_time = models.TimeField(help_text="Kab se override active hoga")
    duration_minutes = models.IntegerField(default=15, help_text="Kitne minute tak")
    intensity_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.5,
        help_text="Kitna % offset lagayein (e.g., 1.5 = 1.5%)"
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.symbol} → {self.direction} ({self.intensity_percent}%)"

    @property
    def end_time(self):
        if not self.start_time:
            return None
        dt = datetime.combine(datetime.today(), self.start_time)
        return (dt + timedelta(minutes=self.duration_minutes)).time()

    @property
    def time_range_display(self):
        if not self.start_time:
            return "—"
        end = self.end_time
        if end:
            return f"{self.start_time.strftime('%H:%M')} – {end.strftime('%H:%M')}"
        return self.start_time.strftime('%H:%M')

    def is_currently_active(self):
        if not self.is_active or not self.start_time:
            return False
        now = datetime.now().time()
        end = self.end_time
        if end:
            if self.start_time <= end:
                return self.start_time <= now <= end
            return now >= self.start_time or now <= end
        return now >= self.start_time


class Signal(models.Model):
    """Admin ke private signals."""
    DIRECTIONS = [("UP", "Buy (UP)"), ("DOWN", "Sell (DOWN)")]

    symbol = models.CharField(max_length=20)
    direction = models.CharField(max_length=4, choices=DIRECTIONS)
    target_price = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    start_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=10)
    notes = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.symbol} {self.direction}"


class Trade(models.Model):
    """Spot trades — Buy/Sell."""
    SIDES = [("BUY", "Buy"), ("SELL", "Sell")]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="trades")
    symbol = models.CharField(max_length=20)
    side = models.CharField(max_length=4, choices=SIDES)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    quantity = models.DecimalField(max_digits=22, decimal_places=8)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    signal = models.ForeignKey(
        Signal, on_delete=models.SET_NULL, null=True, blank=True, related_name="trades"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.side} {self.symbol} ${self.amount}"


class ContractPosition(models.Model):
    """Contract trading — Long/Short positions."""
    DIRECTIONS = [("LONG", "Long (UP)"), ("SHORT", "Short (DOWN)")]
    STATUS = [("OPEN", "Open"), ("CLOSED", "Closed")]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="positions")
    symbol = models.CharField(max_length=20)
    direction = models.CharField(max_length=6, choices=DIRECTIONS)

    entry_price = models.DecimalField(max_digits=18, decimal_places=6)
    close_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    margin = models.DecimalField(max_digits=14, decimal_places=2)
    leverage = models.IntegerField(default=1)
    position_size = models.DecimalField(max_digits=18, decimal_places=2)

    pnl = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=6, choices=STATUS, default="OPEN")

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.direction} {self.symbol} {self.leverage}x ${self.margin}"


class Deposit(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Deposit ${self.amount}"