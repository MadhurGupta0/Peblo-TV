import boto3
from botocore.client import Config


class R2Storage:
    """Cloudflare R2 via its S3-compatible API. Not exercised in this environment
    (no R2 credentials here), but implements the same Storage protocol as
    LocalDiskStorage — switching backends in production is STORAGE_BACKEND=r2 plus
    R2 credentials/endpoint, nothing else in the app changes.
    """

    def __init__(self, *, account_id: str, access_key_id: str, secret_access_key: str, bucket: str, endpoint_url: str = "") -> None:
        self.bucket = bucket
        endpoint = endpoint_url or f"https://{account_id}.r2.cloudflarestorage.com"
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def url_for(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=3600
        )

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
