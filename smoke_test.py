"""
AiSTRA Backend Smoke Test — v0.3.0
====================================
Validates end-to-end API flow including v0.3.0 changes:

  Existing (regression):
   1. Health check
   2. Create session (+ verify note_count = 0)
   3. List/get sessions
   4. Create notes with new types (detail, anomaly)
   5. List notes with type filter
   6. Update note (PUT — operator correction)
   7. Telemetry ingest + query
   8. Export notes (grouped by type)
   9. Delete note
  10. End session

  New in v0.3.0:
  11. note_count increments after adding notes
  12. PATCH /notes/{id} — anomaly append
  13. Create summary note at session end
  14. Export shows correct grouping (summary → anomalies → details)

Usage:
    uvicorn app.main:app --reload
    python smoke_test.py

Author: Yulo (Backend Team)
"""

import requests
import json
from datetime import datetime, timedelta, timezone
import sys

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/sessions"


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {Colors.GREEN}PASS{Colors.END}  {label}")
    else:
        failed += 1
        print(f"  {Colors.RED}FAIL{Colors.END}  {label}")
        if detail:
            print(f"        {Colors.RED}{detail}{Colors.END}")
    return condition


def utcnow():
    return datetime.now(timezone.utc)


def main():
    global passed, failed

    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"  AiSTRA Backend Smoke Test v0.3.0")
    print(f"  {BASE_URL}")
    print(f"{'='*60}{Colors.END}\n")

    # ── 0. Health check ──────────────────────────────────────
    print(f"{Colors.YELLOW}[Health Check]{Colors.END}")
    try:
        r = requests.get(f"{BASE_URL}/health")
        if not check("GET /health returns 200", r.status_code == 200):
            print(f"\n{Colors.RED}Server not running. Start with: uvicorn app.main:app --reload{Colors.END}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"  {Colors.RED}FAIL{Colors.END}  Cannot connect to {BASE_URL}")
        print(f"\n{Colors.RED}Server not running. Start with: uvicorn app.main:app --reload{Colors.END}")
        sys.exit(1)

    r = requests.get(f"{BASE_URL}/")
    root = r.json()
    check("Version is 0.3.0", root.get("version") == "0.3.0", f"got {root.get('version')}")

    # ── 1. Create session ────────────────────────────────────
    print(f"\n{Colors.YELLOW}[Sessions]{Colors.END}")
    r = requests.post(API_URL, json={"name": "Smoke Test v0.3.0", "description": "Testing new note types"})
    check("POST /sessions returns 200", r.status_code == 200)
    session = r.json()
    sid = session["id"]
    check("Session has note_count field", "note_count" in session)
    check("note_count starts at 0", session.get("note_count") == 0, f"got {session.get('note_count')}")

    # List + get
    r = requests.get(API_URL)
    check("GET /sessions returns array", r.status_code == 200 and isinstance(r.json(), list))

    r = requests.get(f"{API_URL}/{sid}")
    check("GET /sessions/{sid} returns session", r.status_code == 200 and r.json()["id"] == sid)

    # ── 2. Create notes with new types ───────────────────────
    print(f"\n{Colors.YELLOW}[Notes — Create with types]{Colors.END}")

    # Detail note (default type)
    r = requests.post(f"{API_URL}/{sid}/notes", json={
        "timestamp": (utcnow() - timedelta(minutes=10)).isoformat(),
        "speaker": "Engineer A",
        "content": "Starting motor test sequence. All systems nominal.",
        "tags": ["motor", "test-start"],
    })
    check("POST detail note (default type)", r.status_code == 200)
    detail1 = r.json()
    check("Default type is 'detail'", detail1["type"] == "detail", f"got {detail1['type']}")
    detail1_id = detail1["id"]

    # Another detail note with explicit type
    r = requests.post(f"{API_URL}/{sid}/notes", json={
        "timestamp": (utcnow() - timedelta(minutes=8)).isoformat(),
        "speaker": "Engineer B",
        "content": "Drove rover around obstacle rock. Motor current peaked at 2.3A.",
        "type": "detail",
        "tags": ["motor", "driving"],
        "telemetry_snapshot": {"motor_current": 2.3, "battery_voltage": 32.5},
    })
    check("POST detail note (explicit type)", r.status_code == 200)
    detail2 = r.json()
    detail2_id = detail2["id"]

    # Anomaly note
    r = requests.post(f"{API_URL}/{sid}/notes", json={
        "timestamp": (utcnow() - timedelta(minutes=5)).isoformat(),
        "speaker": "Engineer A",
        "content": "Motor producing unusual vibration noise during arm extension.",
        "type": "anomaly",
        "tags": ["motor", "vibration", "arm"],
    })
    check("POST anomaly note", r.status_code == 200)
    anomaly = r.json()
    check("Type is 'anomaly'", anomaly["type"] == "anomaly")
    anomaly_id = anomaly["id"]

    # ── 3. Verify note_count ─────────────────────────────────
    print(f"\n{Colors.YELLOW}[Sessions — note_count]{Colors.END}")
    r = requests.get(f"{API_URL}/{sid}")
    session = r.json()
    check("note_count is 3 after creating 3 notes", session["note_count"] == 3, f"got {session.get('note_count')}")

    # ── 4. List notes with type filter ───────────────────────
    print(f"\n{Colors.YELLOW}[Notes — List + Filter]{Colors.END}")

    r = requests.get(f"{API_URL}/{sid}/notes")
    check("GET /notes returns all 3", r.status_code == 200 and len(r.json()) == 3)

    r = requests.get(f"{API_URL}/{sid}/notes?type=detail")
    check("Filter type=detail returns 2", len(r.json()) == 2, f"got {len(r.json())}")

    r = requests.get(f"{API_URL}/{sid}/notes?type=anomaly")
    check("Filter type=anomaly returns 1", len(r.json()) == 1, f"got {len(r.json())}")

    r = requests.get(f"{API_URL}/{sid}/notes?type=summary")
    check("Filter type=summary returns 0 (none yet)", len(r.json()) == 0)

    r = requests.get(f"{API_URL}/{sid}/notes?speaker=Engineer A")
    check("Filter speaker=Engineer A returns 2", len(r.json()) == 2, f"got {len(r.json())}")

    # ── 5. PUT — operator correction (regression) ────────────
    print(f"\n{Colors.YELLOW}[Notes — PUT update (operator edit)]{Colors.END}")

    r = requests.put(f"{API_URL}/{sid}/notes/{detail2_id}", json={
        "content": "Drove rover around obstacle rock. Motor current peaked at 2.5A (corrected).",
        "tags": ["motor", "driving", "corrected"],
    })
    check("PUT updates note content", r.status_code == 200)
    updated = r.json()
    check("Content is replaced", "2.5A (corrected)" in updated["content"])
    check("Tags are replaced", "corrected" in updated["tags"])

    # ── 6. PATCH — anomaly append (NEW in v0.3.0) ───────────
    print(f"\n{Colors.YELLOW}[Notes — PATCH append (anomaly update)]{Colors.END}")

    r = requests.patch(f"{API_URL}/{sid}/notes/{anomaly_id}", json={
        "append_content": "Vibration recurred during second arm extension. Motor temp at 85C.",
        "timestamp": (utcnow() - timedelta(minutes=1)).isoformat(),
        "telemetry_snapshot": {"motor_temp": 85.0},
    })
    check("PATCH returns 200", r.status_code == 200)
    appended = r.json()
    check("Original content preserved", "unusual vibration" in appended["content"])
    check("Appended content present", "recurred during second" in appended["content"])
    check("Telemetry snapshot merged", appended.get("telemetry_snapshot", {}).get("motor_temp") == 85.0)

    # Append again (third occurrence)
    r = requests.patch(f"{API_URL}/{sid}/notes/{anomaly_id}", json={
        "append_content": "Third occurrence. Vibration now audible from 3 meters away.",
    })
    check("Second append succeeds", r.status_code == 200)
    appended2 = r.json()
    check("All 3 entries in content", appended2["content"].count("\n[") == 2)

    # PATCH on non-existent note
    r = requests.patch(f"{API_URL}/{sid}/notes/note_nonexist", json={
        "append_content": "This should 404",
    })
    check("PATCH on missing note returns 404", r.status_code == 404)

    # ── 7. Telemetry ────────────────────────────────────────
    # POST writes to in-memory, GET reads from InfluxDB (Yuyang's instance).
    # GET tests verify endpoint health; data depends on InfluxDB being populated.
    print(f"\n{Colors.YELLOW}[Telemetry — POST (in-memory)]{Colors.END}")

    telemetry_points = [
        {"timestamp": (utcnow() - timedelta(minutes=5)).isoformat(), "channel": "battery_voltage", "value": 32.5, "unit": "V"},
        {"timestamp": (utcnow() - timedelta(minutes=4)).isoformat(), "channel": "battery_voltage", "value": 32.4, "unit": "V"},
        {"timestamp": (utcnow() - timedelta(minutes=3)).isoformat(), "channel": "motor_current", "value": 2.3, "unit": "A"},
    ]

    r = requests.post(f"{API_URL}/{sid}/telemetry", json=telemetry_points[0])
    check("Single telemetry ingest", r.status_code == 200)

    r = requests.post(f"{API_URL}/{sid}/telemetry/batch", json={"data": telemetry_points[1:]})
    check("Batch telemetry ingest", r.status_code == 200 and r.json().get("created") == 2)

    print(f"\n{Colors.YELLOW}[Telemetry — GET (InfluxDB)]{Colors.END}")

    r = requests.get(f"{API_URL}/{sid}/telemetry/channels")
    channels = r.json().get("channels", []) if r.status_code == 200 else []
    check("List channels endpoint responds", r.status_code == 200)
    if channels:
        check(f"InfluxDB has channels: {channels}", len(channels) >= 1)
    else:
        print(f"  {Colors.BLUE}SKIP{Colors.END}  No channels in InfluxDB (expected if DB not populated)")

    r = requests.get(f"{API_URL}/{sid}/telemetry/latest?channel=motor_current")
    if r.status_code == 200:
        check("Get latest motor_current", r.json().get("value") is not None,
              f"value={r.json().get('value')}")
    elif r.status_code == 404:
        print(f"  {Colors.BLUE}SKIP{Colors.END}  No motor_current in InfluxDB (expected if DB not populated)")
    else:
        check("Get latest motor_current", False, f"unexpected status={r.status_code}")

    # ── 8. Summary note (session end) ────────────────────────
    print(f"\n{Colors.YELLOW}[Notes — Summary (session end)]{Colors.END}")

    r = requests.post(f"{API_URL}/{sid}/notes", json={
        "timestamp": utcnow().isoformat(),
        "content": "Session completed motor and arm tests. One anomaly tracked: motor vibration during arm extension (3 occurrences).",
        "type": "summary",
    })
    check("POST summary note", r.status_code == 200)
    summary = r.json()
    check("Type is 'summary'", summary["type"] == "summary")

    # ── 9. Export (grouped by type) ──────────────────────────
    print(f"\n{Colors.YELLOW}[Export — grouped by type]{Colors.END}")

    # Markdown
    r = requests.get(f"{API_URL}/{sid}/notes/export?format=markdown")
    check("Markdown export returns 200", r.status_code == 200)
    md = r.text
    check("Markdown has '## Test Summary' section", "## Test Summary" in md)
    check("Markdown has '## Anomalies' section", "## Anomalies" in md)
    check("Markdown has '## Detailed Notes' section", "## Detailed Notes" in md)

    # Check ordering: summary before anomalies before details
    idx_summary = md.index("## Test Summary")
    idx_anomaly = md.index("## Anomalies")
    idx_detail = md.index("## Detailed Notes")
    check("Export order: Summary → Anomalies → Details",
          idx_summary < idx_anomaly < idx_detail)

    # JSON
    r = requests.get(f"{API_URL}/{sid}/notes/export?format=json")
    check("JSON export returns 200", r.status_code == 200)
    export = r.json()
    check("JSON has 'summary' key", "summary" in export and len(export["summary"]) == 1)
    check("JSON has 'anomalies' key", "anomalies" in export and len(export["anomalies"]) == 1)
    check("JSON has 'detailed_notes' key", "detailed_notes" in export and len(export["detailed_notes"]) == 2)

    # ── 10. Delete note (regression) ─────────────────────────
    print(f"\n{Colors.YELLOW}[Notes — Delete]{Colors.END}")

    r = requests.delete(f"{API_URL}/{sid}/notes/{detail1_id}")
    check("DELETE note returns 200", r.status_code == 200)

    r = requests.get(f"{API_URL}/{sid}")
    check("note_count decremented to 3", r.json()["note_count"] == 3, f"got {r.json().get('note_count')}")

    # ── 11. End session (regression) ─────────────────────────
    print(f"\n{Colors.YELLOW}[Sessions — End]{Colors.END}")

    r = requests.patch(f"{API_URL}/{sid}", json={"status": "ended"})
    check("PATCH status=ended", r.status_code == 200)
    session = r.json()
    check("Status is ended", session["status"] == "ended")
    check("ended_at is set", session["ended_at"] is not None)

    # ── Summary ──────────────────────────────────────────────
    total = passed + failed
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"  Results: {Colors.GREEN}{passed} passed{Colors.END}, {Colors.RED}{failed} failed{Colors.END}, {total} total")

    if failed == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.END}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}Some tests failed — check output above.{Colors.END}")

    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
