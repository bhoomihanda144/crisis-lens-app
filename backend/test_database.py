"""
CrisisLens Database Connectivity and Table Verification Script
Run this script to verify that all 7 tables exist and are reachable in Supabase.
"""
import sys
from app.database.supabase_client import get_supabase_client

REQUIRED_TABLES = [
    "incidents",
    "reports",
    "report_relationships",
    "analysis_results",
    "priority_scores",
    "verifications",
    "simulations",
]


def verify_database():
    print("=" * 60)
    print("CrisisLens Supabase Connectivity & Table Verification")
    print("=" * 60)

    try:
        supabase = get_supabase_client()
        print("[+] Supabase client initialized successfully.")
    except Exception as e:
        print(f"[-] Client initialization failed: {e}")
        print("    -> Make sure you updated SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env")
        sys.exit(1)

    print("\nChecking the 7 required tables in Supabase:")
    all_ok = True

    for table in REQUIRED_TABLES:
        try:
            # Querying 0 records to check table existence and permissions
            response = supabase.table(table).select("*").limit(0).execute()
            print(f"  [✓] Table '{table}' exists and is accessible.")
        except Exception as err:
            all_ok = False
            print(f"  [✗] Table '{table}' error: {err}")

    print("\n" + "=" * 60)
    if all_ok:
        print("SUCCESS: All 7 CrisisLens tables are present and ready!")
    else:
        print("FAILED: Some tables were missing or had permission issues.")
        print("Please ensure you ran schema.sql in your Supabase SQL Editor.")
    print("=" * 60)


if __name__ == "__main__":
    verify_database()
