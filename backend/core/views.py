import random
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AIRecommendation, ExposurePosition, ForwardContract, Transaction
from .serializers import (ExposureSerializer, ForwardSerializer, RegisterSerializer, TransactionSerializer)
from .services import fx, market, ml, payments


# ---------- helpers ----------
def bad(msg, code=400):
    return Response({"error": str(msg)}, status=code)


def num(data, key, default=None, minimum=None, maximum=None):
    raw = data.get(key, default)
    if raw is None:
        raise ValueError(f"'{key}' is required")
    try:
        x = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be a number")
    if minimum is not None and x < minimum:
        raise ValueError(f"'{key}' must be >= {minimum}")
    if maximum is not None and x > maximum:
        raise ValueError(f"'{key}' must be <= {maximum}")
    return x


def ccy(data, key, default=None):
    return market.check_ccy(str(data.get(key, default) or "").upper())


def guarded(fn):
    """Convert validation ValueErrors into HTTP 400."""
    def wrap(*a, **k):
        try:
            return fn(*a, **k)
        except ValueError as e:
            return bad(e)
    wrap.__name__ = fn.__name__
    return wrap


def positions_of(user):
    return [dict(currency=e.currency, amount=float(e.amount), direction=e.direction, due_days=e.due_days)
            for e in user.exposures.all()]


# ---------- auth / meta ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data, status=201)


@api_view(["GET"])
def me(request):
    u = request.user
    return Response({"id": u.id, "username": u.username, "email": u.email})


@api_view(["GET"])
def meta(request):
    return Response({
        "currencies": [dict(code=c, country=market.COUNTRY[c][0], rate_per_usd=market.USD_RATES[c],
                            annual_vol_pct=market.ANNUAL_VOL[c] * 100) for c in market.CURRENCIES],
        "channels": [dict(key=k, label=payments.PROVIDERS[k]["label"], description=payments.PROVIDERS[k]["desc"])
                     for k in payments.CHANNELS],
        "providers": [dict(key=k, label=payments.PROVIDERS[k]["label"]) for k in payments.OPTIMIZER],
    })


# ---------- Module 1: payments ----------
@api_view(["POST"])
@guarded
def payment_simulate(request):
    d = request.data
    return Response(payments.simulate(d.get("channel", ""), num(d, "amount", minimum=0.01), ccy(d, "from_ccy"), ccy(d, "to_ccy")))


@api_view(["GET", "POST"])
@guarded
def payments_view(request):
    if request.method == "GET":
        return Response(TransactionSerializer(request.user.transactions.all()[:200], many=True).data)
    d = request.data
    amount, frm, to = num(d, "amount", minimum=0.01), ccy(d, "from_ccy"), ccy(d, "to_ccy")
    channel = d.get("channel", "")
    sim = payments.simulate(channel, amount, frm, to)
    q = sim["quote"]
    if not q["eligible"]:
        return bad(q["reason"])
    urgency = int(d.get("urgency", 1))
    tx = Transaction.objects.create(
        user=request.user, channel=channel, from_ccy=frm, to_ccy=to, amount=amount,
        exchange_rate=q["applied_rate"], fee_total=q["fee_total"], fx_cost=q["fx_markup_cost"],
        received_amount=q["recipient_gets"], expected_days=q["expected_days"], status="PROCESSING",
        risk_level=ml.classify_risk(market.to_usd(amount, frm), frm, to, q["expected_days"], urgency),
        recipient_name=d.get("recipient_name", ""), steps=sim["steps"])
    return Response(dict(TransactionSerializer(tx).data, warnings=sim["warnings"]), status=201)


@api_view(["POST"])
def payment_advance(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    nxt = {"INITIATED": "PROCESSING", "PROCESSING": "COMPLETED", "COMPLETED": "COMPLETED"}
    tx.status = nxt[tx.status]
    tx.save(update_fields=["status"])
    return Response(TransactionSerializer(tx).data)


# ---------- Module 2: FX ----------
@api_view(["POST"])
@guarded
def fx_scenarios(request):
    d = request.data
    return Response(fx.rate_scenarios(ccy(d, "base"), ccy(d, "quote"), int(num(d, "days", 90, 1, 730)), d.get("shocks")))


@api_view(["POST"])
@guarded
def fx_pnl(request):
    d = request.data
    direction = d.get("direction", "RECEIVABLE")
    if direction not in ("RECEIVABLE", "PAYABLE"):
        raise ValueError("direction must be RECEIVABLE or PAYABLE")
    return Response(fx.pnl(num(d, "amount", minimum=0.01), num(d, "booked_rate", minimum=1e-9),
                           num(d, "new_rate", minimum=1e-9), direction))


@api_view(["GET", "POST"])
def exposures(request):
    if request.method == "GET":
        return Response(ExposureSerializer(request.user.exposures.all(), many=True).data)
    s = ExposureSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save(user=request.user)
    return Response(s.data, status=201)


@api_view(["DELETE"])
def exposure_detail(request, pk):
    get_object_or_404(ExposurePosition, pk=pk, user=request.user).delete()
    return Response(status=204)


@api_view(["GET"])
def exposure_summary(request):
    return Response(fx.exposure_summary(positions_of(request.user), horizon_days=int(request.GET.get("horizon", 30))))


@api_view(["POST"])
@guarded
def forward_sim(request):
    d = request.data
    direction = d.get("direction", "BUY")
    if direction not in ("BUY", "SELL"):
        raise ValueError("direction must be BUY or SELL")
    base, quote = ccy(d, "base"), ccy(d, "quote")
    if base == quote:
        raise ValueError("Base and quote currency must differ")
    res = fx.forward_simulation(base, quote, num(d, "amount", minimum=0.01), int(num(d, "tenor_days", 90, 1, 730)), direction)
    if d.get("save"):
        ForwardContract.objects.create(user=request.user, base_ccy=base, quote_ccy=quote, amount=res["amount"],
                                       direction=direction, spot_rate=res["spot"], forward_rate=res["forward_rate"],
                                       tenor_days=res["tenor_days"])
    return Response(res)


@api_view(["GET"])
def forwards(request):
    return Response(ForwardSerializer(request.user.forwards.all(), many=True).data)


@api_view(["POST"])
@guarded
def hedge(request):
    d = request.data
    if d.get("currency"):
        cur = ccy(d, "currency")
        net = num(d, "net_usd")
    else:  # derive from the user's stored exposures: largest absolute net position
        summ = fx.exposure_summary(positions_of(request.user))
        rows = [r for r in summ["by_currency"] if r["currency"] != "USD"]
        if not rows:
            raise ValueError("Add exposure positions or pass currency and net_usd")
        top = max(rows, key=lambda r: abs(r["net_usd"]))
        cur, net = top["currency"], top["net_usd"]
    return Response(fx.hedge_recommendation(cur, net, int(num(d, "due_days", 60, 1, 1000)),
                                            num(d, "certainty", 0.8, 0, 1), d.get("tolerance", "medium")))


# ---------- Module 3 ----------
@api_view(["POST"])
@guarded
def optimizer(request):
    d = request.data
    return Response(payments.compare(num(d, "amount", minimum=0.01), ccy(d, "from_ccy"), ccy(d, "to_ccy"),
                                     int(num(d, "urgency", 1, 0, 2))))


# ---------- Module 4 ----------
@api_view(["GET"])
def dashboard(request):
    txs = list(request.user.transactions.all())
    summ = fx.exposure_summary(positions_of(request.user))
    vol_usd = sum(market.to_usd(float(t.amount), t.from_ccy) for t in txs)
    fees_usd = sum(market.to_usd(float(t.fee_total + t.fx_cost), t.from_ccy) for t in txs)
    ch, week, corr, risk = defaultdict(list), defaultdict(float), defaultdict(list), defaultdict(int)
    for t in txs:
        usd = market.to_usd(float(t.amount), t.from_ccy)
        ch[t.channel].append((usd, float(t.fee_total + t.fx_cost) / float(t.amount) * 100, t.expected_days))
        monday = (t.created_at - timedelta(days=t.created_at.weekday())).date().isoformat()
        week[monday] += usd
        corr[f"{t.from_ccy}->{t.to_ccy}"].append(t.expected_days)
        risk[t.risk_level] += 1
    by_channel = [dict(channel=payments.PROVIDERS.get(k, {}).get("label", k), count=len(v),
                       volume_usd=round(sum(x[0] for x in v), 2), avg_cost_pct=round(sum(x[1] for x in v) / len(v), 3),
                       avg_days=round(sum(x[2] for x in v) / len(v), 2)) for k, v in ch.items()]
    dest = defaultdict(int)
    for t in txs:
        dest[t.to_ccy] += 1
    for e in summ["by_currency"]:
        dest.setdefault(e["currency"], 0)
    country = [dict(currency=c, country=market.COUNTRY[c][0], risk_score=market.COUNTRY[c][1],
                    avg_delay_days=market.COUNTRY[c][2], transactions=n) for c, n in dest.items()]
    return Response(dict(
        kpis=dict(transactions=len(txs), volume_usd=round(vol_usd, 2), total_cost_usd=round(fees_usd, 2),
                  avg_cost_pct=round(fees_usd / vol_usd * 100, 3) if vol_usd else 0,
                  pending=sum(1 for t in txs if t.status != "COMPLETED"),
                  fx_risk_score=summ["fx_risk_score"], fx_risk_level=summ["level"],
                  var95_usd=summ["portfolio_var95_usd"]),
        exposure=summ, by_channel=by_channel,
        weekly_volume=[dict(week=k, volume_usd=round(v, 2)) for k, v in sorted(week.items())],
        risk_distribution=[dict(level=l, count=risk.get(l, 0)) for l in ("Low", "Medium", "High")],
        country_risk=sorted(country, key=lambda c: -c["risk_score"]),
        corridor_delays=sorted([dict(corridor=k, avg_days=round(sum(v) / len(v), 2), count=len(v)) for k, v in corr.items()],
                               key=lambda x: -x["avg_days"])[:8],
        pending_payments=[dict(id=t.id, corridor=f"{t.from_ccy}->{t.to_ccy}", amount=float(t.amount),
                               expected_days=t.expected_days, status=t.status) for t in txs if t.status != "COMPLETED"][:10],
    ))


@api_view(["POST"])
def seed_demo(request):
    """Create realistic sample data so the dashboard is populated for demos."""
    rng = random.Random(11)
    user, now = request.user, timezone.now()
    ccys = ["EUR", "GBP", "INR", "JPY", "AUD", "CAD", "SGD", "AED", "CNY"]
    for _ in range(25):
        to, ch = rng.choice(ccys), rng.choice(payments.CHANNELS + ["wise", "paypal"])
        amt = round(10 ** rng.uniform(2.3, 5.2), 2)
        q = payments.quote(ch, amt, "USD", to)
        if not q["eligible"]:
            ch, q = "swift", payments.quote("swift", amt, "USD", to)
        t = Transaction.objects.create(
            user=user, channel=ch, from_ccy="USD", to_ccy=to, amount=amt, exchange_rate=q["applied_rate"],
            fee_total=q["fee_total"], fx_cost=q["fx_markup_cost"], received_amount=q["recipient_gets"],
            expected_days=q["expected_days"], status=rng.choice(["COMPLETED"] * 3 + ["PROCESSING"]),
            risk_level=ml.classify_risk(amt, "USD", to, q["expected_days"], 1), recipient_name=f"Supplier {rng.randint(1, 9)}")
        Transaction.objects.filter(pk=t.pk).update(created_at=now - timedelta(days=rng.randint(0, 55)))
    if not user.exposures.exists():
        for c, a, dr, dd in [("EUR", 250000, "RECEIVABLE", 60), ("GBP", 120000, "PAYABLE", 45), ("INR", 9000000, "PAYABLE", 30),
                             ("JPY", 15000000, "RECEIVABLE", 90), ("AUD", 80000, "RECEIVABLE", 120), ("CNY", 600000, "PAYABLE", 75)]:
            ExposurePosition.objects.create(user=user, currency=c, amount=a, direction=dr, due_days=dd, description="Demo")
    return Response({"seeded": True}, status=201)


# ---------- Module 5 ----------
@api_view(["POST"])
@guarded
def ai_recommend(request):
    d = request.data
    req = dict(amount=num(d, "amount", minimum=1), from_ccy=ccy(d, "from_ccy"), to_ccy=ccy(d, "to_ccy"),
               urgency=int(num(d, "urgency", 1, 0, 2)))
    res = ml.recommend(req["amount"], req["from_ccy"], req["to_ccy"], req["urgency"])
    AIRecommendation.objects.create(user=request.user, request=req, response=res, risk_level=res["risk"]["level"])
    return Response(res)


@api_view(["GET"])
def ai_history(request):
    return Response([dict(id=r.id, request=r.request, risk_level=r.risk_level,
                          method=r.response["method"]["label"], timing=r.response["timing"]["action"],
                          created_at=r.created_at) for r in request.user.recommendations.all()[:20]])


@api_view(["GET"])
def ai_models(request):
    return Response(ml.model_info())
