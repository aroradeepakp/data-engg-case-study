from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.utils.email import send_email


def notify_failure(context):
    to_email = Variable.get("trade_etl_alert_email", default_var=None)
    if not to_email:
        return

    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    execution_date = context["execution_date"]
    log_url = context["task_instance"].log_url

    send_email(
        to=to_email,
        subject=f"[Airflow] Trade ETL failure in {dag_id}",
        html_content=(
            f"<p>Task <b>{task_id}</b> failed.</p>"
            f"<p>Execution date: {execution_date}</p>"
            f"<p><a href='{log_url}'>View logs</a></p>"
        ),
    )


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": notify_failure,
}


with DAG(
    dag_id="trade_etl_pipeline",
    default_args=default_args,
    description="Generate mock trades and process them with Beam/Dataflow.",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["trade", "etl", "beam"],
) as dag:
    project_root = Variable.get("trade_etl_project_root", default_var="/home/airflow/gcs/data/trade-etl")
    process_date = "{{ ds }}"

    generate_trades = BashOperator(
        task_id="generate_trades",
        bash_command=(
            f"python {project_root}/scripts/generate_sample_data.py "
            f"--output {project_root}/data/trades.jsonl "
            "--count 100 "
            "--seed 42"
        ),
    )

    run_pipeline = BashOperator(
        task_id="run_trade_pipeline",
        bash_command=(
            f"python -m src.trade_etl.pipeline "
            f"--input_path {project_root}/data/trades.jsonl "
            f"--existing_trades_path {project_root}/data/existing_trades.jsonl "
            f"--valid_output_path {project_root}/output/valid_trades "
            f"--rejected_output_path {project_root}/output/rejected_trades "
            f"--process_date {process_date}"
        ),
        cwd=project_root,
    )

    generate_trades >> run_pipeline
