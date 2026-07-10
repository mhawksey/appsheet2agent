import os
import re
from google.cloud import storage

class GCSClient:
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.environ.get("GCS_BUCKET_NAME", "a2ui-ge-agent-creator-assets")
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None:
            self._client = storage.Client()
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            try:
                self._bucket = self.client.get_bucket(self.bucket_name)
            except Exception:
                try:
                    self._bucket = self.client.create_bucket(self.bucket_name)
                    print(f"[GCSClient] Automatically created bucket: {self.bucket_name}")
                except Exception as e:
                    print(f"[GCSClient] Warning: Could not create bucket {self.bucket_name} ({e})")
                    self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def upload_text(self, blob_name: str, content: str) -> str:
        """
        Uploads plain text content to GCS and returns the gs:// URI.
        """
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(content, content_type="text/plain")
        return f"gs://{self.bucket_name}/{blob_name}"

    def download_text(self, gcs_uri: str) -> str:
        """
        Downloads text content from GCS using a gs:// URI.
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        
        match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
        if not match:
            raise ValueError(f"Failed to parse GCS URI: {gcs_uri}")
        
        bucket_name = match.group(1)
        blob_name = match.group(2)
        
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_text()
