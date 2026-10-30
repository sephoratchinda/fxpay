from django.contrib.auth.models import User
from rest_framework import serializers

from .models import ExposurePosition, ForwardContract, Transaction
from .services import market


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, data):
        return User.objects.create_user(**data)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["user", "exchange_rate", "fee_total", "fx_cost", "received_amount", "expected_days",
                            "status", "risk_level", "steps", "created_at"]


class ExposureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExposurePosition
        fields = "__all__"
        read_only_fields = ["user", "created_at"]

    def validate_currency(self, v):
        if v not in market.USD_RATES:
            raise serializers.ValidationError("Unsupported currency")
        return v

    def validate_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return v


class ForwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForwardContract
        fields = "__all__"
        read_only_fields = ["user", "created_at"]
