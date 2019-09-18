from datetime import date

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import serializers
from billing.constants import USD
from billing.context import top_up_wallet, find_exchange_rates, create_exchange_rates
from billing.models import ExchangeRate, Wallet
from billing.serializers import (
    TransactionSerializer,
    TopUpSerializer,
    ExchangeRateSerializerRead,
    UserSerializerWrite,
    UserSerializerRead,
)


def index(request):
    return render(request, template_name="index.html")


class SignupView(CreateAPIView):
    serializer_class = UserSerializerWrite

    def post(self, request, *args, **kwargs):
        serializer_instance = self.get_serializer(data=request.data)
        serializer_instance.is_valid(raise_exception=True)
        currency = serializer_instance.validated_data.pop("currency")

        user = serializer_instance.save()

        Wallet.objects.create(user=user, currency=currency)
        # user.refresh_from_db()

        return Response(
            status=status.HTTP_201_CREATED, data=UserSerializerRead(instance=user).data
        )


class TopUpWalletView(CreateAPIView):
    serializer_class = TopUpSerializer

    def post(self, request, *args, **kwargs):
        serializer_instance = self.get_serializer(data=request.data)
        serializer_instance.is_valid(raise_exception=True)
        transaction = top_up_wallet(
            request.user.wallet, serializer_instance.validated_data["amount"]
        )
        return Response(
            status=status.HTTP_201_CREATED,
            data=TransactionSerializer(instance=transaction).data,
        )


class ExchangeRateList(ListAPIView):
    serializer_class = ExchangeRateSerializerRead

    def get_queryset(self):
        to_date = self.request.query_params.get("date", date.today())
        queryset = find_exchange_rates(
            dict(
                to_date=to_date,
                from_currency=self.request.query_params.get("from_currency", USD),
                to_currency=self.request.query_params.get("to_currency"),
            )
        )
        return queryset

    def list(self, request, *args, **kwargs):
        """
        Returns currency rates based on `from_currency` query parameter.
        For example if from_currency is EUR, it will calculate all rates based on EUR to other currencies.
        Default stored from_currency is USD.

        Also can be filtered by `date` and `to_currency`.
        Ex.:
        1. USD to CAD for 2019-09-14 requires query string: `?from_currency=USD&to_currency=CAD&date=2019-09-14`
        2. all existing to USD for today: `?from_currency=USD`
        """
        from_currency = self.request.query_params.get("from_currency", USD)
        to_date = date.fromisoformat(
            self.request.query_params.get("date", date.today().isoformat())
        )

        # Download new rates for date if needed.
        if not ExchangeRate.objects.filter(date=to_date).exists():
            create_exchange_rates(date=to_date)

        # Find base rate for currency conversion calculations.
        exchange_rate = ExchangeRate.objects.filter(
            to_currency=from_currency, date=to_date
        ).first()

        if not exchange_rate:
            raise serializers.ValidationError(
                f"No exchange rate for currency '{from_currency}' exists"
            )

        return Response(
            {
                "results": self.serializer_class(
                    self.get_queryset(),
                    many=True,
                    context=dict(
                        base_currency=from_currency, base_rate=exchange_rate.rate
                    ),
                ).data
            }
        )
