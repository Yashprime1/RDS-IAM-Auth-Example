#!/usr/bin/env python3
"""Verify readonly_user can SELECT but not write via RDS IAM auth."""

import sys

from psycopg2 import errors as pg_errors

from rds_iam_connect import TABLE_NAME, connect_as

DB_USER = "readonly_user"


def expect_success(label, fn):
    try:
        fn()
        print(f"PASS  {label}")
        return True
    except Exception as exc:
        print(f"FAIL  {label}: {exc}")
        return False


def expect_denied(label, fn):
    try:
        fn()
        print(f"FAIL  {label}: expected permission denied but succeeded")
        return False
    except pg_errors.InsufficientPrivilege as exc:
        print(f"PASS  {label}: denied as expected ({exc.pgcode})")
        return True
    except Exception as exc:
        print(f"FAIL  {label}: unexpected error: {exc}")
        return False


def main():
    print(f"Connecting as {DB_USER} using RDS IAM auth token...")
    passed = 0
    total = 0

    with connect_as(DB_USER) as conn:
        conn.autocommit = True

        def select_rows():
            with conn.cursor() as cur:
                cur.execute(f"SELECT id, note FROM {TABLE_NAME} ORDER BY id LIMIT 5")
                rows = cur.fetchall()
                assert rows, "expected at least one row"

        def insert_row():
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (note) VALUES (%s)",
                    ("insert from readonly_user script",),
                )

        def update_row():
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {TABLE_NAME} SET note = %s WHERE id = 1",
                    ("readonly should not update",),
                )

        def delete_row():
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {TABLE_NAME} WHERE id = 1")

        tests = [
            ("SELECT on iam_auth_test", select_rows, expect_success),
            ("INSERT on iam_auth_test (should be denied)", insert_row, expect_denied),
            ("UPDATE on iam_auth_test (should be denied)", update_row, expect_denied),
            ("DELETE on iam_auth_test (should be denied)", delete_row, expect_denied),
        ]

        for label, action, runner in tests:
            total += 1
            if runner(label, action):
                passed += 1

    print(f"\nResult: {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
