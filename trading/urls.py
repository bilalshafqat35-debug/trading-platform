from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("trade/", views.trade, name="trade"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("close/<str:symbol>/", views.close_position, name="close_position"),
    path("deposits/", views.deposit_history, name="deposit_history"),
    path("trades/", views.trade_history, name="trade_history"),
    path("profile/", views.profile, name="profile"),
    path("invite/", views.invite_friends, name="invite_friends"),
    path("password/", views.change_password, name="change_password"),

    # Contract Trading
    path("contract/", views.contract_dashboard, name="contract_dashboard"),
    path("contract/open/", views.open_position, name="open_position"),
    path("contract/close/<int:position_id>/", views.close_position_contract, name="close_position_contract"),
    path("contract/history/", views.contract_history, name="contract_history"),

    # API
    path("api/price/<str:symbol>/", views.get_price_api, name="get_price_api"),
    path("api/holding/<str:symbol>/", views.get_holding_api, name="get_holding_api"),
    path("api/override-status/<str:symbol>/", views.get_override_status_api, name="get_override_status_api"),
    path("api/klines/<str:symbol>/", views.get_klines_api, name="get_klines_api"),

    # Auth
    path("r/<str:username>/", views.referral_redirect, name="referral_redirect"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="trading/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/market-list/", views.get_market_list_api, name="get_market_list_api"),
    path("mobile/trade/<str:symbol>/", views.mobile_trade, name="mobile_trade"),
    path("api/mobile-positions/", views.get_mobile_positions_api, name="get_mobile_positions_api"),
    path("api/mobile-history/", views.get_mobile_history_api, name="get_mobile_history_api"),
]