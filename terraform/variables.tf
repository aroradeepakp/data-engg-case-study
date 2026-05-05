variable "project_id" {
  type        = string
  description = "GCP project id."
}

variable "region" {
  type        = string
  description = "Primary GCP region."
  default     = "us-central1"
}

variable "trade_topic_name" {
  type        = string
  default     = "trade-events"
  description = "Pub/Sub topic for inbound trade events."
}

variable "rejected_topic_name" {
  type        = string
  default     = "trade-events-rejected"
  description = "Optional Pub/Sub topic for rejected trade fan-out."
}

variable "bigquery_dataset" {
  type        = string
  default     = "trade_dw"
  description = "BigQuery dataset for trade tables."
}

variable "bigquery_location" {
  type        = string
  default     = "US"
  description = "BigQuery dataset location."
}

variable "bucket_suffix" {
  type        = string
  default     = "trade-dataflow-artifacts"
  description = "Suffix used for the Dataflow artifact bucket name."
}

variable "composer_environment_name" {
  type        = string
  default     = "trade-etl-composer"
  description = "Cloud Composer environment name."
}

variable "composer_image_version" {
  type        = string
  default     = "composer-2-airflow-2.8.1"
  description = "Cloud Composer image version."
}
