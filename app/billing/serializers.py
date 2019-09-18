from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from billing.constants import CURRENCIES
from billing.models import TransactionEntry, Transaction, ExchangeRate, User


class TransactionEntrySerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField(source="wallet.currency")

    class Meta:
        model = TransactionEntry
        fields = ("id", "amount", "currency", "wallet")


class TopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        decimal_places=2, max_digits=20, min_value=Decimal("0.01")
    )


class TransactionSerializer(serializers.ModelSerializer):
    entries = TransactionEntrySerializer(many=True, required=True)

    class Meta:
        model = Transaction
        fields = ("id", "created", "description", "entries", "is_top_up")

    def validate(self, attrs):
        entries = attrs["entries"]
        entries_count = len(entries)

        if attrs["is_top_up"]:
            if entries_count > 1:
                raise serializers.ValidationError(
                    "Only single entry allowed for topping up the wallet"
                )
            # Ensure wallet belongs to current user when topping up
            attrs["entries"][0]["wallet"] = self.context["wallet"]

        if entries_count > 2:
            raise serializers.ValidationError(
                "No more than 2 entries allowed per transaction."
            )
        if entries_count == 2 and entries[0]["wallet"] == entries[1]["wallet"]:
            raise serializers.ValidationError(
                "Transaction must be done between different wallets"
            )
        return attrs

    def create(self, validated_data):
        entries = validated_data.pop("entries")

        # atomic to rollback if anything throws an exception
        with transaction.atomic():
            transaction_instance = Transaction.objects.create(**validated_data)
            for entry_data in entries:
                TransactionEntry.objects.create(
                    transaction=transaction_instance, **entry_data
                )

        return transaction_instance


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ("id", "from_currency", "to_currency", "rate", "date")


class ExchangeRateSerializerRead(ExchangeRateSerializer):
    from_currency = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()

    def get_from_currency(self, obj):  # pylint: disable=unused-argument
        return self.context.get("base_currency")

    def get_rate(self, obj):
        """Calculates rate for current currency and a base currency.

        We can basically calculate any currency rate by diving
        its current rate by base currency rate.

        For example:
        We have in DB:
            USD to EUR: 0.90
            USD to CAD: 1.30
        We want EUR to CAD rate (which must be ~ 1.44).
        Default "base" is USD with base_rate = 1
        Here "base" is EUR, e.g. 0.9, we need to divide the original rate by base_rate.
        Result: 1.30 / 0.90 = 1.44.
        """
        return round(obj.rate / self.context.get("base_rate"), 2)


class UserSerializerRead(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "wallet")


class UserSerializerWrite(serializers.ModelSerializer):
    currency = serializers.ChoiceField(choices=CURRENCIES, required=True)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "city", "country", "password", "currency")

