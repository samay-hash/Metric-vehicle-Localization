import os
from minio import Minio
from minio.error import S3Error

class StorageService:
    def __init__(self):
        # In production, replace with AWS S3 credentials
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = "bankcctv-evidence"
        self.client = None

        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            self._ensure_bucket()
        except Exception as e:
            print(f"Failed to initialize Storage Service: {e}")

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created bucket: {self.bucket_name}")
                
                # Make bucket public so frontend can access images directly
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }
                import json
                self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                
        except S3Error as err:
            print(f"MinIO bucket error: {err}")
        except Exception as e:
            print(f"MinIO connection error: {e}. Is MinIO running?")

    def upload_file(self, file_path: str, object_name: str) -> str:
        """Uploads a file to S3/MinIO and returns the public URL"""
        if not self.client:
            print("Storage service not initialized. Cannot upload.")
            return ""
            
        try:
            self.client.fput_object(self.bucket_name, object_name, file_path)
            # Return the direct URL since bucket is public
            protocol = "https" if self.secure else "http"
            return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"
        except Exception as err:
            print(f"Error uploading to S3: {err}")
            return ""

storage_service = StorageService()
