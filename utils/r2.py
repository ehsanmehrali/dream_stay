import boto3
from botocore.config import Config as BotoCfg
from config import Config

def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=Config.R2_ENDPOINT,
        aws_access_key_id=Config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=Config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=BotoCfg(signature_version="s3v4", s3={"addressing_style": "virtual"})
    )