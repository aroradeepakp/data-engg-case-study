# Trade ETL Case Study

Thousands of trades are generated and transmitted to a central store daily. The organization wants to modernize its data infrastructure to support real-time analytics, compliance, and reporting. You are tasked with designing and implementing a robust, scalable ETL pipeline that ingests, processes, validates, and stores trade data using
cloud-native tools.

## Solution Summary

- `src/trade_etl/generator.py` simulates trade events and can publish them to Google Pub/Sub or write them to a local JSONL file.
- `src/trade_etl/pipeline.py` implements the ETL pipeline with Apache Beam and is structured for Dataflow deployment.
- `src/trade_etl/validation.py` contains the core business rules so they are easy to test and reuse.
- `dags/trade_etl_dag.py` provides an Airflow/Composer DAG for orchestration, monitoring, and failure alerting.
- `terraform/` contains optional Terraform templates to provision Pub/Sub, BigQuery, and Composer resources.
- `sql/merge_valid_trades.sql` contains the BigQuery merge pattern for maintaining the curated latest-trade table.
- `docs/` contains the architecture diagram, setup instructions, and design notes.

## Repository Layout

```text
.
|-- dags/
|-- docs/
|-- scripts/
|-- src/trade_etl/
|-- terraform/
`-- tests/
```

## Business Rules Implemented

1. Reject a trade when its version is lower than the currently stored version for the same `trade_id`.
2. Replace the stored trade when the incoming trade has the same version.
3. Reject newly ingested trades when `maturity_date` is earlier than the pipeline run date.
4. Mark already stored valid trades as `EXPIRED` once their `maturity_date` has passed.
5. Persist rejected trades with a rejection reason and timestamp for compliance and audit.

## Local Quick Start

1. Create a Python 3.10+ virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Generate sample trades:

   ```bash
   python scripts/generate_sample_data.py --output data/trades.jsonl --count 25 --seed 7
   ```

4. Run the local batch pipeline:

   ```bash
   python -m src.trade_etl.pipeline ^
     --input_path data/trades.jsonl ^
     --existing_trades_path data/existing_trades.jsonl ^
     --valid_output_path output/valid_trades ^
     --rejected_output_path output/rejected_trades
   ```

5. Run tests:

   ```bash
   pytest
   ```

## GCP Mapping

- Messaging: Google Pub/Sub topic `trade-events`
- Processing: Apache Beam pipeline deployed to Dataflow
- Storage: BigQuery tables for `valid_trades` and `rejected_trades`
- Orchestration: Cloud Composer / Airflow DAG
- Monitoring: Airflow alert email, Beam/Dataflow logs, rejected trade audit table

For production, the recommended pattern is:

- write accepted records to a staging table from Beam
- merge staged records into the curated `valid_trades` table with a scheduled BigQuery `MERGE`
- write rejected records directly to the compliance table

## Documentation

- [Architecture](C:\Users\lenovo\Documents\Codex\2026-05-02-data-engineering-case-study-background-thousands\docs\architecture.md)
- [Setup Guide](C:\Users\lenovo\Documents\Codex\2026-05-02-data-engineering-case-study-background-thousands\docs\setup.md)

## Notes

- The Beam implementation is runnable locally with the DirectRunner for demonstration.
- The same code is structured to support Pub/Sub and BigQuery parameters for a production-style GCP deployment.
- The version resolution logic is intentionally isolated in pure Python functions for deterministic unit testing.
