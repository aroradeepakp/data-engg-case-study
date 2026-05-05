from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from typing import Iterable

from .schemas import RejectedTrade, Trade, parse_iso_date, parse_iso_datetime


LOWER_VERSION = "LOWER_VERSION"
INVALID_MATURITY_DATE = "INVALID_MATURITY_DATE"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sort_trades_for_processing(trades: Iterable[Trade]) -> list[Trade]:
    return sorted(trades, key=lambda trade: (parse_iso_datetime(trade.updated_at), trade.version))


def mark_existing_trade_status(trade: Trade, process_date: date) -> Trade:
    if parse_iso_date(trade.maturity_date) < process_date:
        return replace(trade, status="EXPIRED")
    return replace(trade, status="VALID")


def apply_trade_rules(
    incoming_trades: Iterable[Trade],
    existing_trade: Trade | None,
    process_date: date,
) -> tuple[Trade | None, list[RejectedTrade]]:
    rejections: list[RejectedTrade] = []
    current_trade = mark_existing_trade_status(existing_trade, process_date) if existing_trade else None

    for trade in sort_trades_for_processing(incoming_trades):
        if parse_iso_date(trade.maturity_date) < process_date:
            rejections.append(
                RejectedTrade(
                    trade_id=trade.trade_id,
                    version=trade.version,
                    reason=INVALID_MATURITY_DATE,
                    rejected_at=_now_utc(),
                    payload=trade.to_dict(),
                )
            )
            continue

        if current_trade and trade.version < current_trade.version:
            rejections.append(
                RejectedTrade(
                    trade_id=trade.trade_id,
                    version=trade.version,
                    reason=LOWER_VERSION,
                    rejected_at=_now_utc(),
                    payload=trade.to_dict(),
                )
            )
            continue

        next_status = "EXPIRED" if parse_iso_date(trade.maturity_date) < process_date else "VALID"
        current_trade = replace(trade, status=next_status)

    return current_trade, rejections
