from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as UserAdminBase

from billing.models import User, Wallet, TransactionEntry, Transaction, ExchangeRate


class UserAdmin(UserAdminBase):
    pass


class TransactionEntryAdmin(admin.ModelAdmin):
    pass


class TransactionEntryInline(admin.TabularInline):
    model = TransactionEntry
    extra = 0


class TransactionAdmin(admin.ModelAdmin):
    readonly_fields = ["created"]
    inlines = [TransactionEntryInline]


admin.site.register(User, UserAdmin)
admin.site.register(Wallet)
admin.site.register(TransactionEntry, TransactionEntryAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(ExchangeRate)
