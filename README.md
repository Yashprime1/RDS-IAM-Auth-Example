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