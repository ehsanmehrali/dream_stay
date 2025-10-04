import boto3
from botocore.config import Config as BotoCfg
from config import Config


_BOTO_CFG = BotoCfg(
    signature_version="s3v4",
    s3={"addressing_style": "virtual"},
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
    max_pool_connections=32,
)


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=Config.R2_ENDPOINT,
        aws_access_key_id=Config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=Config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=_BOTO_CFG,
    )