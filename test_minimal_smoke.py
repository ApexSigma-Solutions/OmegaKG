#!/usr/bin/env python3
"""Minimal smoke test - just send a capture request and check response"""

import requests
import json
import time

print("=" * 70)
print("MINIMAL SMOKE TEST: Capture Request Only")
print("=" * 70)

# Wait for server
print("\n[1/3] Waiting 3 seconds for server to start...")
time.sleep(3)

# Get JWT token by exchanging API key
print("[2/3] Getting JWT token...")
api_key = "N7F6JKUecfl69WTC83rN7qJTMr2H6cylDyIDNM6Npu8y5KczFaAXQoPFYovlQQAP"
try:
    auth_response = requests.post(
        "http://localhost:8002/auth/token", headers={"X-API-Key": api_key}, timeout=5
    )

    if auth_response.status_code == 200:
        token = auth_response.json()["access_token"]
        print("✓ Got JWT token")
    else:
        print(f"✗ Auth failed ({auth_response.status_code}): {auth_response.text}")
        exit(1)
except Exception as e:
    print(f"✗ Auth error: {e}")
    exit(1)

# Send capture request with JWT token
print("[3/3] Sending capture request...")
try:
    payload = {
        "platform": "Terminal",
        "url": f"http://localhost/smoke-test-{time.time()}",
        "title": f"Phase 3 Verification Test {time.time()}",
        "messages": [
            {
                "role": "user",
                "content": f"Phase 3 verification test at {time.time()}: The eagle has landed.",
            }
        ],
    }

    start = time.time()
    # Use JWT Bearer token for authentication
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "http://localhost:8002/capture", json=payload, headers=headers, timeout=10
    )
    elapsed = time.time() - start

    print(f"\n✓ Response received in {elapsed*1000:.0f}ms")
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
        print("\n" + "=" * 70)
        print("✅ SMOKE TEST PASSED - Capture request successful!")
        print("=" * 70)
    else:
        print(f"✗ Request failed: {response.text}")

except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to server at http://localhost:8002")
    print("  Make sure the capture server is running")
except Exception as e:
    print(f"✗ Error: {e}")
