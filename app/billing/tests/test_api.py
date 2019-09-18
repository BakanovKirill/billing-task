from mock import patch
from datetime import datetime, date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from billing.constants import USD, EUR, CAD
from billing.models import User, Wallet, Transaction, ExchangeRate


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
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}"
        )

    def test_auth_permissions_work(self):
        client = APIClient()
        result = client.post(reverse("top-up-wallet"), dict(amount=100), format="json")

        self.assertEquals(result.status_code, 401)

    def test_top_up_wallet_validation(self):
        for amount in [-100, 0, 0.001]:
            result = self.client.post(
                reverse("top-up-wallet"), dict(amount=amount), format="json"
            )
            self.assertEquals(result.status_code, 400)
        self.assertEquals(Transaction.objects.count(), 0)

    def test_top_up_wallet(self):
        result = self.client.post(
            reverse("top-up-wallet"), dict(amount=100), format="json"
        )
        self.assertEquals(result.status_code, 201)
        self.assertEquals(result.data["description"], "Top up")
        self.assertTrue(result.data["is_top_up"])
        self.assertEquals(len(result.data["entries"]), 1)
        self.assertEquals(result.data["entries"][0]["wallet"], self.user_wallet.id)
        self.assertEquals(result.data["entries"][0]["amount"], "100.00")
        self.assertEquals(Transaction.objects.count(), 1)

        self.user_wallet.refresh_from_db()
        self.assertEquals(self.user_wallet.balance, 100)

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
            self.assertEquals(len(result.data["results"]), 3)  # excluding USD

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
        self.assertEquals(len(result.data["results"]), 2)  # self rate excluded

        self.assertEquals(result.data["results"][0]["from_currency"], EUR)
        self.assertEquals(result.data["results"][0]["to_currency"], USD)
        self.assertEquals(result.data["results"][1]["from_currency"], EUR)
        self.assertEquals(result.data["results"][1]["to_currency"], CAD)
        # Rates calculated according to from_currency in request
        self.assertEquals(result.data["results"][0]["rate"], Decimal("1.11"))
        self.assertEquals(result.data["results"][1]["rate"], Decimal("1.48"))
        result = self.client.get(f"{reverse('exchange-rates')}?from_currency=EUR&date={date.today()}")
        self.assertEquals(len(result.data["results"]), 2)  # self rate excluded
    # def test_register(self):
    #     result = self.client.post(
    #         reverse("register"),
    #         dict(
    #             username="hellothere",
    #             password="asd12345",
    #             city="Kiev",
    #             country="Ukraine",
    #             currency=USD,
    #         ),
    #         format="json",
    #     )
    #     self.assertEquals(result.status_code, 201)
    #     result = result.json()
