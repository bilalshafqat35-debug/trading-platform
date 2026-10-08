from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import RegisterForm, ProfileForm
from .models import Account, Profile, Signal, ChartOverride, ContractPosition

ASSETS = {
    "BTC": {"label": "Bitcoin", "type": "crypto", "binance": "BTCUSDT"},
    "ETH": {"label": "Ethereum", "type": "crypto", "binance": "ETHUSDT"},
    "SOL": {"label": "Solana", "type": "crypto", "binance": "SOLUSDT"},
    "BNB": {"label": "BNB", "type": "crypto", "binance": "BNBUSDT"},
    "XRP": {"label": "Ripple", "type": "crypto", "binance": "XRPUSDT"},
    "ADA": {"label": "Cardano", "type": "crypto", "binance": "ADAUSDT"},
    "DOGE": {"label": "Dogecoin", "type": "crypto", "binance": "DOGEUSDT"},
    "DOT": {"label": "Polkadot", "type": "crypto", "binance": "DOTUSDT"},
    "LINK": {"label": "Chainlink", "type": "crypto", "binance": "LINKUSDT"},
    "MATIC": {"label": "Polygon", "type": "crypto", "binance": "MATICUSDT"},
    "AVAX": {"label": "Avalanche", "type": "crypto", "binance": "AVAXUSDT"},
    "SHIB": {"label": "Shiba Inu", "type": "crypto", "binance": "SHIBUSDT"},
    "LTC": {"label": "Litecoin", "type": "crypto", "binance": "LTCUSDT"},
    "TRX": {"label": "Tron", "type": "crypto", "binance": "TRXUSDT"},
    "ATOM": {"label": "Cosmos", "type": "crypto", "binance": "ATOMUSDT"},
    "UNI": {"label": "Uniswap", "type": "crypto", "binance": "UNIUSDT"},
    "EURUSD": {"label": "EUR/USD", "type": "forex", "pair": "EUR/USD"},
    "GBPUSD": {"label": "GBP/USD", "type": "forex", "pair": "GBP/USD"},
    "USDJPY": {"label": "USD/JPY", "type": "forex", "pair": "USD/JPY"},
    "AUDUSD": {"label": "AUD/USD", "type": "forex", "pair": "AUD/USD"},
    "USDCAD": {"label": "USD/CAD", "type": "forex", "pair": "USD/CAD"},
    "EURGBP": {"label": "EUR/GBP", "type": "forex", "pair": "EUR/GBP"},
}

# CoinGecko IDs for crypto
CG_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "DOT": "polkadot", "LINK": "chainlink",
    "MATIC": "matic-network", "AVAX": "avalanche-2",
    "SHIB": "shiba-inu", "LTC": "litecoin", "TRX": "tron",
    "ATOM": "cosmos", "UNI": "uniswap",
}

# Coin icons
COIN_ICONS = {
    "BTC": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
    "ETH": "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
    "SOL": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
    "BNB": "https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png",
    "XRP": "https://assets.coingecko.com/coins/images/44/small/xrp-symbol-white-128.png",
    "ADA": "https://assets.coingecko.com/coins/images/975/small/cardano.png",
    "DOGE": "https://assets.coingecko.com/coins/images/5/small/dogecoin.png",
    "DOT": "https://assets.coingecko.com/coins/images/12171/small/polkadot.png",
    "LINK": "https://assets.coingecko.com/coins/images/877/small/chainlink-new-logo.png",
    "MATIC": "https://assets.coingecko.com/coins/images/4713/small/polygon.png",
    "AVAX": "https://assets.coingecko.com/coins/images/12559/small/Avalanche_Circle_RedWhite_Trans.png",
    "SHIB": "https://assets.coingecko.com/coins/images/11939/small/shiba.png",
    "LTC": "https://assets.coingecko.com/coins/images/2/small/litecoin.png",
    "TRX": "https://assets.coingecko.com/coins/images/1094/small/tron-logo.png",
    "ATOM": "https://assets.coingecko.com/coins/images/1481/small/cosmos_hub.png",
    "UNI": "https://assets.coingecko.com/coins/images/12504/small/uniswap-uni.png",
    "EURUSD": "https://flagcdn.com/w80/eu.png",
    "GBPUSD": "https://flagcdn.com/w80/gb.png",
    "USDJPY": "https://flagcdn.com/w80/jp.png",
    "AUDUSD": "https://flagcdn.com/w80/au.png",
    "USDCAD": "https://flagcdn.com/w80/ca.png",
    "EURGBP": "https://flagcdn.com/w80/eu.png",
}


# ============================================================
# HELPERS
# ============================================================

def get_trending_coins():
    coins = cache.get("trending_coins")
    if coins is not None:
        return coins
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=10)
        r.raise_for_status()
        data = r.json()
        coins = [
            {
                "name": c["item"]["name"],
                "symbol": c["item"]["symbol"],
                "rank": c["item"].get("market_cap_rank"),
                "thumb": c["item"].get("thumb"),
            }
            for c in data.get("coins", [])[:7]
        ]
        cache.set("trending_coins", coins, 600)
        return coins
    except requests.RequestException:
        return []


def get_account(user):
    account, _ = Account.objects.get_or_create(
        user=user,
        defaults={"name": user.username, "balance": 0},
    )
    return account


def get_profile(user):
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={"referral_code": user.username},
    )
    return profile


def get_holding(account, symbol):
    buys = account.trades.filter(symbol=symbol, side="BUY").aggregate(s=Sum("quantity"))["s"] or Decimal("0")
    sells = account.trades.filter(symbol=symbol, side="SELL").aggregate(s=Sum("quantity"))["s"] or Decimal("0")
    return buys - sells


def get_avg_buy_price(account, symbol):
    buys = account.trades.filter(symbol=symbol, side="BUY")
    total_qty = buys.aggregate(s=Sum("quantity"))["s"] or Decimal("0")
    total_amount = buys.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    if total_qty > 0:
        return total_amount / total_qty
    return Decimal("0")


def get_price(symbol, force_refresh=False):
    """Fetch price — Binance primary, CoinGecko fallback (crypto); TwelveData (forex).

    force_refresh=True: Cache bypass karo aur fresh price fetch karo.
    """
    if symbol not in ASSETS:
        return None

    asset = ASSETS[symbol]
    cache_key = f"price_{symbol}"

    # Cache check (agar force_refresh nahi)
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            try:
                return Decimal(cached)
            except Exception:
                pass

    if asset["type"] == "crypto":
        # Binance
        try:
            r = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": asset["binance"]},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()
                if "price" in data:
                    price = Decimal(str(data["price"]))
                    cache.set(cache_key, str(price), 30)
                    return price
        except (requests.RequestException, KeyError, InvalidOperation, ValueError):
            pass

        # CoinGecko fallback
        try:
            cg_id = CG_IDS.get(symbol)
            if cg_id:
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": cg_id, "vs_currencies": "usd"},
                    timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()
                    if cg_id in data and "usd" in data[cg_id]:
                        price = Decimal(str(data[cg_id]["usd"]))
                        cache.set(cache_key, str(price), 30)
                        return price
        except (requests.RequestException, KeyError, InvalidOperation, ValueError):
            pass

        return None

    # Forex
    try:
        r = requests.get(
            "https://api.twelvedata.com/price",
            params={"symbol": asset["pair"], "apikey": settings.TWELVEDATA_API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        price = Decimal(r.json()["price"])
        cache.set(cache_key, str(price), 30)
        return price
    except (requests.RequestException, KeyError, InvalidOperation):
        return None


def get_active_override(symbol):
    overrides = ChartOverride.objects.filter(symbol=symbol, is_active=True)
    for o in overrides:
        if o.is_currently_active():
            return o
    return None


def get_display_price(symbol):
    real_price = get_price(symbol)

    if real_price is None:
        return {
            "real_price": None, "display_price": None,
            "override_active": False, "direction": None, "intensity": None,
        }

    override = get_active_override(symbol)
    if override:
        offset = real_price * (override.intensity_percent / Decimal("100"))
        if override.direction == "UP":
            fake_price = real_price + offset
        else:
            fake_price = real_price - offset
        return {
            "real_price": real_price, "display_price": fake_price,
            "override_active": True, "direction": override.direction,
            "intensity": str(override.intensity_percent),
        }

    return {
        "real_price": real_price, "display_price": real_price,
        "override_active": False, "direction": None, "intensity": None,
    }
# ============================================================
# PAGES
# ============================================================

@login_required
def dashboard(request):
    market = request.GET.get("market", "crypto")
    symbol = "FX:EURUSD" if market == "forex" else "BINANCE:BTCUSDT"
    account = get_account(request.user)

    context = {
        "market": market,
        "symbol": symbol,
        "balance": account.balance,
        "coins": get_trending_coins(),
        "assets": [(k, v["label"]) for k, v in ASSETS.items() if v["type"] == market],
        "trades": account.trades.all()[:10],
    }
    return render(request, "trading/dashboard.html", context)


@login_required
def trade(request):
    if request.method != "POST":
        return redirect("dashboard")

    account = get_account(request.user)
    symbol = request.POST.get("symbol")
    side = request.POST.get("side")
    signal_id = request.POST.get("signal_id", "").strip()
    try:
        amount = Decimal(request.POST.get("amount", "0"))
    except InvalidOperation:
        amount = Decimal("0")

    if symbol not in ASSETS or side not in ("BUY", "SELL") or amount <= 0:
        messages.error(request, "Invalid data. Please try again.")
        return redirect("dashboard")

    # Fresh price
    cache.delete(f"price_{symbol}")
    price = get_price(symbol, force_refresh=True)
    if price is None or price <= 0:
        messages.error(request, "Price unavailable. Please try again in a moment.")
        return redirect("dashboard")

    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    quantity = (amount / price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

    if side == "BUY":
        if amount > account.balance:
            messages.error(request, "Insufficient balance. Please deposit funds first.")
            return redirect("dashboard")
        account.balance -= amount
    else:
        if quantity > get_holding(account, symbol):
            messages.error(request, "You do not own enough quantity to sell.")
            return redirect("dashboard")
        account.balance += amount

    account.save()

    signal_obj = None
    if signal_id:
        try:
            signal_obj = Signal.objects.get(pk=signal_id, is_active=True)
        except Signal.DoesNotExist:
            signal_obj = None

    account.trades.create(
        symbol=symbol, side=side, price=price,
        quantity=quantity, amount=amount, signal=signal_obj,
    )
    messages.success(request, f"{side} executed: {symbol} @ {price}")
    return redirect("dashboard")


@login_required
def portfolio(request):
    account = get_account(request.user)

    holdings = []
    total_value = Decimal("0")
    total_invested = Decimal("0")

    for symbol in ASSETS.keys():
        qty = get_holding(account, symbol)
        if qty <= 0:
            continue

        avg_buy = get_avg_buy_price(account, symbol)
        current_price = get_price(symbol, force_refresh=True) or Decimal("0")

        invested = (qty * avg_buy).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        current_value = (qty * current_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else Decimal("0")

        holdings.append({
            "symbol": symbol, "label": ASSETS[symbol]["label"],
            "type": ASSETS[symbol]["type"], "quantity": qty,
            "avg_buy": avg_buy, "current_price": current_price,
            "invested": invested, "current_value": current_value,
            "pnl": pnl, "pnl_pct": pnl_pct, "is_profit": pnl >= 0,
        })

        total_value += current_value
        total_invested += invested

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else Decimal("0")

    context = {
        "holdings": holdings, "total_value": total_value,
        "total_invested": total_invested, "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct, "is_total_profit": total_pnl >= 0,
        "balance": account.balance,
    }
    return render(request, "trading/portfolio.html", context)


@login_required
def close_position(request, symbol):
    if symbol not in ASSETS:
        messages.error(request, "Invalid symbol.")
        return redirect("portfolio")

    account = get_account(request.user)
    qty_held = get_holding(account, symbol)

    if qty_held <= 0:
        messages.error(request, f"You don't own any {symbol}.")
        return redirect("portfolio")

    if request.method != "POST":
        return redirect("portfolio")

    percent = request.POST.get("percent", "100")
    try:
        percent = Decimal(percent)
    except InvalidOperation:
        percent = Decimal("100")

    if percent <= 0 or percent > 100:
        messages.error(request, "Invalid percentage.")
        return redirect("portfolio")

    qty_to_sell = (qty_held * percent / 100).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    if qty_to_sell <= 0:
        messages.error(request, "Quantity too small to close.")
        return redirect("portfolio")

    cache.delete(f"price_{symbol}")
    current_price = get_price(symbol, force_refresh=True)
    if current_price is None or current_price <= 0:
        messages.error(request, "Price unavailable. Please try again.")
        return redirect("portfolio")

    amount = (qty_to_sell * current_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    account.balance += amount
    account.save()
    account.trades.create(
        symbol=symbol, side="SELL", price=current_price,
        quantity=qty_to_sell, amount=amount,
    )

    messages.success(request, f"Closed {percent}% of {symbol}: +${amount} added to balance.")
    return redirect("portfolio")


@login_required
def trade_history(request):
    account = get_account(request.user)
    trades_qs = account.trades.all()

    q = request.GET.get("q", "").strip()
    side = request.GET.get("side", "").strip().upper()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    if q:
        trades_qs = trades_qs.filter(symbol__icontains=q)
    if side in ("BUY", "SELL"):
        trades_qs = trades_qs.filter(side=side)
    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            trades_qs = trades_qs.filter(created_at__date__gte=d)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            trades_qs = trades_qs.filter(created_at__date__lte=d)
        except ValueError:
            pass

    total_count = trades_qs.count()
    buy_total = trades_qs.filter(side="BUY").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    sell_total = trades_qs.filter(side="SELL").aggregate(s=Sum("amount"))["s"] or Decimal("0")

    paginator = Paginator(trades_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]
    filters_qs = query_params.urlencode()

    context = {
        "page_obj": page_obj, "total_count": total_count,
        "buy_total": buy_total, "sell_total": sell_total,
        "q": q, "side": side, "date_from": date_from, "date_to": date_to,
        "filters_qs": filters_qs,
        "has_filters": bool(q or side or date_from or date_to),
    }
    return render(request, "trading/trade_history.html", context)


@login_required
def deposit_history(request):
    account = get_account(request.user)
    deposits_qs = account.deposits.all()

    total_count = deposits_qs.count()
    total_amount = deposits_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    last_deposit = deposits_qs.first()

    paginator = Paginator(deposits_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj, "total_count": total_count,
        "total_amount": total_amount, "last_deposit": last_deposit,
    }
    return render(request, "trading/deposit_history.html", context)


@login_required
def profile(request):
    user = request.user
    account = get_account(user)
    user_profile = get_profile(user)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=user)

    total_trades = account.trades.count()
    total_deposits = account.deposits.count()
    total_deposited = account.deposits.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    referrals_count = User.objects.filter(profile__referred_by=user).count()

    context = {
        "form": form, "account": account, "profile_obj": user_profile,
        "total_trades": total_trades, "total_deposits": total_deposits,
        "total_deposited": total_deposited, "referrals_count": referrals_count,
    }
    return render(request, "trading/profile.html", context)


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("profile")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "trading/password_change.html", {"form": form})


@login_required
def invite_friends(request):
    user = request.user
    user_profile = get_profile(user)
    referral_link = request.build_absolute_uri(f"/r/{user.username}/")
    referrals = User.objects.filter(profile__referred_by=user).order_by("-date_joined")

    context = {
        "profile_obj": user_profile,
        "referral_link": referral_link,
        "referrals": referrals,
    }
    return render(request, "trading/invite_friends.html", context)
# ============================================================
# API ENDPOINTS
# ============================================================

@login_required
def get_price_api(request, symbol):
    if symbol not in ASSETS:
        return JsonResponse({"error": "Invalid symbol"}, status=400)

    result = get_display_price(symbol)
    if result["display_price"] is None:
        return JsonResponse({"error": "Price unavailable"}, status=503)

    return JsonResponse({
        "symbol": symbol,
        "price": str(result["display_price"]),
        "real_price": str(result["real_price"]),
        "override_active": result["override_active"],
        "direction": result["direction"],
        "label": ASSETS[symbol]["label"],
    })


@login_required
def get_holding_api(request, symbol):
    if symbol not in ASSETS:
        return JsonResponse({"error": "Invalid symbol"}, status=400)

    account = get_account(request.user)
    qty = get_holding(account, symbol)

    return JsonResponse({
        "symbol": symbol,
        "quantity": str(qty),
        "label": ASSETS[symbol]["label"],
    })


@login_required
def get_override_status_api(request, symbol):
    if symbol not in ASSETS:
        return JsonResponse({"error": "Invalid symbol"}, status=400)

    override = get_active_override(symbol)

    if override:
        return JsonResponse({
            "symbol": symbol,
            "override_active": True,
            "direction": override.direction,
            "intensity_percent": str(override.intensity_percent),
            "end_time": override.end_time.strftime("%H:%M") if override.end_time else None,
        })

    return JsonResponse({
        "symbol": symbol,
        "override_active": False,
    })


@login_required
def get_klines_api(request, symbol):
    """Candles — Binance primary, CoinGecko fallback. 2-minute cache."""
    if symbol not in ASSETS:
        return JsonResponse({"error": "Invalid symbol"}, status=400)

    asset = ASSETS[symbol]
    if asset["type"] != "crypto":
        return JsonResponse({"error": "Klines only available for crypto"}, status=400)

    override = get_active_override(symbol)
    override_key = f"{override.direction}_{override.intensity_percent}" if override else "none"
    cache_key = f"klines_{symbol}_{override_key}"

    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    candles = []

    # Attempt 1: Binance
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": asset["binance"], "interval": "5m", "limit": 100},
            timeout=5,
        )
        if r.status_code == 200:
            raw = r.json()
            for k in raw:
                try:
                    candles.append({
                        "time": int(k[0]) // 1000,
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]),
                    })
                except (IndexError, ValueError):
                    continue
    except (requests.RequestException, ValueError):
        pass

    # Attempt 2: CoinGecko fallback
    if not candles:
        cg_id = CG_IDS.get(symbol)
        if cg_id:
            try:
                r = requests.get(
                    f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc",
                    params={"vs_currency": "usd", "days": 1},
                    timeout=10,
                )
                if r.status_code == 200:
                    raw = r.json()
                    for k in raw:
                        try:
                            candles.append({
                                "time": int(k[0]) // 1000,
                                "open": float(k[1]), "high": float(k[2]),
                                "low": float(k[3]), "close": float(k[4]),
                            })
                        except (IndexError, ValueError):
                            continue
            except (requests.RequestException, ValueError):
                pass

    if not candles:
        return JsonResponse({"error": "Failed to fetch klines"}, status=503)

    # Apply override offset
    if override:
        pct = float(override.intensity_percent) / 100.0
        factor = (1 + pct) if override.direction == "UP" else (1 - pct)
        for c in candles:
            c["open"] = round(c["open"] * factor, 6)
            c["high"] = round(c["high"] * factor, 6)
            c["low"] = round(c["low"] * factor, 6)
            c["close"] = round(c["close"] * factor, 6)

    response_data = {
        "symbol": symbol,
        "interval": "5m" if len(candles) > 50 else "1h",
        "override_active": bool(override),
        "direction": override.direction if override else None,
        "candles": candles,
    }

    cache.set(cache_key, response_data, 120)
    return JsonResponse(response_data)


@login_required
def get_market_list_api(request):
    """Market list — 22 symbols with sparklines. Cached 120 seconds."""
    cache_key = "market_list_data"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    result = []

    for symbol, asset in ASSETS.items():
        try:
            current_price = get_price(symbol)
            if current_price is None:
                continue

            spark_cache_key = f"spark_{symbol}"
            spark = cache.get(spark_cache_key) or []

            if not spark:
                if asset["type"] == "crypto":
                    # Binance klines
                    try:
                        r = requests.get(
                            "https://api.binance.com/api/v3/klines",
                            params={"symbol": asset["binance"], "interval": "1h", "limit": 24},
                            timeout=5,
                        )
                        if r.status_code == 200:
                            raw = r.json()
                            spark = [float(k[4]) for k in raw]
                    except Exception:
                        pass

                    # CoinGecko fallback
                    if not spark:
                        cg_id = CG_IDS.get(symbol)
                        if cg_id:
                            try:
                                r = requests.get(
                                    f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart",
                                    params={"vs_currency": "usd", "days": 1},
                                    timeout=10,
                                )
                                if r.status_code == 200:
                                    prices = r.json().get("prices", [])
                                    step = max(1, len(prices) // 24)
                                    spark = [float(p[1]) for p in prices[::step]][:24]
                            except Exception:
                                pass
                else:
                    # Forex - Twelve Data
                    try:
                        r = requests.get(
                            "https://api.twelvedata.com/time_series",
                            params={
                                "symbol": asset["pair"],
                                "interval": "1h",
                                "outputsize": 24,
                                "apikey": settings.TWELVEDATA_API_KEY,
                            },
                            timeout=10,
                        )
                        if r.status_code == 200:
                            values = r.json().get("values", [])
                            spark = [float(v["close"]) for v in reversed(values)]
                    except Exception:
                        pass

                if spark:
                    cache.set(spark_cache_key, spark, 600)

            # Change %
            if len(spark) >= 2:
                first = spark[0]
                last = spark[-1]
                change_pct = ((last - first) / first * 100) if first > 0 else 0
            else:
                change_pct = 0

            result.append({
                "symbol": symbol,
                "label": asset["label"],
                "icon_img": COIN_ICONS.get(symbol, ""),
                "price": str(current_price),
                "change_pct": round(change_pct, 2),
                "spark": spark,
            })
        except Exception:
            continue

    response_data = {"symbols": result}
    cache.set(cache_key, response_data, 120)
    return JsonResponse(response_data)


# ============================================================
# CONTRACT TRADING
# ============================================================

@login_required
def contract_dashboard(request):
    account = get_account(request.user)
    open_positions = account.positions.filter(status="OPEN").order_by("-opened_at")

    positions_data = []
    total_pnl = Decimal("0")
    total_margin = Decimal("0")

    for p in open_positions:
        current_price = get_price(p.symbol, force_refresh=True) or Decimal("0")

        if current_price > 0:
            if p.direction == "LONG":
                pnl = ((current_price - p.entry_price) / p.entry_price) * p.position_size
            else:
                pnl = ((p.entry_price - current_price) / p.entry_price) * p.position_size
            pnl = pnl.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        else:
            pnl = Decimal("0")

        pnl_pct = (pnl / p.margin * 100) if p.margin > 0 else Decimal("0")

        positions_data.append({
            "id": p.id,
            "symbol": p.symbol,
            "direction": p.direction,
            "leverage": p.leverage,
            "margin": p.margin,
            "position_size": p.position_size,
            "entry_price": p.entry_price,
            "current_price": current_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "is_profit": pnl >= 0,
            "opened_at": p.opened_at,
        })

        total_pnl += pnl
        total_margin += p.margin

    context = {
        "balance": account.balance,
        "positions": positions_data,
        "total_pnl": total_pnl,
        "total_margin": total_margin,
        "is_total_profit": total_pnl >= 0,
        "assets": [(k, v["label"]) for k, v in ASSETS.items() if v["type"] == "crypto"],
        "leverage_options": [1, 10, 50, 100],
    }
    return render(request, "trading/contract_dashboard.html", context)


@login_required
def open_position(request):
    if request.method != "POST":
        return redirect("contract_dashboard")

    account = get_account(request.user)
    symbol = request.POST.get("symbol")
    direction = request.POST.get("direction")
    leverage_str = request.POST.get("leverage", "1")

    try:
        margin = Decimal(request.POST.get("margin", "0"))
    except InvalidOperation:
        margin = Decimal("0")

    try:
        leverage = int(leverage_str)
    except ValueError:
        leverage = 1

    if symbol not in ASSETS:
        messages.error(request, "Invalid symbol.")
        return redirect("contract_dashboard")

    if direction not in ("LONG", "SHORT"):
        messages.error(request, "Invalid direction.")
        return redirect("contract_dashboard")

    if leverage not in (1, 10, 50, 100):
        messages.error(request, "Invalid leverage.")
        return redirect("contract_dashboard")

    if margin < Decimal("1"):
        messages.error(request, "Minimum margin is $1.")
        return redirect("contract_dashboard")

    if margin > account.balance:
        messages.error(request, "Insufficient balance. Please deposit funds first.")
        return redirect("contract_dashboard")

    cache.delete(f"price_{symbol}")
    price = get_price(symbol, force_refresh=True)
    if price is None or price <= 0:
        messages.error(request, "Price unavailable. Please try again.")
        return redirect("contract_dashboard")

    position_size = (margin * leverage).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    account.balance -= margin
    account.save()

    ContractPosition.objects.create(
        account=account,
        symbol=symbol,
        direction=direction,
        entry_price=price,
        margin=margin,
        leverage=leverage,
        position_size=position_size,
    )

    messages.success(
        request,
        f"{direction} position opened: {symbol} {leverage}x, margin ${margin}"
    )

    referer = request.META.get('HTTP_REFERER', '')
    if '/mobile/trade/' in referer:
        success_msg = f"{direction} {symbol} {leverage}x opened at ${price}"
        return redirect(f"/mobile/trade/{symbol}/?success=1&msg={success_msg}")

    return redirect("contract_dashboard")


@login_required
def close_position_contract(request, position_id):
    if request.method != "POST":
        return redirect("contract_dashboard")

    account = get_account(request.user)

    try:
        position = ContractPosition.objects.get(pk=position_id, account=account, status="OPEN")
    except ContractPosition.DoesNotExist:
        messages.error(request, "Position not found or already closed.")
        return redirect("contract_dashboard")

    cache.delete(f"price_{position.symbol}")
    current_price = get_price(position.symbol, force_refresh=True)
    if current_price is None or current_price <= 0:
        messages.error(request, "Price unavailable. Please try again.")
        return redirect("contract_dashboard")

    if position.direction == "LONG":
        pnl = ((current_price - position.entry_price) / position.entry_price) * position.position_size
    else:
        pnl = ((position.entry_price - current_price) / position.entry_price) * position.position_size

    pnl = pnl.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    payout = position.margin + pnl
    if payout < 0:
        payout = Decimal("0")

    account.balance += payout
    account.save()

    position.close_price = current_price
    position.pnl = pnl
    position.status = "CLOSED"
    position.closed_at = timezone.now()
    position.save()

    if pnl >= 0:
        messages.success(
            request,
            f"{position.direction} {position.symbol} closed: +${pnl} profit"
        )
    else:
        messages.error(
            request,
            f"{position.direction} {position.symbol} closed: ${pnl} loss"
        )

    return redirect("contract_dashboard")


@login_required
def contract_history(request):
    account = get_account(request.user)
    closed_positions = account.positions.filter(status="CLOSED").order_by("-closed_at")

    paginator = Paginator(closed_positions, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_pnl = closed_positions.aggregate(s=Sum("pnl"))["s"] or Decimal("0")
    total_count = closed_positions.count()
    wins = closed_positions.filter(pnl__gte=0).count()
    losses = closed_positions.filter(pnl__lt=0).count()

    context = {
        "page_obj": page_obj,
        "total_count": total_count,
        "total_pnl": total_pnl,
        "wins": wins,
        "losses": losses,
        "is_total_profit": total_pnl >= 0,
    }
    return render(request, "trading/contract_history.html", context)


# ============================================================
# MOBILE APIs
# ============================================================

@login_required
def mobile_trade(request, symbol):
    if symbol not in ASSETS:
        messages.error(request, "Invalid symbol.")
        return redirect("dashboard")

    account = get_account(request.user)
    asset = ASSETS[symbol]

    if asset["type"] == "crypto":
        tv_symbol = f"BINANCE:{asset['binance']}"
    else:
        pair = asset["pair"].replace("/", "")
        tv_symbol = f"FX:{pair}"

    context = {
        "symbol": symbol,
        "label": asset["label"],
        "type": asset["type"],
        "tv_symbol": tv_symbol,
        "balance": account.balance,
        "leverage_options": [1, 10, 50, 100],
    }
    return render(request, "trading/mobile_trade.html", context)


@login_required
def get_mobile_positions_api(request):
    """Mobile Orders tab — cache-first for instant response."""
    account = get_account(request.user)
    positions = account.positions.filter(status="OPEN").order_by("-opened_at")

    result = []
    total_pnl = Decimal("0")
    total_margin = Decimal("0")

    for p in positions:
        current_price = get_price(p.symbol) or Decimal("0")

        if current_price > 0:
            if p.direction == "LONG":
                pnl = ((current_price - p.entry_price) / p.entry_price) * p.position_size
            else:
                pnl = ((p.entry_price - current_price) / p.entry_price) * p.position_size
            pnl = pnl.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        else:
            pnl = Decimal("0")

        pnl_pct = (pnl / p.margin * 100) if p.margin > 0 else Decimal("0")

        result.append({
            "id": p.id,
            "symbol": p.symbol,
            "direction": p.direction,
            "leverage": p.leverage,
            "margin": str(p.margin),
            "position_size": str(p.position_size),
            "entry_price": str(p.entry_price),
            "current_price": str(current_price),
            "pnl": str(pnl),
            "pnl_pct": str(round(pnl_pct, 2)),
            "is_profit": pnl >= 0,
            "opened_at": p.opened_at.strftime("%d %b, %H:%M"),
        })

        total_pnl += pnl
        total_margin += p.margin

    return JsonResponse({
        "positions": result,
        "count": len(result),
        "total_pnl": str(total_pnl.quantize(Decimal("0.01"), rounding=ROUND_DOWN)),
        "total_margin": str(total_margin.quantize(Decimal("0.01"), rounding=ROUND_DOWN)),
        "is_profit": total_pnl >= 0,
    })


@login_required
def get_mobile_history_api(request):
    """Mobile Orders tab — closed contract positions."""
    account = get_account(request.user)
    closed = account.positions.filter(status="CLOSED").order_by("-closed_at")

    total_count = closed.count()
    wins = closed.filter(pnl__gte=0).count()
    losses = closed.filter(pnl__lt=0).count()
    total_pnl = closed.aggregate(s=Sum("pnl"))["s"] or Decimal("0")

    closed = closed[:50]

    result = []
    for p in closed:
        result.append({
            "id": p.id,
            "symbol": p.symbol,
            "direction": p.direction,
            "leverage": p.leverage,
            "margin": str(p.margin),
            "position_size": str(p.position_size),
            "entry_price": str(p.entry_price),
            "close_price": str(p.close_price) if p.close_price else "0",
            "pnl": str(p.pnl) if p.pnl is not None else "0",
            "is_profit": (p.pnl or Decimal("0")) >= 0,
            "opened_at": p.opened_at.strftime("%d %b, %H:%M"),
            "closed_at": p.closed_at.strftime("%d %b, %H:%M") if p.closed_at else "—",
        })

    return JsonResponse({
        "history": result,
        "total_count": total_count,
        "wins": wins,
        "losses": losses,
        "total_pnl": str(total_pnl.quantize(Decimal("0.01"), rounding=ROUND_DOWN)),
        "is_profit": total_pnl >= 0,
    })


# ============================================================
# AUTH
# ============================================================

def referral_redirect(request, username):
    return redirect(f"/register/?ref={username}")


def register(request):
    url_ref = request.GET.get("ref", "").strip()
    form_ref = request.POST.get("ref_code", "").strip() if request.method == "POST" else ""
    ref_code = form_ref or url_ref

    referrer = None
    if ref_code:
        try:
            referrer = User.objects.get(username__iexact=ref_code)
        except User.DoesNotExist:
            referrer = None

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            Profile.objects.create(
                user=user, referred_by=referrer,
                referral_code=user.username,
            )
            get_account(user)

            messages.success(
                request,
                "Your account has been created. Please wait for admin approval. "
                "You will be able to login once approved."
            )
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "trading/register.html", {
        "form": form, "referrer": referrer, "ref_code": ref_code,
    })