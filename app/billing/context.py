import requests

from django.conf import settings
from django.db.models import Sum
from rest_framework import serializers

from billing.models import Transaction, TransactionEntry, ExchangeRate
from billing.constants import USD, SUPPORTED_CURRENCIES
from billing.serializers import ExchangeRateSerializer


def create_transaction_entry(attrs):
    entry = TransactionEntry.objects.create(**attrs)

    # Update wallet balance after each entry creation.
    wallet = entry.wallet
    wallet.balance = TransactionEntry.objects.filter(wallet=wallet).aggregate(
        Sum("amount")
    )["amount__sum"]
    wallet.save()

    return entry


def top_up_wallet(wallet, amount):
    transaction = Transaction.objects.create(description="Top up", is_top_up=True)
    create_transaction_entry(
        dict(transaction=transaction, amount=amount, wallet=wallet)
    )
    return transaction


def send_payment(source_wallet, destination_wallet, amount, description):
    transaction_data = dict(
        description=description, entries=[dict(amount=-amount, wallet=source_wallet)]
    )
    destination_entry = dict(amount=amount, wallet=destination_wallet)
    if destination_wallet.currency != source_wallet.currency:
        # TODO: convert currency
        destination_entry["amount"] = amount

    transaction_data["entries"].append(destination_entry)


def find_exchange_rates(filters=None):
    if not filters:
        filters = {}
    to_currency = filters.get("to_currency")
    from_currency = filters.get("from_currency", USD)
    to_date = filters.get("date")
    # The only from_currency in DB is USD, so no need to filter it.
    # And we exclude the self-rate e.g. USD to USD or CAD to CAD.
    queryset = ExchangeRate.objects.exclude(to_currency=from_currency)

    if to_date:
        queryset = queryset.filter(date=to_date)

    if to_currency:
        if to_currency not in SUPPORTED_CURRENCIES:
            raise serializers.ValidationError(
                f"to_currency must be one of the {SUPPORTED_CURRENCIES}"
            )
        queryset = queryset.filter(to_currency=to_currency)

    return queryset


def download_exchange_rates(date):
    response = requests.get(
        f"{settings.EXCHANGE_RATES_URL}{date}?base={USD}&symbols={','.join(SUPPORTED_CURRENCIES)}"
    )
    return response.json()


def create_exchange_rates(date):
    data = download_exchange_rates(date)
    serializer = ExchangeRateSerializer(
        many=True,
        data=[
            dict(
                rate=round(rate, 2), from_currency=USD, to_currency=currency, date=date
            )
            for currency, rate in data["rates"].items()
        ],
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
