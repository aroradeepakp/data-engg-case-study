from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .schemas import Trade

try:
    from google.cloud import pubsub_v1
except ImportError:  # pragma: no cover
    pubsub_v1 = None


PORTFOLIOS = ["RATES", "CREDIT", "FX", "EQUITIES"]
COUNTERPARTIES = ["GS", "JPM", "MS", "BARC", "CITI"]
INSTRUMENTS = ["SWAP", "BOND", "OPTION", "FORWARD", "FUTURE"]


def generate_trades(count: int, seed: int | None = None, base_version: int = 1) -> list[Trade]:
    random.seed(seed)
    today = date.today()
    trades: list[Trade] = []

    for idx in range(count):
        trade_num = random.randint(1, max(5, count // 3))
        version = base_version + random.randint(0, 3)
        trade_date = today - timedelta(days=random.randint(0, 5))
        maturity_offset = random.randint(-2, 20)
        maturity_date = today + timedelta(days=maturity_offset)
        updated_at = datetime.now(timezone.utc) + timedelta(seconds=idx)

        trade = Trade(
            trade_id=f"T{trade_num:05d}",
            portfolio=random.choice(PORTFOLIOS),
            counterparty=random.choice(COUNTERPARTIES),
            instrument=random.choice(INSTRUMENTS),
            quantity=random.randint(1, 1_000),
            price=round(random.uniform(90, 110), 2),
            version=version,
            trade_date=trade_date.strftime("%Y-%m-%d"),
            maturity_date=maturity_date.strftime("%Y-%m-%d"),
            updated_at=updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        trades.append(trade)

    return trades


def write_jsonl(trades: list[Trade], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(trade.to_dict()) + "\n")


def publish_to_pubsub(trades: list[Trade], project_id: str, topic_id: str) -> None:
    if pubsub_v1 is None:  # pragma: no cover
        raise RuntimeError("google-cloud-pubsub is required to publish to Pub/Sub.")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    publish_futures = []

    for trade in trades:
        payload = json.dumps(trade.to_dict()).encode("utf-8")
        publish_futures.append(publisher.publish(topic_path, payload, trade_id=trade.trade_id))

    for future in publish_futures:
        future.result()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate mock trade events.")
    parser.add_argument("--count", type=int, default=100, help="Number of trade events to generate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    parser.add_argument("--base-version", type=int, default=1, help="Starting version floor.")
    parser.add_argument("--output", default=None, help="Optional output JSONL file path.")
    parser.add_argument("--gcp-project", default=None, help="GCP project for Pub/Sub publishing.")
    parser.add_argument("--pubsub-topic", default=None, help="Pub/Sub topic id.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    trades = generate_trades(count=args.count, seed=args.seed, base_version=args.base_version)

    if args.output:
        write_jsonl(trades, args.output)

    if args.gcp_project and args.pubsub_topic:
        publish_to_pubsub(trades, args.gcp_project, args.pubsub_topic)

    if not args.output and not (args.gcp_project and args.pubsub_topic):
        for trade in trades:
            print(json.dumps(trade.to_dict()))
