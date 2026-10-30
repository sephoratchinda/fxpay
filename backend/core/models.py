from django.conf import settings
from django.db import models

U = settings.AUTH_USER_MODEL


class Transaction(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"

    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="transactions")
    channel = models.CharField(max_length=30)
    from_ccy = models.CharField(max_length=3)
    to_ccy = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6)
    fee_total = models.DecimalField(max_digits=18, decimal_places=2)
    fx_cost = models.DecimalField(max_digits=18, decimal_places=2)
    received_amount = models.DecimalField(max_digits=18, decimal_places=2)
    expected_days = models.FloatField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    risk_level = models.CharField(max_length=6, default="Low")
    recipient_name = models.CharField(max_length=120, blank=True)
    steps = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ExposurePosition(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="exposures")
    currency = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    direction = models.CharField(max_length=10, choices=[("RECEIVABLE", "Receivable"), ("PAYABLE", "Payable")])
    due_days = models.PositiveIntegerField(default=30)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ForwardContract(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="forwards")
    base_ccy = models.CharField(max_length=3)
    quote_ccy = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    direction = models.CharField(max_length=4, choices=[("BUY", "Buy"), ("SELL", "Sell")])
    spot_rate = models.DecimalField(max_digits=18, decimal_places=6)
    forward_rate = models.DecimalField(max_digits=18, decimal_places=6)
    tenor_days = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class AIRecommendation(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="recommendations")
    request = models.JSONField()
    response = models.JSONField()
    risk_level = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
