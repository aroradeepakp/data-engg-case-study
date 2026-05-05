terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_pubsub_topic" "trade_events" {
  name = var.trade_topic_name
}

resource "google_pubsub_topic" "rejected_trade_events" {
  name = var.rejected_topic_name
}

resource "google_bigquery_dataset" "trade_dw" {
  dataset_id = var.bigquery_dataset
  location   = var.bigquery_location
}

resource "google_bigquery_table" "valid_trades" {
  dataset_id = google_bigquery_dataset.trade_dw.dataset_id
  table_id   = "valid_trades"

  schema = file("${path.module}/schemas/valid_trades.json")
}

resource "google_bigquery_table" "rejected_trades" {
  dataset_id = google_bigquery_dataset.trade_dw.dataset_id
  table_id   = "rejected_trades"

  schema = file("${path.module}/schemas/rejected_trades.json")
}

resource "google_storage_bucket" "dataflow_bucket" {
  name                        = "${var.project_id}-${var.bucket_suffix}"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_composer_environment" "trade_orchestration" {
  name   = var.composer_environment_name
  region = var.region

  config {
    software_config {
      image_version = var.composer_image_version
    }
    workloads_config {
      scheduler {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }
      web_server {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
      }
      worker {
        cpu        = 1
        memory_gb  = 4
        storage_gb = 10
        min_count  = 1
        max_count  = 3
      }
    }
  }
}
