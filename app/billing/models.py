from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from billing.constants import CURRENCIES


class UserManagerWithRelations(UserManager):
    def get_queryset(self):
        return super().get_queryset().select_related("wallet")


class User(AbstractUser):
    country = models.CharField(max_length=200)
    city = models.CharField(max_length=200)

    objects = UserManagerWithRelations()


class Wallet(models.Model):
    balance = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    user = models.OneToOneField(User, related_name="wallet", on_delete=models.CASCADE)
    currency = models.CharField(max_length=3, choices=CURRENCIES)

    def __str__(self):
        return f"{self.user.username}'s wallet, balance: {self.balance} {self.currency}"


class Transaction(models.Model):
    """
    Represents transaction where TransactionEntry is an operation on a single wallet.
    Each transaction can have up to 2 entries:
    1. for changing the balance of current user wallet
    2. for changing balance of different user's wallet. Can be None if this is a top up transaction.
    """

    created = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_top_up = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return (
            f"{self.description}. Operations: {[entry for entry in self.entries.all()]}"
        )


class ExchangeRate(models.Model):
    """
    Exchange rates taken form public european API servers.
    """

    date = models.DateField()
    from_currency = models.CharField(max_length=3, choices=CURRENCIES)
    to_currency = models.CharField(max_length=3, choices=CURRENCIES)
    rate = models.DecimalField(decimal_places=2, max_digits=20, default=0)

    def __str__(self):
        return f"{self.from_currency} to {self.to_currency}: {self.rate}, Date: {self.date}"

    class Meta:
        ordering = ("-date",)


class TransactionEntry(models.Model):
    """
    Shows money operations on the wallet.
    Negative amount for expenses.
    Positive amount for incomes.
    """

    amount = models.DecimalField(decimal_places=2, max_digits=20)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction = models.ForeignKey(
        Transaction, related_name="entries", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.amount} {self.wallet.currency}"
