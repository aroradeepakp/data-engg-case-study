# Setup And Execution Guide

## 1. Local Development

### Prerequisites

- Python 3.10+
- `pip`
- Optional: a GCP project if you want to deploy the pipeline

### Install

```bash
pip install -r requirements.txt
```

### Generate Mock Data

```bash
python scripts/generate_sample_data.py --output data/trades.jsonl --count 50 --seed 101
```

Optional seed snapshot:

```bash
python scripts/generate_sample_data.py --output data/existing_trades.jsonl --count 10 --seed 5 --base-version 2
```

### Run The Pipeline Locally

```bash
python -m src.trade_etl.pipeline ^
  --input_path data/trades.jsonl ^
  --existing_trades_path data/existing_trades.jsonl ^
  --valid_output_path output/valid_trades ^
  --rejected_output_path output/rejected_trades ^
  --process_date 2026-05-02
```

The pipeline writes newline-delimited JSON files:

- `output/valid_trades-00000-of-00001`
- `output/rejected_trades-00000-of-00001`

## 2. Publish To Pub/Sub

If you want to publish generated trades instead of writing a file:

```bash
python scripts/generate_sample_data.py ^
  --count 100 ^
  --gcp-project your-project-id ^
  --pubsub-topic trade-events
```

## 3. Deploy To Dataflow

Example shape of a deployment command:

```bash
python -m src.trade_etl.pipeline ^
  --runner DataflowRunner ^
  --project your-project-id ^
  --region us-central1 ^
  --temp_location gs://your-bucket/tmp ^
  --staging_location gs://your-bucket/staging ^
  --input_subscription projects/your-project-id/subscriptions/trade-events-sub ^
  --valid_table your-project-id:trade_dw.valid_trades ^
  --rejected_table your-project-id:trade_dw.rejected_trades ^
  --existing_trades_path gs://your-bucket/bootstrap/existing_trades.jsonl
```

When using Pub/Sub subscriptions, the sample pipeline applies fixed 5-minute windows before key-based reconciliation so `GroupByKey` is valid in streaming mode.

## 4. Airflow / Composer

- Copy [trade_etl_dag.py](C:\Users\lenovo\Documents\Codex\2026-05-02-data-engineering-case-study-background-thousands\dags\trade_etl_dag.py) into your Composer DAGs folder.
- Set Airflow Variables for project, region, bucket, and optional alert email.
- Point the generation step at either local generation logic or a containerized producer job.

## 5. Terraform

The optional Terraform config provisions:

- Pub/Sub topics
- BigQuery dataset and tables
- GCS bucket for Dataflow temp files
- A baseline Composer environment

Run:

```bash
cd terraform
terraform init
terraform plan -var="project_id=your-project-id"
terraform apply -var="project_id=your-project-id"
```

## Validation Logic Summary

- Lower version than current: reject with reason `LOWER_VERSION`.
- Same version as current: accept and replace stored record.
- New trade with maturity date before run date: reject with reason `INVALID_MATURITY_DATE`.
- Stored trade whose maturity date is before run date: mark status `EXPIRED`.

For a production BigQuery model, use the Beam output as an incremental staging layer and run a downstream `MERGE` into the curated valid-trades table to preserve the latest version per `trade_id`.

## Why This Stack

- Pub/Sub is a managed ingestion layer with good producer/consumer decoupling.
- Beam/Dataflow provides scalable transformation logic and a clean local-to-cloud path.
- BigQuery fits analytics and reporting requirements with SQL-native access.
- Airflow/Composer adds scheduling, retries, observability, and alert hooks.
