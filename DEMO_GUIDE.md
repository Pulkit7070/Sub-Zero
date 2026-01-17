# Sub-Zero Enterprise Demo Guide

This guide explains the demo functionality and how the numbers are calculated in the dashboard.

## Demo Overview

The demo showcases **Acme Corporation**, a fictional company with 156 employees using various SaaS tools. All data is realistic and demonstrates the full capabilities of the Sub-Zero platform.

## 🏠 Landing Page (http://localhost:3000)

**Two-Path Selection:**

- **Personal**: For individual users to manage their personal subscriptions
- **Enterprise**: For organizations to manage company-wide subscriptions (demo mode)

## 📊 Enterprise Dashboard (http://localhost:3000/enterprise)

### Key Metrics

| Metric                   | Value        | Calculation                                                |
| ------------------------ | ------------ | ---------------------------------------------------------- |
| **Total Tools**          | 47           | Number of unique SaaS tools discovered in the organization |
| **Active Subscriptions** | 42           | Subscriptions currently in active status                   |
| **Total Users**          | 156          | Number of employees in the organization                    |
| **Monthly Spend**        | $42,350      | Sum of all monthly subscription costs                      |
| **Annual Spend**         | $508,200     | Monthly spend × 12                                         |
| **Potential Savings**    | $8,475/month | 20% of monthly spend (identified by AI)                    |
| **Pending Decisions**    | 12           | Number of optimization recommendations awaiting approval   |
| **Average Utilization**  | 64.5%        | Average of all subscription utilization rates              |

### Quick Wins Breakdown

1. **Reduce Slack licenses** - $1,920/month savings
   - Current: 156 licenses at $8/user
   - Recommendation: 124 licenses (32 inactive users for 60+ days)
   - Confidence: 92%

2. **Cancel unused Figma seats** - $1,440/month savings
   - Current: 30 seats at $12/seat
   - Recommendation: 18 seats (12 with zero activity in 90 days)
   - Confidence: 88%

3. **Switch Zoom to Business plan** - $950/month savings
   - Current: Enterprise plan at $1,900/month
   - Recommendation: Business plan at $950/month
   - Reason: Enterprise features underutilized (12% webinar usage, 35% storage)
   - Confidence: 75%

4. **Consolidate project management** - $1,250/month savings
   - Issue: Teams using both Asana and Monday.com
   - Recommendation: Merge to single platform
   - Confidence: 68%

### Utilization Summary

| Category          | Count | Definition                         |
| ----------------- | ----- | ---------------------------------- |
| **Healthy**       | 18    | 60%+ utilization (good value)      |
| **Moderate**      | 15    | 40-60% utilization (acceptable)    |
| **Underutilized** | 11    | 20-40% utilization (needs review)  |
| **Critical**      | 3     | <20% utilization (likely wasteful) |

**Total Waste**: $8,475/month ($101,700/year) from underutilized subscriptions

## 💡 Decisions Page (http://localhost:3000/enterprise/decisions)

### Run Analysis Feature

When you click **"Run Analysis"**, the demo simulates:

1. **2-second processing time** (simulating AI analysis)
2. **Analysis of subscription data**:
   - User login patterns (last 90 days)
   - Feature utilization rates
   - License vs active user counts
   - Historical usage trends
   - Department-level insights

3. **Decision Generation** showing:
   - 12 total recommendations
   - Prioritized by savings potential
   - Confidence scores (68-92%)
   - Risk scores (15-25%)
   - Detailed explanations

### Decision Types

- **License Reduction**: Remove inactive/underutilized seats
- **Plan Downgrade**: Switch to lower-tier plans when features aren't used
- **Tool Consolidation**: Merge redundant tools
- **Cancellation**: Eliminate completely unused tools

### How Confidence Scores Work

Confidence scores are calculated based on:

- **Inactive Users Weight** (40%): Users with 60+ days no activity
- **Low Activity Weight** (30%): Users below threshold usage
- **Historical Patterns** (30%): Consistent low usage over time

Example for Slack:

- 32 inactive users (40% weight) = 0.40
- 18 low activity users (30% weight) = 0.30
- Avg 3.2 messages/day (30% weight) = 0.22
- **Total Confidence: 92%**

## 💳 Subscriptions Page (http://localhost:3000/enterprise/subscriptions)

### Demo Subscriptions

| Tool       | Plan         | Cost          | Utilization | Renewal  |
| ---------- | ------------ | ------------- | ----------- | -------- |
| **Slack**  | Business+    | $12,480/month | 79.5%       | 18 days  |
| **GitHub** | Team         | $3,480/month  | 100%        | 12 days  |
| **Zoom**   | Enterprise   | $1,900/month  | 87%         | 120 days |
| **Figma**  | Professional | $360/month    | 60%         | 45 days  |
| **Notion** | Plus         | $1,200/month  | 91%         | 8 days   |

### Utilization Calculation

**Formula**: (Active Seats / Paid Seats) × 100

Example for Slack:

- Paid Seats: 156
- Active Seats: 124 (users who logged in last 30 days)
- Utilization: 124/156 = 79.5%

### Renewal Alerts

- **Urgent** (red): ≤7 days until renewal
- **Soon** (amber): 8-30 days
- **Upcoming** (blue): 31-60 days

## 🔧 Tools Page (http://localhost:3000/enterprise/tools)

Shows all discovered SaaS tools with:

- **Keystone Score**: 1-10 rating of tool importance
- **Dependency Count**: Number of integrations/dependencies
- **Active Users**: Current monthly active users
- **Category**: Communication, Development, Design, Productivity, etc.

### Keystone Tools

High-score tools (8+) that are critical to operations:

- GitHub (9.8) - 22 dependencies
- Slack (9.2) - 15 dependencies
- Notion (8.1) - 5 dependencies

## 👥 Users Page (http://localhost:3000/enterprise/users)

Demo users including:

- **Sarah Johnson** (VP Engineering) - Admin
- **Michael Chen** (Senior Developer) - Active
- **Emily Rodriguez** (Design Lead) - Active
- **David Kim** (Product Manager) - Active
- **Inactive User** (Developer) - 90 days since login

## 🎯 How It All Works

### Data Collection (Personal Mode)

1. User connects Gmail (read-only)
2. AI scans emails for subscription receipts
3. Extracts: vendor, amount, billing date, renewal date
4. Builds personal subscription dashboard

### Enterprise Mode

1. SSO integration for all employees
2. Automated email scanning across organization
3. User activity tracking (anonymized)
4. Cross-reference with IT/Finance systems
5. AI-powered analysis and recommendations

### AI Decision Engine

**Input Data**:

- Login frequency per user/tool
- Feature usage metrics (API calls, file edits, messages, etc.)
- License allocation vs actual users
- Historical trends (3-6 months)
- Industry benchmarks

**Output**:

- Decision type (reduce/downgrade/consolidate/cancel)
- Confidence score (0-100%)
- Risk score (0-100%)
- Savings potential
- Recommended action with explanation
- Supporting factors with weights

### Privacy & Security

- Read-only Gmail access
- No email content stored
- Only metadata extracted (sender, subject, dates, amounts)
- All data encrypted at rest
- SOC 2 compliance ready

## 💰 ROI Example

For Acme Corporation (156 employees):

- **Current Annual Spend**: $508,200
- **Identified Waste**: $101,700/year (20%)
- **Quick Win Savings**: $4,560/month ($54,720/year)
- **Implementation Time**: 2-4 weeks
- **Payback Period**: < 1 month (considering tool cost)

## 🚀 Getting Started (Real Implementation)

1. **Connect Organization**: SSO setup
2. **Initial Scan**: 24-48 hours
3. **First Analysis**: AI generates recommendations
4. **Review & Approve**: IT/Finance review decisions
5. **Execute**: Automated seat reductions, plan changes
6. **Monitor**: Ongoing optimization and alerts

---

## Technical Notes

- All demo data is in `frontend/src/lib/demo-data.ts`
- Set `USE_DEMO_DATA = false` to switch to real backend API
- Backend API ready at `/api/v1/organizations/{org_id}/*`
- Demo mode requires no authentication
- Real mode requires OAuth + organization verification
