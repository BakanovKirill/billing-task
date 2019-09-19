from datetime import date

from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework import status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer
from rest_framework_xml.renderers import XMLRenderer

from billing.constants import USD
from billing.context import (
    top_up_wallet,
    find_exchange_rates,
    send_payment,
    find_transactions,
    update_exchange_rates_for_date_if_not_exist,
)
from billing.models import TransactionEntry
from billing.serializers import (
    TransactionSerializer,
    TopUpSerializer,
    ExchangeRateSerializerRead,
    UserSerializerWrite,
    UserSerializerRead,
    PaymentSerializer,
    ReportSerializer,
)


def index(request):
    return redirect(reverse("schema-swagger-ui"))


class SignupView(CreateAPIView):
    serializer_class = UserSerializerWrite
    permission_classes = (AllowAny,)
    authentication_classes = [BasicAuthentication]

    def post(self, request, *args, **kwargs):
        serializer_instance = self.get_serializer(data=request.data)
        serializer_instance.is_valid(raise_exception=True)
        user = serializer_instance.save()

        return Response(
            status=status.HTTP_201_CREATED, data=UserSerializerRead(instance=user).data
        )


class TopUpWalletView(CreateAPIView):
    serializer_class = TopUpSerializer

    def post(self, request, *args, **kwargs):
        serializer_instance = self.get_serializer(data=request.data)
        serializer_instance.is_valid(raise_exception=True)
        transaction_instance = top_up_wallet(
            request.user.wallet, serializer_instance.validated_data["amount"]
        )
        return Response(
            status=status.HTTP_201_CREATED,
            data=dict(
                balance=request.user.wallet.balance,
                transaction=TransactionSerializer(instance=transaction_instance).data,
            ),
        )


class TransactionViewset(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentSerializer
        return TransactionSerializer

    def get_queryset(self):
        return find_transactions(dict(wallet=self.request.user.wallet))

    def post(self, request, *args, **kwargs):
        payment_serializer = PaymentSerializer(data=request.data)
        payment_serializer.is_valid(raise_exception=True)
        user_wallet = request.user.wallet
        if user_wallet.balance < payment_serializer.validated_data["amount"]:
            raise serializers.ValidationError("More gold is needed.")
        transaction_instance = send_payment(
            source_wallet=user_wallet, **payment_serializer.validated_data
        )
        return Response(
            status=status.HTTP_201_CREATED,
            data=dict(
                balance=user_wallet.balance,
                transaction=TransactionSerializer(instance=transaction_instance).data,
            ),
        )


class ExchangeRateList(ListAPIView):
    serializer_class = ExchangeRateSerializerRead

    def get_queryset(self):
        for_date = self.request.query_params.get("date", date.today())
        queryset = find_exchange_rates(
            dict(
                for_date=for_date,
                from_currency=self.request.query_params.get("from_currency", USD),
                to_currency=self.request.query_params.get("to_currency"),
            )
        )
        return queryset

    def list(self, request, *args, **kwargs):
        """Returns currency rates based on `from_currency` query parameter.

        For example if from_currency is EUR, it will calculate all rates based on EUR to other currencies.
        Default stored from_currency is USD.

        Also can be filtered by `date` and `to_currency`.
        Ex.:
        1. USD to CAD for 2019-09-14 requires query string: `?from_currency=USD&to_currency=CAD&date=2019-09-14`
        2. all existing to USD for today: `?from_currency=USD`
        """
        from_currency = self.request.query_params.get("from_currency", USD)
        for_date = date.fromisoformat(
            self.request.query_params.get("date", date.today().isoformat())
        )

        # Download new rates for date if needed.
        update_exchange_rates_for_date_if_not_exist(for_date)

        # Find base rate for currency conversion calculations.
        exchange_rate = find_exchange_rates(
            dict(to_currency=from_currency, for_date=for_date)
        ).first()

        if not exchange_rate:
            raise serializers.ValidationError(
                f"No exchange rate for currency '{from_currency}' exists"
            )

        return Response(
            {
                "results": self.serializer_class(
                    self.get_queryset().exclude(
                        to_currency=from_currency
                    ),  # remove self rate from results, e.g. USD to USD
                    many=True,
                    context=dict(
                        base_currency=from_currency, base_rate=exchange_rate.rate
                    ),
                ).data
            }
        )


class ReportView(APIView):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [
        CSVRenderer,
        XMLRenderer,
    ]

    def get(self, request):
        output_format = request.query_params.get("format")
        username = request.query_params.get("username")

        if not username:
            raise serializers.ValidationError("username query param is required")
        if not request.user.is_staff and username != request.user.username:
            raise PermissionDenied(
                "You need staff permissions to see another user report."
            )

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        entries = TransactionEntry.objects.filter(
            wallet__user__username=username
        ).select_related("wallet__user", "transaction")

        if date_from:
            entries = entries.filter(transaction__created__gte=date_from)

        if date_to:
            entries = entries.filter(transaction__created__lte=date_to)

        entries = entries.values(
            "id",
            "amount",
            username=F("wallet__user__username"),
            created=F("transaction__created"),
            currency=F("wallet__currency"),
        )

        resp = Response(ReportSerializer(entries, many=True).data)

        if output_format:
            resp[
                "Content-Disposition"
            ] = f"attachment; filename='{username}_report.{output_format}'"

        return resp
