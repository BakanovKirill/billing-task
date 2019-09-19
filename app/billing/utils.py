from decimal import Decimal


def calculate_currency_rate(target_rate, base_rate):
    """Calculates rate for current currency and a base currency.

    We can basically calculate any currency rate by dividing
    its current rate by base currency rate.
    Default currency is USD with base_rate = 1

    Examples:
    We have in DB:
        USD to USD: 1
        USD to EUR: 0.90
        USD to CAD: 1.33
        USD to CNY: 7.09
    Example 1:
        We want CAD to USD:
        "base" is CAD=1.33, USD to USD rate is 1,
        we need to divide the original USD to USD rate by new base_rate
        Result: 1 / 1.33 = 0.75
    Example 2:
        We want EUR to CAD:
        "base" is EUR=0.9, USD to CAD is 1.33,
        we need to divide the original USD to CAD rate by new base_rate.
        Result: 1.33 / 0.90 = 1.48.
    """
    return Decimal(target_rate / base_rate).quantize(Decimal("1.00"))
