"""R2 storage client tests, run against an in-process S3 mock (moto).

No live bucket needed — moto intercepts the boto3 calls. Skips only if moto isn't
installed. We inject a moto-backed client into R2Storage, exactly how get_r2()
injects the real one.
"""

import boto3
import pytest

pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

from app.storage.r2 import R2Storage  # noqa: E402

BUCKET = "skillbridge-test"


async def test_put_get_delete_and_signed_url() -> None:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        storage = R2Storage(client, BUCKET)

        await storage.put("resumes/abc.txt", b"resume text", "text/plain")
        assert await storage.get("resumes/abc.txt") == b"resume text"

        # Signed URL points at this object and this bucket.
        url = storage.signed_url("resumes/abc.txt", ttl_seconds=60)
        assert "resumes/abc.txt" in url
        assert BUCKET in url

        await storage.delete("resumes/abc.txt")
        with pytest.raises(client.exceptions.NoSuchKey):
            await storage.get("resumes/abc.txt")
