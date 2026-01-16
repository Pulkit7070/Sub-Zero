"""
Quick test script for Enterprise API
Run: python test_enterprise.py
"""

import requests

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if server is running"""
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"✓ Server health: {r.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ Server not running! Start with: uvicorn app.main:app --reload")
        return False

def test_create_org():
    """Create a test organization"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations", json={
        "name": "Test Company",
        "domain": "testcompany.com"
    })
    if r.status_code == 200:
        org = r.json()
        print(f"✓ Created org: {org['name']} (ID: {org['id']})")
        return org['id']
    elif r.status_code == 400:
        print("! Org already exists, fetching...")
        r = requests.get(f"{BASE_URL}/api/v1/organizations/by-domain/testcompany.com")
        if r.status_code == 200:
            org = r.json()
            print(f"✓ Found org: {org['name']} (ID: {org['id']})")
            return org['id']
    print(f"✗ Failed to create org: {r.text}")
    return None

def test_create_user(org_id):
    """Create a test user"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/users", json={
        "email": "admin@testcompany.com",
        "name": "Test Admin",
        "role": "admin",
        "department": "Engineering"
    })
    if r.status_code == 200:
        user = r.json()
        print(f"✓ Created user: {user['name']} (ID: {user['id']})")
        return user['id']
    elif r.status_code == 400:
        print("! User already exists")
        return None
    print(f"✗ Failed to create user: {r.text}")
    return None

def test_create_tool(org_id):
    """Create a test tool"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/tools", json={
        "name": "Slack",
        "category": "communication",
        "vendor_domain": "slack.com",
        "description": "Team communication"
    })
    if r.status_code == 200:
        tool = r.json()
        print(f"✓ Created tool: {tool['name']} (ID: {tool['id']})")
        return tool['id']
    elif r.status_code == 400:
        print("! Tool already exists")
        # Get existing tools
        r = requests.get(f"{BASE_URL}/api/v1/organizations/{org_id}/tools")
        if r.status_code == 200 and r.json()['items']:
            tool = r.json()['items'][0]
            print(f"✓ Found tool: {tool['name']} (ID: {tool['id']})")
            return tool['id']
    print(f"✗ Failed to create tool: {r.text}")
    return None

def test_create_subscription(org_id, tool_id):
    """Create a test subscription"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/subscriptions", json={
        "tool_id": tool_id,
        "plan_name": "Business",
        "billing_cycle": "monthly",
        "amount_cents": 1500,  # $15/month
        "paid_seats": 10,
        "renewal_date": "2025-03-01"
    })
    if r.status_code == 200:
        sub = r.json()
        print(f"✓ Created subscription: {sub['plan_name']} (ID: {sub['id']})")
        return sub['id']
    print(f"✗ Failed to create subscription: {r.text}")
    return None

def test_dashboard(org_id):
    """Test dashboard stats"""
    r = requests.get(f"{BASE_URL}/api/v1/organizations/{org_id}/dashboard/stats")
    if r.status_code == 200:
        stats = r.json()
        print(f"✓ Dashboard stats:")
        print(f"  - Tools: {stats['total_tools']}")
        print(f"  - Users: {stats['total_users']}")
        print(f"  - Monthly spend: ${stats['monthly_spend_cents']/100:.2f}")
        return True
    print(f"✗ Failed to get dashboard: {r.text}")
    return False

def test_analyze(org_id, sub_id):
    """Test decision analysis"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/decisions/analyze/{sub_id}")
    if r.status_code == 200:
        result = r.json()
        decision = result['decision']
        print(f"✓ Analysis result for {result['tool_name']}:")
        print(f"  - Decision: {decision['type']}")
        print(f"  - Confidence: {decision['confidence']*100:.0f}%")
        print(f"  - Explanation: {decision['explanation']}")
        return True
    print(f"✗ Analysis failed: {r.text}")
    return False

def main():
    print("=" * 50)
    print("Enterprise API Test")
    print("=" * 50)
    print()

    # Test health
    if not test_health():
        return
    print()

    # Create org
    org_id = test_create_org()
    if not org_id:
        return
    print()

    # Create user
    test_create_user(org_id)
    print()

    # Create tool
    tool_id = test_create_tool(org_id)
    print()

    # Create subscription
    if tool_id:
        sub_id = test_create_subscription(org_id, tool_id)
        print()

        # Test analysis
        if sub_id:
            test_analyze(org_id, sub_id)
            print()

    # Test dashboard
    test_dashboard(org_id)
    print()

    print("=" * 50)
    print(f"✓ Tests complete!")
    print(f"")
    print(f"Organization ID: {org_id}")
    print(f"")
    print(f"Next steps:")
    print(f"1. Update ORG_ID in frontend pages to: {org_id}")
    print(f"2. Start frontend: cd frontend && npm run dev")
    print(f"3. Visit: http://localhost:3000/enterprise")
    print("=" * 50)

if __name__ == "__main__":
    main()
