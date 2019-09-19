from decimal import Decimal

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from billing.constants import CURRENCIES
from billing.models import TransactionEntry, Transaction, ExchangeRate, User, Wallet
from billing.utils import calculate_currency_rate


class TransactionEntrySerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField(source="wallet.currency")

    class Meta:
        model = TransactionEntry
        fields = ("id", "amount", "currency", "wallet")


class TopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        decimal_places=2, max_digits=20, min_value=Decimal("0.01")
    )


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("id", "balance", "currency")


class TransactionSerializer(serializers.ModelSerializer):
    entries = TransactionEntrySerializer(many=True, required=True)

    class Meta:
        model = Transaction
        fields = ("id", "created", "description", "entries", "is_top_up")


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
        return calculate_currency_rate(obj.rate, self.context.get("base_rate"))


class UserSerializerRead(serializers.ModelSerializer):
    wallet = WalletSerializer()

    class Meta:
        model = User
        fields = ("id", "username", "email", "wallet", "city", "country")


class UserSerializerWrite(serializers.ModelSerializer):
    currency = serializers.ChoiceField(choices=CURRENCIES, required=True)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "city", "country", "password", "currency")

    def create(self, validated_data):
        currency = validated_data.pop("currency")
        user = super().create(validated_data)

        Wallet.objects.create(user=user, currency=currency)

        return user


class PaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        decimal_places=2, max_digits=20, min_value=Decimal("0.01")
    )
    destination_wallet = serializers.IntegerField()
    description = serializers.CharField(max_length=255)

    def validate(self, attrs):
        destination_wallet = Wallet.objects.filter(
            id=attrs["destination_wallet"]
        ).first()
        if not destination_wallet:
            raise serializers.ValidationError(
                f"Wallet with id {attrs['destination_wallet']} does not exist"
            )
        attrs["destination_wallet"] = destination_wallet
        return attrs


class ReportSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    created = serializers.DateTimeField()
    currency = serializers.CharField()
    amount = serializers.DecimalField(decimal_places=2, max_digits=20)
