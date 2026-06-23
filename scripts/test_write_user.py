#!/usr/bin/env python3
"""Verify write_user can run DML but not DDL via RDS IAM auth."""

import sys

import psycopg2
from psycopg2 import errors as pg_errors

from rds_iam_connect import TABLE_NAME, connect_as

DB_USER = "write_user"


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
                cur.execute(f"SELECT count(*) FROM {TABLE_NAME}")
                count = cur.fetchone()[0]
                assert count >= 1, "expected at least one row"

        def insert_row():
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (note) VALUES (%s) RETURNING id",
                    ("insert from write_user script",),
                )
                row_id = cur.fetchone()[0]
                assert row_id is not None

        def update_row():
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET note = %s
                    WHERE note = %s
                    """,
                    ("updated by write_user", "insert from write_user script"),
                )
                assert cur.rowcount == 1, "expected one updated row"

        def delete_row():
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {TABLE_NAME} WHERE note = %s",
                    ("updated by write_user",),
                )
                assert cur.rowcount == 1, "expected one deleted row"

        def create_table():
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE write_user_should_not_create (id INT)")

        tests = [
            ("SELECT on iam_auth_test", select_rows, expect_success),
            ("INSERT on iam_auth_test", insert_row, expect_success),
            ("UPDATE on iam_auth_test", update_row, expect_success),
            ("DELETE on iam_auth_test", delete_row, expect_success),
            ("CREATE TABLE (should be denied)", create_table, expect_denied),
        ]

        for label, action, runner in tests:
            total += 1
            if runner(label, action):
                passed += 1

    print(f"\nResult: {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
