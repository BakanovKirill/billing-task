from enum import Enum


class Currency(Enum):
    EUR = "EUR"
    USD = "USD"
    CAD = "CAD"
    CNY = "CNY"


BASE_CURRENCY = Currency.USD

CURRENCIES = [(cur, cur.value) for cur in Currency]
