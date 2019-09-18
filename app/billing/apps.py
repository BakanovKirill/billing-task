from datetime import date, timedelta

from django.apps import AppConfig


class BillingAppConfig(AppConfig):
    name = "billing"
    verbose_name = "Billing"

    def ready(self):
        pass
