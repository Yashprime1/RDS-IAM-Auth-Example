# RDS-IAM-Auth-Example

PostgreSQL on RDS with IAM database authentication, managed via Liquibase.

## Database users

Liquibase creates two IAM-enabled PostgreSQL users:

| User | Purpose |
|---|---|
| `write_user` | SELECT, INSERT, UPDATE, DELETE on `public` schema |
| `readonly_user` | SELECT only on `public` schema |

Both have the `rds_iam` role, which allows passwordless auth using an IAM-generated token.

Run migrations via GitHub Actions (`workflow_dispatch`) or locally:

```bash
liquibase update \
  --changelog-file=changelog.xml \
  --url=jdbc:postgresql://HOST:5432/appdb \
  --username=postgres \
  --password=YOUR_PASSWORD
```

## IAM policy for connecting

Attach `iam-db-connect-policy.json` to the IAM user or role that will connect. Replace:

- `ACCOUNT_ID` — your AWS account ID
- `RESOURCE_ID` — RDS resource ID (`aws rds describe-db-instances --query 'DBInstances[0].DbiResourceId'`)

Each `Resource` ARN maps one IAM principal to one database username.

## Connect with IAM auth token

```bash
TOKEN=$(aws rds generate-db-auth-token \
  --hostname postgres-standalone.cuusbdloicfm.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --username write_user \
  --region us-east-1)

PGPASSWORD="$TOKEN" psql \
  "host=postgres-standalone.cuusbdloicfm.us-east-1.rds.amazonaws.com port=5432 dbname=appdb user=write_user sslmode=require"
```

Tokens expire after ~15 minutes; generate a new one for each connection.

## Python permission tests

Two scripts verify IAM auth against `RDS-AUTH-ROLE`:

| Script | DB user | Checks |
|---|---|---|
| `scripts/test_write_user.py` | `write_user` | SELECT/INSERT/UPDATE/DELETE pass; CREATE TABLE denied |
| `scripts/test_readonly_user.py` | `readonly_user` | SELECT passes; INSERT/UPDATE/DELETE denied |

### Prerequisites

1. Run Liquibase so changesets 2–4 exist (users + `iam_auth_test` table).
2. Attach `iam-db-connect-policy.json` to `arn:aws:iam::736548753645:role/RDS-AUTH-ROLE`.
3. Your local IAM user must be allowed to `sts:AssumeRole` on that role (if running locally).

### Run

```bash
pip install -r requirements.txt

# Assumes RDS-AUTH-ROLE automatically (default)
python scripts/test_write_user.py
python scripts/test_readonly_user.py
```

If the role is already active (e.g. on EC2/Lambda), skip re-assume:

```bash
SKIP_ASSUME_ROLE=1 python scripts/test_write_user.py
```

Optional env vars: `RDS_HOST`, `RDS_PORT`, `RDS_DB`, `AWS_REGION`, `ASSUME_ROLE_ARN`.