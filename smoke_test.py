"""
ASTRA Backend Smoke Test Script
================================
Validates end-to-end API flow:
1. Create session
2. Create notes
3. List notes
4. Update note (operator edit)
5. Query telemetry
6. Export notes (Markdown & JSON)
7. Delete note
8. End session

Usage:
    # Start the backend first
    uvicorn app.main:app --reload

    # Run this script
    python smoke_test.py

Author: Yulo (Backend Team)
Date: February 2025
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/sessions"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_pass(msg):
    print(f"{Colors.GREEN} PASS:{Colors.END} {msg}")

def print_fail(msg):
    print(f"{Colors.RED} FAIL:{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ  INFO:{Colors.END} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{'='*60}{Colors.END}")

# =============================================================================
# Test Functions
# =============================================================================

def test_health_check():
    """Test: Health check endpoint"""
    print_header("Test 0: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200 and response.json().get("status") == "healthy":
            print_pass("Health check passed")
            return True
        else:
            print_fail(f"Health check failed: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print_fail("Cannot connect to server. Is the backend running?")
        print_info("Start the backend with: uvicorn app.main:app --reload")
        return False


def test_create_session():
    """Test 1: Create a new session"""
    print_header("Test 1: Create Session")

    payload = {
        "name": "Smoke Test Session",
        "description": "Automated smoke test for API validation"
    }

    response = requests.post(API_URL, json=payload)

    if response.status_code == 200:
        session = response.json()
        print_pass(f"Session created: {session['id']}")
        print_info(f"Name: {session['name']}")
        print_info(f"Status: {session['status']}")
        return session['id']
    else:
        print_fail(f"Failed to create session: {response.text}")
        return None


def test_list_sessions():
    """Test 2: List all sessions"""
    print_header("Test 2: List Sessions")

    response = requests.get(API_URL)

    if response.status_code == 200:
        sessions = response.json()
        print_pass(f"Listed {len(sessions)} session(s)")
        return True
    else:
        print_fail(f"Failed to list sessions: {response.text}")
        return False


def test_get_session(session_id):
    """Test 3: Get specific session"""
    print_header("Test 3: Get Session")

    response = requests.get(f"{API_URL}/{session_id}")

    if response.status_code == 200:
        session = response.json()
        print_pass(f"Got session: {session['id']}")
        return True
    else:
        print_fail(f"Failed to get session: {response.text}")
        return False


def test_create_notes(session_id):
    """Test 4: Create multiple notes (simulating AI module)"""
    print_header("Test 4: Create Notes (AI Module Simulation)")

    notes_data = [
        {
            "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z",
            "speaker": "Engineer A",
            "content": "Starting motor test sequence",
            "type": "observation",
            "tags": ["motor", "test-start"],
            "telemetry_snapshot": None
        },
        {
            "timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat() + "Z",
            "speaker": "Engineer B",
            "content": "Motor current rising to 2.3A, voltage stable at 32.5V",
            "type": "observation",
            "tags": ["motor", "current", "voltage"],
            "telemetry_snapshot": {
                "motor_current": 2.3,
                "battery_voltage": 32.5
            }
        },
        {
            "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z",
            "speaker": "Engineer A",
            "content": "Sending shutdown command to motor",
            "type": "command",
            "tags": ["motor", "shutdown"],
            "telemetry_snapshot": None
        }
    ]

    created_notes = []
    for note_data in notes_data:
        response = requests.post(f"{API_URL}/{session_id}/notes", json=note_data)
        if response.status_code == 200:
            note = response.json()
            created_notes.append(note['id'])
            print_pass(f"Note created: {note['id']} - {note['content'][:40]}...")
        else:
            print_fail(f"Failed to create note: {response.text}")

    return created_notes


def test_list_notes(session_id):
    """Test 5: List notes with filters"""
    print_header("Test 5: List Notes (with filters)")

    # List all notes
    response = requests.get(f"{API_URL}/{session_id}/notes")
    if response.status_code == 200:
        notes = response.json()
        print_pass(f"Listed {len(notes)} note(s)")
    else:
        print_fail(f"Failed to list notes: {response.text}")
        return False

    # Filter by speaker
    response = requests.get(f"{API_URL}/{session_id}/notes?speaker=Engineer A")
    if response.status_code == 200:
        notes = response.json()
        print_pass(f"Filtered by speaker 'Engineer A': {len(notes)} note(s)")

    # Filter by type
    response = requests.get(f"{API_URL}/{session_id}/notes?type=command")
    if response.status_code == 200:
        notes = response.json()
        print_pass(f"Filtered by type 'command': {len(notes)} note(s)")

    return True


def test_update_note(session_id, note_id):
    """Test 6: Update note (operator correction)"""
    print_header("Test 6: Update Note (Operator Correction)")

    update_data = {
        "content": "Motor current rising to 2.5A (corrected from 2.3A)",
        "tags": ["motor", "current", "voltage", "corrected"]
    }

    response = requests.put(f"{API_URL}/{session_id}/notes/{note_id}", json=update_data)

    if response.status_code == 200:
        note = response.json()
        print_pass(f"Note updated: {note['id']}")
        print_info(f"New content: {note['content'][:50]}...")
        print_info(f"New tags: {note['tags']}")
        return True
    else:
        print_fail(f"Failed to update note: {response.text}")
        return False


def test_create_telemetry(session_id):
    """Test 7: Create telemetry data"""
    print_header("Test 7: Ingest Telemetry Data")

    telemetry_data = [
        {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z", "channel": "battery_voltage", "value": 32.5, "unit": "V"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat() + "Z", "channel": "battery_voltage", "value": 32.4, "unit": "V"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat() + "Z", "channel": "battery_voltage", "value": 32.3, "unit": "V"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z", "channel": "motor_current", "value": 0.0, "unit": "A"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat() + "Z", "channel": "motor_current", "value": 1.5, "unit": "A"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat() + "Z", "channel": "motor_current", "value": 2.3, "unit": "A"},
    ]

    # Single ingest
    response = requests.post(f"{API_URL}/{session_id}/telemetry", json=telemetry_data[0])
    if response.status_code == 200:
        print_pass(f"Single telemetry ingested: {telemetry_data[0]['channel']}")
    else:
        print_fail(f"Failed to ingest telemetry: {response.text}")
        return False

    # Batch ingest
    batch_payload = {"data": telemetry_data[1:]}
    response = requests.post(f"{API_URL}/{session_id}/telemetry/batch", json=batch_payload)
    if response.status_code == 200:
        result = response.json()
        print_pass(f"Batch telemetry ingested: {result['created']} records")
    else:
        print_fail(f"Failed to batch ingest: {response.text}")

    return True


def test_query_telemetry(session_id):
    """Test 8: Query telemetry data"""
    print_header("Test 8: Query Telemetry")

    # List all telemetry
    response = requests.get(f"{API_URL}/{session_id}/telemetry")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Listed {len(data)} telemetry record(s)")
    else:
        print_fail(f"Failed to list telemetry: {response.text}")
        return False

    # Filter by channel
    response = requests.get(f"{API_URL}/{session_id}/telemetry?channel=battery_voltage")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Filtered by channel 'battery_voltage': {len(data)} record(s)")

    # Get latest value (AI module would use this)
    response = requests.get(f"{API_URL}/{session_id}/telemetry/latest?channel=motor_current")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Latest motor_current: {data['value']} {data['unit']}")
    else:
        print_fail(f"Failed to get latest telemetry: {response.text}")

    # List channels
    response = requests.get(f"{API_URL}/{session_id}/telemetry/channels")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Available channels: {data['channels']}")

    return True


def test_export_notes(session_id):
    """Test 9: Export notes as Markdown and JSON"""
    print_header("Test 9: Export Notes")

    # Export as Markdown
    response = requests.get(f"{API_URL}/{session_id}/notes/export?format=markdown")
    if response.status_code == 200:
        content = response.text
        print_pass("Exported as Markdown")
        print_info("Preview (first 300 chars):")
        print(f"{Colors.BLUE}{content[:300]}...{Colors.END}")

        # Save to file
        with open("smoke_test_export.md", "w") as f:
            f.write(content)
        print_info("Saved to: smoke_test_export.md")
    else:
        print_fail(f"Failed to export as Markdown: {response.text}")
        return False

    # Export as JSON
    response = requests.get(f"{API_URL}/{session_id}/notes/export?format=json")
    if response.status_code == 200:
        content = response.text
        print_pass("Exported as JSON")

        # Save to file
        with open("smoke_test_export.json", "w") as f:
            f.write(content)
        print_info("Saved to: smoke_test_export.json")
    else:
        print_fail(f"Failed to export as JSON: {response.text}")

    return True


def test_delete_note(session_id, note_id):
    """Test 10: Delete a note"""
    print_header("Test 10: Delete Note")

    response = requests.delete(f"{API_URL}/{session_id}/notes/{note_id}")

    if response.status_code == 200:
        print_pass(f"Note deleted: {note_id}")
        return True
    else:
        print_fail(f"Failed to delete note: {response.text}")
        return False


def test_end_session(session_id):
    """Test 11: End session"""
    print_header("Test 11: End Session")

    update_data = {"status": "ended"}
    response = requests.patch(f"{API_URL}/{session_id}", json=update_data)

    if response.status_code == 200:
        session = response.json()
        print_pass(f"Session ended: {session['id']}")
        print_info(f"Status: {session['status']}")
        print_info(f"Ended at: {session['ended_at']}")
        return True
    else:
        print_fail(f"Failed to end session: {response.text}")
        return False


# =============================================================================
# Main
# =============================================================================

def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  ASTRA Backend Smoke Test{Colors.END}")
    print(f"{Colors.BOLD}  Testing API: {BASE_URL}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    # Test 0: Health check
    if not test_health_check():
        print(f"\n{Colors.RED}Cannot proceed without healthy backend. Exiting.{Colors.END}")
        sys.exit(1)
    results["passed"] += 1

    # Test 1: Create session
    session_id = test_create_session()
    if session_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print(f"\n{Colors.RED}Cannot proceed without session. Exiting.{Colors.END}")
        sys.exit(1)

    # Test 2: List sessions
    if test_list_sessions():
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 3: Get session
    if test_get_session(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 4: Create notes
    note_ids = test_create_notes(session_id)
    if note_ids:
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 5: List notes
    if test_list_notes(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 6: Update note
    if note_ids and len(note_ids) > 1:
        if test_update_note(session_id, note_ids[1]):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 7: Create telemetry
    if test_create_telemetry(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 8: Query telemetry
    if test_query_telemetry(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 9: Export notes
    if test_export_notes(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 10: Delete note
    if note_ids and len(note_ids) > 0:
        if test_delete_note(session_id, note_ids[0]):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 11: End session
    if test_end_session(session_id):
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Summary
    print_header("Test Summary")
    total = results["passed"] + results["failed"]
    print(f"\n{Colors.BOLD}Results:{Colors.END}")
    print(f"  {Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"  {Colors.RED}Failed: {results['failed']}{Colors.END}")
    print(f"  Total:  {total}")

    if results["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! Backend is ready for integration.{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[NOTICE!] Some tests failed. Please check the errors above.{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
