from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class Trade:
    trade_id: str
    portfolio: str
    counterparty: str
    instrument: str
    quantity: int
    price: float
    version: int
    trade_date: str
    maturity_date: str
    updated_at: str
    status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RejectedTrade:
    trade_id: str
    version: int
    reason: str
    rejected_at: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_iso_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def normalize_trade(raw: dict[str, Any]) -> Trade:
    return Trade(
        trade_id=str(raw["trade_id"]),
        portfolio=str(raw["portfolio"]),
        counterparty=str(raw["counterparty"]),
        instrument=str(raw["instrument"]),
        quantity=int(raw["quantity"]),
        price=float(raw["price"]),
        version=int(raw["version"]),
        trade_date=str(raw["trade_date"]),
        maturity_date=str(raw["maturity_date"]),
        updated_at=str(raw["updated_at"]),
        status=str(raw.get("status", "VALID")),
    )
