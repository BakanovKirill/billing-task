from django.core.management.base import BaseCommand

from billing.context import top_up_wallet, send_payment
from billing.models import User


class Command(BaseCommand):
    help = "Add transactions command to quickly create lots of transactions for testing purposes"

    def handle(self, *args, **options):
        user1, user2 = User.objects.all()[:2]
        top_up_wallet(user1.wallet, 1000)
        top_up_wallet(user2.wallet, 2000)
        for x in range(100):
            source_wallet = user1.wallet
            destination_wallet = user2.wallet
            if x % 2:
                source_wallet, destination_wallet = destination_wallet, source_wallet
            send_payment(
                source_wallet=source_wallet,
                destination_wallet=destination_wallet,
                amount=x,
                description=f"Payment #{x}",
            )
