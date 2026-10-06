from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Account, Trade, Deposit, Profile, Signal, ChartOverride, ContractPosition
)


class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False
    verbose_name_plural = "Account"


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    verbose_name_plural = "Profile"
    readonly_fields = ("referral_code", "created_at")


class UserAdmin(BaseUserAdmin):
    inlines = [AccountInline, ProfileInline]
    list_display = ("username", "email", "referred_by_user", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined", "profile__referred_by")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    actions = ["approve_users", "reject_users"]

    def referred_by_user(self, obj):
        try:
            if obj.profile.referred_by:
                return obj.profile.referred_by.username
        except Profile.DoesNotExist:
            pass
        return "—"
    referred_by_user.short_description = "Referred By"

    def approve_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) approved successfully.")
    approve_users.short_description = "✅ Approve selected users"

    def reject_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) rejected.")
    reject_users.short_description = "❌ Reject selected users"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(ChartOverride)
class ChartOverrideAdmin(admin.ModelAdmin):
    list_display = (
        "symbol", "direction", "intensity_percent",
        "time_range_display", "duration_minutes",
        "order", "is_active", "created_at"
    )
    list_filter = ("direction", "is_active", "symbol")
    search_fields = ("symbol",)
    list_editable = ("order", "is_active")
    ordering = ("order", "-created_at")


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ("symbol", "direction", "target_price", "order", "is_active", "created_at")
    list_filter = ("direction", "is_active", "symbol")
    search_fields = ("symbol", "notes")
    list_editable = ("order", "is_active")
    ordering = ("order", "-created_at")


@admin.register(ContractPosition)
class ContractPositionAdmin(admin.ModelAdmin):
    list_display = (
        "opened_at", "account", "symbol", "direction",
        "leverage", "margin", "entry_price", "close_price",
        "pnl", "status"
    )
    list_filter = ("direction", "status", "symbol", "leverage")
    search_fields = ("symbol", "account__user__username")
    date_hierarchy = "opened_at"
    ordering = ("-opened_at",)
    readonly_fields = ("opened_at", "closed_at")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "balance", "trade_count", "deposit_count")
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("user__is_active",)

    def trade_count(self, obj):
        return obj.trades.count()
    trade_count.short_description = "Trades"

    def deposit_count(self, obj):
        return obj.deposits.count()
    deposit_count.short_description = "Deposits"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "referral_code", "referred_by", "referral_count", "created_at")
    search_fields = ("user__username", "user__email", "referral_code")
    list_filter = ("created_at", "referred_by")
    readonly_fields = ("created_at",)

    def referral_count(self, obj):
        return User.objects.filter(profile__referred_by=obj.user).count()
    referral_count.short_description = "Referrals"


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "symbol", "side", "price", "quantity", "amount", "signal")
    list_filter = ("side", "symbol", "created_at", "signal")
    search_fields = ("symbol", "account__user__username", "account__name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("account", "symbol", "side", "price", "quantity", "amount", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "amount")
    list_filter = ("created_at",)
    search_fields = ("account__user__username", "account__name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)