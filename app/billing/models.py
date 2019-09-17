from django.contrib.auth.models import AbstractUser
from django.db import models

from billing.constants import CURRENCIES


class CurrencyMixin:
    currency = models.CharField(
        max_length=3, choices=CURRENCIES
    )


class User(AbstractUser):
    country = models.CharField(max_length=200)
    city = models.CharField(max_length=200)


class Wallet(models.Model, CurrencyMixin):
    balance = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    user = models.OneToOneField(User, related_name="wallet", on_delete=models.CASCADE)


class Transaction(models.Model):
    """
    Represents transaction between two wallets
    """

    created = models.DateTimeField(auto_now_add=True)


class ExchangeRate(models.Model):
    date = models.DateField()
    from_currency = models.CharField(
        max_length=3, choices=CURRENCIES
    )
    to_currency = models.CharField(
        max_length=3, choices=CURRENCIES
    )
    rate = models.DecimalField(decimal_places=2, max_digits=20, default=0)


class TransactionEntry(models.Model, CurrencyMixin):
    amount = models.DecimalField(decimal_places=2, max_digits=20)

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    # nullable transaction happens when user tops up his wallet by himself.
    transaction = models.ForeignKey(
        Transaction,
        related_name="entries",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
