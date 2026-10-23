resource "google_storage_bucket_iam_member" "deployer_metadata" {
  for_each = {
    state    = google_storage_bucket.state.name
    delivery = google_storage_bucket.delivery.name
  }
  bucket = each.value
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.deployer.email}"
}
