from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Iterable

import apache_beam as beam
from apache_beam.io import ReadFromPubSub
from apache_beam.io.filesystems import FileSystems
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.pvalue import AsSingleton
from apache_beam.transforms.window import FixedWindows

from .schemas import Trade, normalize_trade
from .validation import apply_trade_rules


def read_jsonl_records(path: str) -> list[dict]:
    if not path:
        return []

    records: list[dict] = []
    with FileSystems.open(path) as handle:
        for raw_line in handle:
            line = raw_line.decode("utf-8").strip()
            if line:
                records.append(json.loads(line))
    return records


def parse_message(payload: bytes) -> dict:
    return json.loads(payload.decode("utf-8"))


class ReconcileTradesDoFn(beam.DoFn):
    def process(self, element: tuple[str, list[dict]], existing_snapshot: dict[str, dict], process_date: str):
        trade_id, records = element
        incoming: list[Trade] = []

        for record in records:
            if record.get("_record_type") == "incoming":
                incoming.append(normalize_trade(record["trade"]))

        existing_trade = None
        if trade_id in existing_snapshot:
            existing_trade = normalize_trade(existing_snapshot[trade_id])

        final_trade, rejected = apply_trade_rules(
            incoming_trades=incoming,
            existing_trade=existing_trade,
            process_date=datetime.strptime(process_date, "%Y-%m-%d").date(),
        )

        if final_trade:
            yield beam.pvalue.TaggedOutput("valid", final_trade.to_dict())

        for rejected_trade in rejected:
            yield beam.pvalue.TaggedOutput("rejected", rejected_trade.to_dict())


def build_pipeline(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default=None, help="Local or GCS JSONL trade event file.")
    parser.add_argument("--input_subscription", default=None, help="Pub/Sub subscription path.")
    parser.add_argument("--existing_trades_path", default=None, help="JSONL snapshot of current valid trades.")
    parser.add_argument("--valid_output_path", required=False, help="Output path prefix for valid trades.")
    parser.add_argument("--rejected_output_path", required=False, help="Output path prefix for rejected trades.")
    parser.add_argument("--valid_table", default=None, help="BigQuery table for valid trades.")
    parser.add_argument("--rejected_table", default=None, help="BigQuery table for rejected trades.")
    parser.add_argument("--process_date", default=datetime.utcnow().strftime("%Y-%m-%d"))
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args, save_main_session=True)

    existing_snapshot = {}
    for record in read_jsonl_records(known_args.existing_trades_path):
        trade = normalize_trade(record)
        existing_snapshot[trade.trade_id] = trade.to_dict()

    if not known_args.input_path and not known_args.input_subscription:
        raise ValueError("Either --input_path or --input_subscription must be provided.")

    with beam.Pipeline(options=options) as pipeline:
        if known_args.input_subscription:
            incoming_records = (
                pipeline
                | "ReadFromPubSub" >> ReadFromPubSub(subscription=known_args.input_subscription)
                | "ParsePubSubMessages" >> beam.Map(parse_message)
                | "WindowStreamingEvents" >> beam.WindowInto(FixedWindows(300))
            )
        else:
            incoming_records = (
                pipeline
                | "ReadInputFile" >> beam.io.ReadFromText(known_args.input_path)
                | "ParseInputJson" >> beam.Map(json.loads)
            )

        tagged_incoming = (
            incoming_records
            | "TagIncoming" >> beam.Map(
                lambda trade: (
                    trade["trade_id"],
                    {"_record_type": "incoming", "trade": trade},
                )
            )
        )

        valid_results, rejected_results = (
            tagged_incoming
            | "GroupByTradeId" >> beam.GroupByKey()
            | "ReconcileTradeRecords"
            >> beam.ParDo(
                ReconcileTradesDoFn(),
                existing_snapshot=AsSingleton(
                    pipeline | "CreateSnapshotSideInput" >> beam.Create([existing_snapshot])
                ),
                process_date=known_args.process_date,
            ).with_outputs("valid", "rejected")
        )

        if known_args.valid_output_path:
            _ = (
                valid_results
                | "SerializeValidJson" >> beam.Map(json.dumps)
                | "WriteValidJson"
                >> beam.io.WriteToText(
                known_args.valid_output_path,
                file_name_suffix=".jsonl",
                shard_name_template="-SSSSS-of-NNNNN",
                )
            )

        if known_args.rejected_output_path:
            _ = (
                rejected_results
                | "SerializeRejectedJson" >> beam.Map(json.dumps)
                | "WriteRejectedJson"
                >> beam.io.WriteToText(
                known_args.rejected_output_path,
                file_name_suffix=".jsonl",
                shard_name_template="-SSSSS-of-NNNNN",
                )
            )

        if known_args.valid_table:
            _ = valid_results | "WriteValidBQ" >> beam.io.WriteToBigQuery(
                known_args.valid_table,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )

        if known_args.rejected_table:
            _ = rejected_results | "WriteRejectedBQ" >> beam.io.WriteToBigQuery(
                known_args.rejected_table,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )


def main() -> None:
    build_pipeline()


if __name__ == "__main__":
    main()
