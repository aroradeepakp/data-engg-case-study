from datetime import date

from src.trade_etl.schemas import Trade
from src.trade_etl.validation import INVALID_MATURITY_DATE, LOWER_VERSION, apply_trade_rules


def make_trade(trade_id: str, version: int, maturity_date: str, updated_at: str, price: float = 100.0) -> Trade:
    return Trade(
        trade_id=trade_id,
        portfolio="RATES",
        counterparty="GS",
        instrument="SWAP",
        quantity=10,
        price=price,
        version=version,
        trade_date="2026-05-01",
        maturity_date=maturity_date,
        updated_at=updated_at,
    )


def test_rejects_lower_version_than_existing():
    existing = make_trade("T00001", 3, "2026-05-20", "2026-05-01T09:00:00Z")
    incoming = [make_trade("T00001", 2, "2026-05-21", "2026-05-02T09:00:00Z")]

    final_trade, rejected = apply_trade_rules(incoming, existing, date(2026, 5, 2))

    assert final_trade.version == 3
    assert len(rejected) == 1
    assert rejected[0].reason == LOWER_VERSION


def test_replaces_same_version_trade():
    existing = make_trade("T00001", 3, "2026-05-20", "2026-05-01T09:00:00Z", price=100.0)
    replacement = make_trade("T00001", 3, "2026-05-20", "2026-05-02T09:00:00Z", price=101.5)

    final_trade, rejected = apply_trade_rules([replacement], existing, date(2026, 5, 2))

    assert not rejected
    assert final_trade.version == 3
    assert final_trade.price == 101.5


def test_rejects_trade_with_past_maturity_date():
    incoming = [make_trade("T00002", 1, "2026-05-01", "2026-05-02T09:00:00Z")]

    final_trade, rejected = apply_trade_rules(incoming, None, date(2026, 5, 2))

    assert final_trade is None
    assert len(rejected) == 1
    assert rejected[0].reason == INVALID_MATURITY_DATE


def test_marks_existing_trade_as_expired():
    existing = make_trade("T00003", 1, "2026-05-01", "2026-05-01T09:00:00Z")

    final_trade, rejected = apply_trade_rules([], existing, date(2026, 5, 2))

    assert not rejected
    assert final_trade.status == "EXPIRED"


def test_accepts_higher_version():
    existing = make_trade("T00004", 1, "2026-05-20", "2026-05-01T09:00:00Z", price=99.0)
    incoming = [make_trade("T00004", 2, "2026-05-21", "2026-05-02T09:00:00Z", price=105.0)]

    final_trade, rejected = apply_trade_rules(incoming, existing, date(2026, 5, 2))

    assert not rejected
    assert final_trade.version == 2
    assert final_trade.price == 105.0
