"""
verify_supabase.py — Verify Supabase setup from Step 1.

Tests:
  1. Publishable key can SELECT from decisions (should succeed)
  2. Publishable key cannot INSERT into decisions (should fail/be blocked)
  3. Secret key can INSERT + DELETE (should succeed — bypasses RLS)
  4. plant-photos storage bucket exists and is public
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL", "")
PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

if not SUPABASE_URL or not PUBLISHABLE_KEY or not SECRET_KEY:
    print("ERROR: SUPABASE_PROJECT_URL, SUPABASE_PUBLISHABLE_KEY, and SUPABASE_SECRET_KEY must be in .env")
    sys.exit(1)


def main():
    from supabase import create_client

    passed = 0
    failed = 0

    # --- Test 1: Publishable key SELECT ---
    print("Test 1: Publishable key can SELECT from decisions...")
    pub_client = create_client(SUPABASE_URL, PUBLISHABLE_KEY)
    try:
        result = pub_client.table("decisions").select("id").limit(1).execute()
        # Success even if 0 rows (table might be empty)
        print(f"  PASS — SELECT returned {len(result.data)} row(s)")
        passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1

    # --- Test 2: Publishable key INSERT blocked ---
    print("Test 2: Publishable key cannot INSERT into decisions...")
    test_row = {
        "cycle_timestamp": datetime.now().isoformat(),
        "light": "on",
        "air_pump": "on",
        "humidifier": "off",
        "ph_adjustment": "none",
        "reasoning": {"overall": "VERIFY TEST — should be blocked"},
        "plant_health_score": 5,
        "intervention_needed": False,
    }
    try:
        result = pub_client.table("decisions").insert(test_row).execute()
        # If we get here, the insert succeeded — that's a FAIL (RLS should block it)
        print(f"  FAIL — INSERT was NOT blocked! Row id: {result.data[0]['id']}")
        # Clean up the accidental row
        pub_client.table("decisions").delete().eq("id", result.data[0]["id"]).execute()
        failed += 1
    except Exception as e:
        error_str = str(e)
        if "policy" in error_str.lower() or "permission" in error_str.lower() or "violates" in error_str.lower() or "new row" in error_str.lower():
            print(f"  PASS — INSERT correctly blocked by RLS")
            passed += 1
        else:
            print(f"  FAIL — Unexpected error: {e}")
            failed += 1

    # --- Test 3: Secret key INSERT + DELETE ---
    print("Test 3: Secret key can INSERT and DELETE (bypasses RLS)...")
    secret_client = create_client(SUPABASE_URL, SECRET_KEY)
    test_id = None
    try:
        result = secret_client.table("decisions").insert(test_row).execute()
        test_id = result.data[0]["id"]
        print(f"  INSERT succeeded — row id: {test_id}")

        # Now delete it
        secret_client.table("decisions").delete().eq("id", test_id).execute()
        print(f"  DELETE succeeded — test row cleaned up")
        print(f"  PASS")
        passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1
        # Try to clean up if insert succeeded but delete failed
        if test_id:
            try:
                secret_client.table("decisions").delete().eq("id", test_id).execute()
            except Exception:
                print(f"  WARNING: Could not clean up test row {test_id}")

    # --- Test 4: Storage bucket exists and is public ---
    print("Test 4: plant-photos storage bucket exists and is public...")
    try:
        buckets = secret_client.storage.list_buckets()
        plant_bucket = None
        for b in buckets:
            if b.name == "plant-photos":
                plant_bucket = b
                break

        if plant_bucket is None:
            print(f"  FAIL — plant-photos bucket not found")
            failed += 1
        elif not plant_bucket.public:
            print(f"  FAIL — plant-photos bucket exists but is NOT public")
            failed += 1
        else:
            print(f"  PASS — plant-photos bucket exists and is public")
            passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1

    # --- Summary ---
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("All checks passed! Step 1 is complete.")
    else:
        print("Some checks failed — review the output above.")
    print(f"{'='*40}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
