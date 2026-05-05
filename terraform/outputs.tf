output "trade_topic" {
  value = google_pubsub_topic.trade_events.name
}

output "rejected_topic" {
  value = google_pubsub_topic.rejected_trade_events.name
}

output "dataset_id" {
  value = google_bigquery_dataset.trade_dw.dataset_id
}

output "dataflow_bucket" {
  value = google_storage_bucket.dataflow_bucket.name
}

output "composer_name" {
  value = google_composer_environment.trade_orchestration.name
}
