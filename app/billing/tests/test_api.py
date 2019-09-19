import csv
import io

from django.core.management import call_command
from mock import patch
from datetime import datetime, date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from billing.constants import USD, EUR, CAD, SUPPORTED_CURRENCIES
from billing.context import top_up_wallet, find_transactions
from billing.models import User, Wallet, Transaction, ExchangeRate, TransactionEntry


class TestAPI(TestCase):
    fixtures = []

    def setUp(self):
        self.now = datetime.utcnow()

        self.user = User.objects.create(
            username="admin",
            email="kirill.bakanov@gmail.com",
            first_name="Kirill",
            last_name="Bakanov",
        )
        self.user2 = User.objects.create(
            username="terminator",
            email="terminator@gmail.com",
            first_name="Arny",
            last_name="Shwarts",
        )
        self.password = "asd123456"
        self.user.set_password(self.password)
        self.user2.set_password(self.password)
        self.user.save()
        self.user2.save()
        self.user_wallet = Wallet.objects.create(currency=USD, user=self.user)
        self.user2_wallet = Wallet.objects.create(currency=EUR, user=self.user2)

        self.client = APIClient()
        self.anon_client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}"
        )

    def test_auth_permissions_work(self):
        result = self.anon_client.post(
            reverse("top-up-wallet"), dict(amount=100), format="json"
        )

        self.assertEqual(result.status_code, 401)

    def test_top_up_wallet_validation(self):
        for amount in [-100, 0, 0.001]:
            result = self.client.post(
                reverse("top-up-wallet"), dict(amount=amount), format="json"
            )
            self.assertEqual(result.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_top_up_wallet(self):
        result = self.client.post(
            reverse("top-up-wallet"), dict(amount=100), format="json"
        )
        self.assertEqual(result.status_code, 201)
        transaction_data = result.data["transaction"]
        self.assertEqual(transaction_data["description"], "Top up")
        self.assertTrue(transaction_data["is_top_up"])
        self.assertEqual(len(transaction_data["entries"]), 1)
        self.assertEqual(transaction_data["entries"][0]["wallet"], self.user_wallet.id)
        self.assertEqual(transaction_data["entries"][0]["amount"], "100.00")
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(TransactionEntry.objects.count(), 1)

        self.user_wallet.refresh_from_db()
        self.assertEqual(self.user_wallet.balance, 100)

    def test_get_exchange_rates_downloads_new_rates(self):
        to_date = date.today().isoformat()
        example_response = {
            "rates": {
                "CAD": 1.3259568293,
                "EUR": 0.9069472157,
                "CNY": 7.0967712679,
                "USD": 1.0,
            },
            "base": "USD",
            "date": to_date,
        }
        with patch(
            "billing.context.download_exchange_rates", return_value=example_response
        ):
            result = self.client.get(
                f"{reverse('exchange-rates')}?from_currency=USD&date={to_date}"
            )
            self.assertEqual(len(result.data["results"]), 3)  # excluding USD
            for result in result.data["results"]:
                self.assertEqual(result["from_currency"], USD)
                self.assertIn(result["to_currency"], SUPPORTED_CURRENCIES)
                self.assertIsNotNone(result["rate"])
                self.assertIsNotNone(result["date"])

    def test_get_existing_exchange_rates(self):
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=EUR, rate=0.90, date=date.today()
        )
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=USD, rate=1, date=date.today()
        )
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=CAD, rate=1.33, date=date.today()
        )
        result = self.client.get(f"{reverse('exchange-rates')}?from_currency=EUR")
        self.assertEqual(len(result.data["results"]), 2)  # self rate excluded

        self.assertEqual(result.data["results"][0]["from_currency"], EUR)
        self.assertEqual(result.data["results"][0]["to_currency"], USD)
        self.assertEqual(result.data["results"][1]["from_currency"], EUR)
        self.assertEqual(result.data["results"][1]["to_currency"], CAD)
        # Rates calculated according to from_currency in request
        self.assertEqual(result.data["results"][0]["rate"], Decimal("1.11"))
        self.assertEqual(result.data["results"][1]["rate"], Decimal("1.48"))
        result = self.client.get(
            f"{reverse('exchange-rates')}?from_currency=EUR&date={date.today()}"
        )
        self.assertEqual(len(result.data["results"]), 2)  # self rate excluded

    def test_signup(self):
        result = self.anon_client.post(
            reverse("signup"),
            dict(
                username="hellothere",
                password="GeneralKenobi!",
                email="order66@gmail.com",
                city="Jedi Temple",
                country="Coruscant",
                currency=CAD,
            ),
            format="json",
        )
        self.assertEqual(result.status_code, 201)
        result = result.json()
        self.assertIsNotNone(result["id"])
        self.assertIsNotNone(result["wallet"])
        self.assertEqual(result["email"], "order66@gmail.com")
        self.assertEqual(result["username"], "hellothere")
        self.assertTrue(User.objects.filter(username="hellothere").count(), 1)
        self.assertEqual(
            sorted(result["wallet"].keys()), sorted(["id", "balance", "currency"])
        )
        self.assertEqual(result["wallet"]["currency"], CAD)

    def test_send_money(self):
        today = date.today()
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=USD, rate=1, date=today
        )
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=EUR, rate=0.90, date=today
        )
        self.assertEqual(self.user_wallet.balance, 0)
        post_data = dict(
            amount=100,
            description="It's a trap!",
            destination_wallet=self.user2_wallet.id,
        )
        result = self.client.post(reverse("transactions"), post_data, format="json")
        # didn't validate because not enough funds
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json(), ["More gold is needed."])
        # Add 500 $ to user wallet
        top_up_wallet(self.user_wallet, 500)
        result = self.client.post(reverse("transactions"), post_data, format="json")

        self.assertEqual(result.status_code, 201)
        self.user_wallet.refresh_from_db()
        self.user2_wallet.refresh_from_db()
        self.assertEqual(self.user_wallet.balance, Decimal("400"))
        self.assertEqual(self.user2_wallet.balance, Decimal("90"))
        self.assertEqual(Transaction.objects.count(), 2)  # 1 top up, 1 payment
        self.assertEqual(
            TransactionEntry.objects.count(), 3
        )  # 1 top up, 2 for payment

    def test_report(self):
        # Setup data before report testing
        today = date.today()
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=USD, rate=1, date=today
        )
        ExchangeRate.objects.create(
            from_currency=USD, to_currency=EUR, rate=0.90, date=today
        )
        call_command("add_transactions")
        transactions = Transaction.objects.count()
        self.assertEqual(transactions, 102)
        # Check report query of another user doesn't work if you are not staff
        result = self.client.get(
            f"{reverse('generate-report')}?username={self.user2.username}"
        )
        self.assertEqual(result.status_code, 403)
        # Check report works for self
        result = self.client.get(
            f"{reverse('generate-report')}?username={self.user.username}"
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data), 101)  # 102 - 1 for top up from another user
        self.assertEqual(
            sorted(result.data[0].keys()),
            sorted(["id", "username", "created", "currency", "amount"]),
        )
        # Check report works with date_from filter
        result = self.client.get(
            f"{reverse('generate-report')}?username={self.user.username}&date_from={result.data[50]['created']}"
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data), 51)
        # Check report works with date_from and date_to
        result = self.client.get(
            f"{reverse('generate-report')}?"
            f"username={self.user.username}&date_from={result.data[10]['created']}&date_to={result.data[5]['created']}"
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data), 6)

        # Check CSV
        result = self.client.get(
            f"{reverse('generate-report')}?username={self.user.username}&format=csv"
        )

        content = result.content.decode("utf-8")
        cvs_reader = csv.reader(io.StringIO(content))
        body = list(cvs_reader)
        headers = body.pop(0)
        self.assertEqual(headers, ["amount", "created", "currency", "id", "username"])
        self.assertEqual(len(body), 101)
