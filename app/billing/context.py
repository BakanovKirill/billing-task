from datetime import date
from decimal import Decimal

import requests

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from billing.models import Transaction, TransactionEntry, ExchangeRate
from billing.constants import USD, SUPPORTED_CURRENCIES
from billing.serializers import ExchangeRateSerializer, TransactionSerializer
from billing.utils import calculate_currency_rate


def create_transaction_entry(attrs):
    """Create TransactionEntry

    :param attrs: dict() with keys: transaction, amount, wallet
    :return: TransactionEntry
    """
    entry = TransactionEntry.objects.create(**attrs)

    # Update wallet balance after each entry creation.
    wallet = entry.wallet
    wallet.balance = TransactionEntry.objects.filter(wallet=wallet).aggregate(
        Sum("amount")
    )["amount__sum"]
    wallet.save()

    return entry


def create_transaction(transaction_attrs, entries):
    """Create Transaction

    :param transaction_attrs: dict() with keys: description
    :param entries: list of dict() with keys: amount, wallet
    :return: Transaction
    """

    # atomic to rollback if anything throws an exception
    with transaction.atomic():
        transaction_instance = Transaction.objects.create(**transaction_attrs)
        for entry_data in entries:
            create_transaction_entry(
                dict(transaction=transaction_instance, **entry_data)
            )

    return transaction_instance


def top_up_wallet(wallet, amount):
    """Add money to wallet balance

    Creates a Transaction with single TransactionEntry

    :param wallet: Wallet instance
    :param amount: Decimal
    :return: Transaction
    """
    return create_transaction(
        transaction_attrs=dict(description="Top up", is_top_up=True),
        entries=[dict(amount=abs(amount), wallet=wallet)],
    )


def send_payment(source_wallet, destination_wallet, amount, description):
    """Sends amount of money from source_wallet to destination_wallet

    :param source_wallet: Wallet
    :param destination_wallet: Wallet
    :param amount: Decimal
    :param description: str
    :return: Transaction
    """
    # in case the sign is wrong get absolute value
    amount = abs(amount)

    source_entry = dict(amount=-amount, wallet=source_wallet)
    destination_entry = dict(amount=amount, wallet=destination_wallet)

    if destination_wallet.currency != source_wallet.currency:
        from_rate = (
            find_exchange_rates(dict(to_currency=source_wallet.currency)).first().rate
        )
        to_rate = (
            find_exchange_rates(dict(to_currency=destination_wallet.currency))
            .first()
            .rate
        )
        destination_entry["amount"] = (
            amount * calculate_currency_rate(base_rate=from_rate, target_rate=to_rate)
        ).quantize(Decimal("1.00"))

    transaction_instance = create_transaction(
        dict(description=description), entries=[source_entry, destination_entry]
    )
    return transaction_instance


def find_transactions(filters):
    queryset = Transaction.objects.prefetch_related("entries__wallet").filter(
        entries__wallet=filters["wallet"]
    )
    return queryset


def find_exchange_rates(filters=None):
    if not filters:
        filters = {}

    for_date = filters.get("for_date", date.today())

    queryset = ExchangeRate.objects.filter(date=for_date)

    to_currency = filters.get("to_currency")

    if to_currency:
        if to_currency not in SUPPORTED_CURRENCIES:
            raise serializers.ValidationError(
                f"to_currency must be one of the {SUPPORTED_CURRENCIES}"
            )
        queryset = queryset.filter(to_currency=to_currency)

    return queryset


def download_exchange_rates(for_date):
    response = requests.get(
        f"{settings.EXCHANGE_RATES_URL}{for_date}?base={USD}&symbols={','.join(SUPPORTED_CURRENCIES)}"
    )
    return response.json()


def create_exchange_rates(for_date):
    data = download_exchange_rates(for_date)
    serializer = ExchangeRateSerializer(
        many=True,
        data=[
            dict(
                rate=round(rate, 2),
                from_currency=USD,
                to_currency=currency,
                date=for_date,
            )
            for currency, rate in data["rates"].items()
        ],
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()


def update_exchange_rates_for_date_if_not_exist(for_date=None):
    if not for_date:
        for_date = date.today()
    # Download exchange rates for the current day on app startup
    if not find_exchange_rates(dict(for_date=for_date)).exists():
        create_exchange_rates(for_date)
