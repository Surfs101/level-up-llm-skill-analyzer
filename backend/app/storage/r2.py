"""Cloudflare R2 object storage (S3-compatible).

Holds resume artifacts: the staged upload binary (briefly) and the extracted .txt.
Per §11 the .txt is fetched only through short-lived signed URLs, and the client is
locked to one bucket — it never touches a user-supplied bucket or URL, so there's no
SSRF surface here.

boto3 is synchronous, so each network call runs in a thread (`asyncio.to_thread`) to
keep the interface async without pulling in aioboto3. The client is injected into
R2Storage, which keeps it trivially testable against moto.
"""

import asyncio
from functools import lru_cache
from typing import Any, cast

import boto3
from botocore.config import Config

from app.config import get_settings

# How long a signed .txt URL stays valid. Short by design — just long enough for the
# worker (or a one-off admin fetch) to read the object.
SIGNED_URL_TTL_SECONDS = 300


class R2Storage:
    """Put/get/delete and signed-URL access, all scoped to a single bucket."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def put(self, key: str, body: bytes, content_type: str = "text/plain") -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        data = await asyncio.to_thread(response["Body"].read)
        return cast(bytes, data)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    def signed_url(self, key: str, ttl_seconds: int = SIGNED_URL_TTL_SECONDS) -> str:
        """A time-limited GET URL for one object. Signing is local (no network)."""
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=ttl_seconds,
        )
        return str(url)


@lru_cache(maxsize=1)
def get_r2() -> R2Storage:
    """Build (once) the S3 client from settings, bound to our bucket.

    In production the endpoint is Cloudflare R2, derived from the account ID. In local
    dev, setting R2_ENDPOINT_URL points the same client at MinIO instead. MinIO only
    speaks path-style addressing (host/bucket, not bucket.host), so we force that
    whenever a custom endpoint is set.
    """
    settings = get_settings()
    if settings.r2_endpoint_url:
        endpoint_url = settings.r2_endpoint_url
        config = Config(s3={"addressing_style": "path"})
    else:
        endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        config = None
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=config,
    )
    return R2Storage(client, settings.r2_bucket)
