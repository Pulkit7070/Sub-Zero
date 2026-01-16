"""
Seed Enterprise Database with Realistic Test Data
Run: python seed_enterprise.py

This creates a full test organization with:
- 15 users across departments
- 12 SaaS tools
- Subscriptions with varying utilization
- Dependencies between tools
- Ready for decision analysis
"""

import requests
from datetime import date, timedelta
import random

BASE_URL = "http://localhost:8000"

# Realistic SaaS tools
TOOLS = [
    {"name": "Slack", "category": "communication", "vendor_domain": "slack.com", "monthly_cost": 1250, "seats": 50},
    {"name": "Google Workspace", "category": "productivity", "vendor_domain": "google.com", "monthly_cost": 1200, "seats": 50, "is_keystone": True},
    {"name": "GitHub", "category": "dev_tools", "vendor_domain": "github.com", "monthly_cost": 400, "seats": 15},
    {"name": "Figma", "category": "productivity", "vendor_domain": "figma.com", "monthly_cost": 450, "seats": 8},
    {"name": "Notion", "category": "productivity", "vendor_domain": "notion.so", "monthly_cost": 800, "seats": 45},
    {"name": "Zoom", "category": "communication", "vendor_domain": "zoom.us", "monthly_cost": 500, "seats": 20},
    {"name": "Jira", "category": "dev_tools", "vendor_domain": "atlassian.com", "monthly_cost": 700, "seats": 25},
    {"name": "Salesforce", "category": "sales", "vendor_domain": "salesforce.com", "monthly_cost": 3000, "seats": 10},
    {"name": "HubSpot", "category": "marketing", "vendor_domain": "hubspot.com", "monthly_cost": 1600, "seats": 8},
    {"name": "Datadog", "category": "dev_tools", "vendor_domain": "datadog.com", "monthly_cost": 2500, "seats": 5},
    {"name": "1Password", "category": "security", "vendor_domain": "1password.com", "monthly_cost": 400, "seats": 50, "is_keystone": True},
    {"name": "Linear", "category": "dev_tools", "vendor_domain": "linear.app", "monthly_cost": 200, "seats": 12},
]

# Test users
USERS = [
    {"name": "Sarah Chen", "email": "sarah@testcompany.com", "role": "admin", "department": "Engineering", "job_title": "CTO"},
    {"name": "Mike Johnson", "email": "mike@testcompany.com", "role": "admin", "department": "IT", "job_title": "IT Manager"},
    {"name": "Emily Davis", "email": "emily@testcompany.com", "role": "finance", "department": "Finance", "job_title": "CFO"},
    {"name": "Alex Kim", "email": "alex@testcompany.com", "role": "member", "department": "Engineering", "job_title": "Senior Developer"},
    {"name": "Jordan Lee", "email": "jordan@testcompany.com", "role": "member", "department": "Engineering", "job_title": "Developer"},
    {"name": "Taylor Swift", "email": "taylor@testcompany.com", "role": "member", "department": "Design", "job_title": "Lead Designer"},
    {"name": "Chris Martin", "email": "chris@testcompany.com", "role": "member", "department": "Sales", "job_title": "Sales Manager"},
    {"name": "Jamie Wilson", "email": "jamie@testcompany.com", "role": "member", "department": "Marketing", "job_title": "Marketing Lead"},
    {"name": "Casey Brown", "email": "casey@testcompany.com", "role": "member", "department": "Engineering", "job_title": "DevOps"},
    {"name": "Morgan Gray", "email": "morgan@testcompany.com", "role": "member", "department": "Product", "job_title": "Product Manager"},
    {"name": "Riley Adams", "email": "riley@testcompany.com", "role": "member", "department": "Support", "job_title": "Support Lead"},
    {"name": "Quinn Foster", "email": "quinn@testcompany.com", "role": "member", "department": "HR", "job_title": "HR Manager"},
    # Offboarded user (for testing departed owner scenario)
    {"name": "Sam Roberts", "email": "sam@testcompany.com", "role": "member", "department": "Engineering", "job_title": "Developer", "offboarded": True},
    {"name": "Drew Parker", "email": "drew@testcompany.com", "role": "member", "department": "Sales", "job_title": "Account Exec"},
    {"name": "Avery Thompson", "email": "avery@testcompany.com", "role": "member", "department": "Engineering", "job_title": "Junior Developer"},
]

# Tool dependencies (source depends on target)
DEPENDENCIES = [
    ("Slack", "Google Workspace", "sso", 0.9),
    ("GitHub", "Google Workspace", "sso", 0.8),
    ("Figma", "Google Workspace", "sso", 0.7),
    ("Notion", "Google Workspace", "sso", 0.7),
    ("Jira", "GitHub", "integration", 0.6),
    ("Linear", "GitHub", "integration", 0.5),
    ("Slack", "Jira", "integration", 0.4),
    ("Slack", "GitHub", "integration", 0.5),
    ("Datadog", "GitHub", "integration", 0.6),
    ("HubSpot", "Salesforce", "data_flow", 0.7),
]


def check_server():
    try:
        r = requests.get(f"{BASE_URL}/health")
        return r.status_code == 200
    except:
        return False


def create_org():
    """Create or get test organization"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations", json={
        "name": "Acme Corp",
        "domain": "acmecorp.com",
        "plan": "growth"
    })

    if r.status_code == 200:
        return r.json()
    elif r.status_code == 400:
        # Already exists, fetch it
        r = requests.get(f"{BASE_URL}/api/v1/organizations/by-domain/acmecorp.com")
        if r.status_code == 200:
            return r.json()

    print(f"Failed to create org: {r.text}")
    return None


def create_users(org_id):
    """Create test users"""
    created_users = {}

    for user in USERS:
        r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/users", json={
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "department": user["department"],
            "job_title": user["job_title"]
        })

        if r.status_code == 200:
            created_users[user["name"]] = r.json()
            print(f"  [+] Created user: {user['name']}")

            # Offboard if needed
            if user.get("offboarded"):
                requests.post(
                    f"{BASE_URL}/api/v1/organizations/{org_id}/users/{r.json()['id']}/offboard?revoke_access=false"
                )
                print(f"    => Offboarded: {user['name']}")
        elif r.status_code == 400:
            # Already exists
            r2 = requests.get(f"{BASE_URL}/api/v1/organizations/{org_id}/users?search={user['email']}")
            if r2.status_code == 200 and r2.json()['items']:
                created_users[user["name"]] = r2.json()['items'][0]
                print(f"  [+] Found existing user: {user['name']}")

    return created_users


def create_tools(org_id):
    """Create test tools"""
    created_tools = {}

    for tool in TOOLS:
        r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/tools", json={
            "name": tool["name"],
            "category": tool["category"],
            "vendor_domain": tool["vendor_domain"],
            "description": f"{tool['name']} - {tool['category'].replace('_', ' ')} tool"
        })

        if r.status_code == 200:
            created_tools[tool["name"]] = {**r.json(), **tool}
            print(f"  [+] Created tool: {tool['name']}")
        elif r.status_code == 400:
            # Already exists
            r2 = requests.get(f"{BASE_URL}/api/v1/organizations/{org_id}/tools?search={tool['name']}")
            if r2.status_code == 200 and r2.json()['items']:
                created_tools[tool["name"]] = {**r2.json()['items'][0], **tool}
                print(f"  [+] Found existing tool: {tool['name']}")

    return created_tools


def create_subscriptions(org_id, tools, users):
    """Create subscriptions with varying utilization"""
    created_subs = {}

    # Get user IDs for owners
    user_ids = {name: u["id"] for name, u in users.items()}

    # Owner assignments
    owners = {
        "Slack": "Mike Johnson",
        "Google Workspace": "Mike Johnson",
        "GitHub": "Sarah Chen",
        "Figma": "Taylor Swift",
        "Notion": "Morgan Gray",
        "Zoom": "Mike Johnson",
        "Jira": "Sarah Chen",
        "Salesforce": "Chris Martin",
        "HubSpot": "Jamie Wilson",
        "Datadog": "Casey Brown",
        "1Password": "Mike Johnson",
        "Linear": "Sam Roberts",  # Departed owner!
    }

    # Utilization scenarios
    utilization = {
        "Slack": 0.85,        # Healthy
        "Google Workspace": 0.92,  # Healthy
        "GitHub": 0.73,       # Healthy
        "Figma": 0.50,        # Moderate
        "Notion": 0.35,       # Underutilized
        "Zoom": 0.25,         # Critical - low usage
        "Jira": 0.60,         # Moderate
        "Salesforce": 0.40,   # Underutilized
        "HubSpot": 0.55,      # Moderate
        "Datadog": 0.80,      # Healthy
        "1Password": 0.90,    # Healthy
        "Linear": 0.00,       # Zero usage! (departed owner)
    }

    for tool_name, tool in tools.items():
        tool_id = tool["id"]
        paid_seats = tool.get("seats", 10)
        util = utilization.get(tool_name, 0.5)
        active_seats = int(paid_seats * util)

        # Renewal dates - some urgent, some soon
        days_to_renewal = random.choice([5, 15, 25, 45, 90, 180])
        renewal_date = (date.today() + timedelta(days=days_to_renewal)).isoformat()

        owner_name = owners.get(tool_name)
        owner_id = user_ids.get(owner_name)

        r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/subscriptions", json={
            "tool_id": tool_id,
            "plan_name": random.choice(["Pro", "Business", "Enterprise", "Team"]),
            "billing_cycle": random.choice(["monthly", "yearly"]),
            "amount_cents": tool.get("monthly_cost", 500) * 100,
            "paid_seats": paid_seats,
            "renewal_date": renewal_date,
            "auto_renew": True,
            "owner_id": owner_id,
            "department": users.get(owner_name, {}).get("department", "IT") if owner_name else "IT"
        })

        if r.status_code == 200:
            sub = r.json()
            # Update active seats
            requests.patch(f"{BASE_URL}/api/v1/organizations/{org_id}/subscriptions/{sub['id']}", json={
                "active_seats": active_seats
            })
            created_subs[tool_name] = sub
            status = "[!!]" if util < 0.3 else "[!]" if util < 0.5 else "[OK]"
            print(f"  {status} {tool_name}: {active_seats}/{paid_seats} seats ({util*100:.0f}%), renews in {days_to_renewal}d")
        else:
            print(f"  [X] Failed to create subscription for {tool_name}: {r.text}")

    return created_subs


def create_dependencies(org_id, tools):
    """Create tool dependencies"""
    for source, target, dep_type, strength in DEPENDENCIES:
        if source not in tools or target not in tools:
            continue

        source_id = tools[source]["id"]
        target_id = tools[target]["id"]

        r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/tools/{source_id}/dependencies", json={
            "source_tool_id": source_id,
            "target_tool_id": target_id,
            "dependency_type": dep_type,
            "strength": strength,
            "description": f"{source} uses {target} for {dep_type}"
        })

        if r.status_code == 200:
            print(f"  [+] {source} => {target} ({dep_type})")


def run_analysis(org_id):
    """Run decision analysis on all subscriptions"""
    r = requests.post(f"{BASE_URL}/api/v1/organizations/{org_id}/decisions/analyze-all")

    if r.status_code == 200:
        result = r.json()
        return result
    else:
        print(f"  [X] Analysis failed: {r.text}")
        return None


def main():
    print("=" * 60)
    print("Seeding Enterprise Database")
    print("=" * 60)
    print()

    # Check server
    if not check_server():
        print("[X] Server not running!")
        print("    Start with: cd backend && uvicorn app.main:app --reload")
        return

    print("[OK] Server is running")
    print()

    # Create organization
    print("[1] Creating organization...")
    org = create_org()
    if not org:
        return
    print(f"[OK] Organization: {org['name']} (ID: {org['id']})")
    print()

    # Create users
    print("[2] Creating users...")
    users = create_users(org['id'])
    print(f"[OK] Created {len(users)} users")
    print()

    # Create tools
    print("[3] Creating SaaS tools...")
    tools = create_tools(org['id'])
    print(f"[OK] Created {len(tools)} tools")
    print()

    # Create subscriptions
    print("[4] Creating subscriptions with utilization data...")
    subs = create_subscriptions(org['id'], tools, users)
    print(f"[OK] Created {len(subs)} subscriptions")
    print()

    # Create dependencies
    print("[5] Creating tool dependencies...")
    create_dependencies(org['id'], tools)
    print()

    # Run analysis
    print("[6] Running decision analysis...")
    result = run_analysis(org['id'])
    if result:
        print(f"[OK] Created {result['decisions_created']} decision recommendations")
    print()

    # Summary
    print("=" * 60)
    print("SEED COMPLETE!")
    print("=" * 60)
    print()
    print(f"Organization ID: {org['id']}")
    print()
    print("Test scenarios created:")
    print("  [CRITICAL] Zero usage: Linear (departed owner)")
    print("  [CRITICAL] Low utilization: Zoom (25%)")
    print("  [WARNING]  Underutilized: Notion, Salesforce")
    print("  [OK]       Healthy: Slack, Google Workspace, GitHub, 1Password")
    print("  [ALERT]    Departed owner: Linear (owned by Sam Roberts)")
    print("  [RENEWAL]  Urgent renewals: Some tools renew in <7 days")
    print()
    print("Next steps:")
    print(f"  1. Update ORG_ID in frontend files to: {org['id']}")
    print("  2. Start frontend: cd frontend && npm run dev")
    print("  3. Visit: http://localhost:3000/enterprise")
    print()
    print("Or test API directly at: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
