import os

import boto3
import psycopg2

DEFAULT_HOST = "postgres-standalone.cuusbdloicfm.us-east-1.rds.amazonaws.com"
TABLE_NAME = "iam_auth_test"


def _config():
    return {
        "host": os.environ.get("RDS_HOST", DEFAULT_HOST),
        "port": int(os.environ.get("RDS_PORT", "5432")),
        "database": os.environ.get("RDS_DB", "appdb"),
        "region": os.environ.get("AWS_REGION", "us-east-1"),
        "role_arn": os.environ.get("ASSUME_ROLE_ARN", ""),
    }


def current_identity_arn() -> str:
    sts = boto3.client("sts", region_name=_config()["region"])
    return sts.get_caller_identity()["Arn"]


def _boto3_session():
    cfg = _config()
    if os.environ.get("SKIP_ASSUME_ROLE", "").lower() in ("1", "true", "yes"):
        return boto3.Session(region_name=cfg["region"])

    role_arn = cfg["role_arn"]
    if not role_arn:
        return boto3.Session(region_name=cfg["region"])

    sts = boto3.client("sts", region_name=cfg["region"])
    identity = sts.get_caller_identity()
    role_name = role_arn.split("/")[-1]
    if f"assumed-role/{role_name}/" in identity.get("Arn", ""):
        return boto3.Session(region_name=cfg["region"])

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="rds-iam-auth-test",
    )
    creds = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=cfg["region"],
    )


def generate_auth_token(db_username: str) -> str:
    cfg = _config()
    session = _boto3_session()
    client = session.client("rds", region_name=cfg["region"])
    return client.generate_db_auth_token(
        DBHostname=cfg["host"],
        Port=cfg["port"],
        DBUsername=db_username,
        Region=cfg["region"],
    )


def connect_as(db_username: str):
    cfg = _config()
    token = generate_auth_token(db_username)
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["database"],
        user=db_username,
        password=token,
        sslmode="require",
    )
