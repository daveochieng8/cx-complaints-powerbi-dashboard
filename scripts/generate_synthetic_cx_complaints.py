import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

random.seed(7)
np.random.seed(7)

N = 12000
start_date = datetime(2025, 7, 1)
end_date = datetime(2026, 2, 23)
days_range = (end_date - start_date).days

channels = ["Call Centre", "WhatsApp", "Email", "Live Chat", "Branch", "App", "Facebook", "X"]
segments = ["Retail", "SME", "Corporate"]
regions = ["Nairobi", "Central", "Coast", "Rift Valley", "Western", "Nyanza", "Eastern", "North Eastern"]

products = ["Cards", "Mobile Banking", "Internet Banking", "Accounts", "Loans", "Payments", "ATM", "Agent Banking"]
issues_by_product = {
    "Cards": ["Declined transaction", "Chargeback dispute", "Card blocked", "Fraud alert", "PIN reset"],
    "Mobile Banking": ["Login failure", "App crash", "OTP not received", "Transfer failed", "Bill payment failed"],
    "Internet Banking": ["Login failure", "Token/OTP issues", "Beneficiary issues", "Transfer failed", "Session timeout"],
    "Accounts": ["Charges dispute", "Statement request", "Account blocked", "KYC update", "Balance discrepancy"],
    "Loans": ["Loan balance query", "Repayment not reflecting", "Reschedule request", "Interest dispute", "Top-up query"],
    "Payments": ["P2P failed", "Merchant payment failed", "Reversal delay", "Duplicate debit", "Settlement delay"],
    "ATM": ["Cash not dispensed", "Partial dispense", "Card retained", "Reversal delay", "ATM downtime"],
    "Agent Banking": ["Float issues", "Cash-out failed", "Reversal delay", "Wrong posting", "Service unavailable"]
}

severity_levels = ["Low", "Medium", "High"]
severity_weights = [0.55, 0.33, 0.12]

status_levels = ["Closed", "Open", "Escalated"]
status_weights = [0.78, 0.14, 0.08]

resolution_levels = ["Resolved", "Partially Resolved", "Unresolved"]
resolution_weights = [0.86, 0.09, 0.05]

def random_date():
    d = start_date + timedelta(days=int(np.random.randint(0, days_range + 1)))

    hours = np.array([8,9,10,11,12,13,14,15,16,17,18,19])
    probs = np.array([.06,.07,.08,.09,.09,.09,.09,.09,.08,.08,.07,.06], dtype=float)
    probs = probs / probs.sum()  # normalize to sum to 1

    hour = int(np.random.choice(hours, p=probs))
    minute = int(np.random.randint(0, 60))
    return d.replace(hour=hour, minute=minute, second=0)

def sla_target(product, severity):
    base = {
        "Cards": 24, "Mobile Banking": 24, "Internet Banking": 24,
        "Accounts": 48, "Loans": 72, "Payments": 48, "ATM": 48, "Agent Banking": 48
    }[product]
    if severity == "High":
        return max(12, base - 12)
    if severity == "Low":
        return base + 24
    return base

def ttr_hours(product, issue, channel, severity):
    # typical resolution time patterns
    base = {
        "Declined transaction": 10, "Chargeback dispute": 72, "Fraud alert": 18, "Card blocked": 8, "PIN reset": 3,
        "Login failure": 6, "App crash": 18, "OTP not received": 4, "Transfer failed": 14, "Bill payment failed": 16,
        "Token/OTP issues": 6, "Beneficiary issues": 20, "Session timeout": 5,
        "Charges dispute": 60, "Statement request": 12, "Account blocked": 36, "KYC update": 72, "Balance discrepancy": 48,
        "Loan balance query": 20, "Repayment not reflecting": 40, "Reschedule request": 72, "Interest dispute": 96, "Top-up query": 18,
        "P2P failed": 18, "Merchant payment failed": 18, "Reversal delay": 36, "Duplicate debit": 60, "Settlement delay": 72,
        "Cash not dispensed": 48, "Partial dispense": 60, "Card retained": 36, "ATM downtime": 12,
        "Float issues": 24, "Cash-out failed": 18, "Wrong posting": 48, "Service unavailable": 12
    }.get(issue, 24)

    # channel effect
    if channel in ["App", "Live Chat", "WhatsApp"]:
        base *= 0.9
    if channel == "Branch":
        base *= 1.1

    # severity effect
    if severity == "High":
        base *= 0.85
    elif severity == "Low":
        base *= 1.2

    # randomness + skew
    noise = np.random.lognormal(mean=0.0, sigma=0.45)
    return max(1, int(round(base * noise)))

def frt_minutes(channel):
    base = {"Call Centre": 6, "Live Chat": 4, "WhatsApp": 10, "Email": 60, "Branch": 15, "App": 3, "Facebook": 18, "X": 14}
    noise = np.random.lognormal(mean=0.0, sigma=0.55)
    return int(max(1, round(base[channel] * noise)))

def csat_score(status, resolution, ttr, sla):
    # score 1–5, worse if SLA breached or unresolved
    score = 4.3
    if status != "Closed":
        score -= 0.5
    if resolution == "Unresolved":
        score -= 1.4
    elif resolution == "Partially Resolved":
        score -= 0.7
    if ttr > sla:
        score -= 0.8
    score += np.random.normal(0, 0.35)
    return int(min(5, max(1, round(score))))

rows = []
for i in range(N):
    opened = random_date()
    product = random.choice(products)
    issue = random.choice(issues_by_product[product])
    channel = random.choice(channels)
    segment = random.choice(segments)
    region = random.choice(regions)
    severity = np.random.choice(severity_levels, p=severity_weights)
    status = np.random.choice(status_levels, p=status_weights)

    sla = sla_target(product, severity)
    ttr = ttr_hours(product, issue, channel, severity)

    # if open/escalated, some have no close date
    if status == "Closed":
        closed = opened + timedelta(hours=ttr)
        resolution = np.random.choice(resolution_levels, p=resolution_weights)
    else:
        # 60% of open/escalated have no close date yet
        if random.random() < 0.6:
            closed = pd.NaT
        else:
            closed = opened + timedelta(hours=int(ttr * 0.8))
        resolution = "Unresolved" if status == "Escalated" else np.random.choice(["Unresolved","Partially Resolved"], p=[0.7,0.3])

    frt = frt_minutes(channel)
    csat = csat_score(status, resolution, ttr, sla)
    handle_time = int(max(2, round(np.random.lognormal(mean=3.0, sigma=0.35))))  # minutes
    complaint_id = f"CX{opened.strftime('%y%m')}{i:05d}"
    customer_id = f"C{np.random.randint(10000, 99999)}"

    rows.append({
        "ComplaintID": complaint_id,
        "CustomerID": customer_id,
        "DateOpened": opened,
        "DateClosed": closed,
        "Channel": channel,
        "Product": product,
        "IssueCategory": issue,
        "Severity": severity,
        "Status": status,
        "Resolution": resolution,
        "SLA_Target_Hours": sla,
        "FRT_Minutes": frt,
        "HandleTime_Minutes": handle_time,
        "CustomerSegment": segment,
        "Region": region
    })

df = pd.DataFrame(rows)

spike_days = [datetime(2025, 10, 10), datetime(2025, 12, 20), datetime(2026, 1, 15)]

for d in spike_days:
    idx = df.sample(200, random_state=int(d.strftime("%d"))).index

    # keep original opened so we can compute a shift
    old_opened = df.loc[idx, "DateOpened"]

    # set opened to the spike day (keep original time)
    new_opened = old_opened.apply(lambda x: x.replace(year=d.year, month=d.month, day=d.day))
    df.loc[idx, "DateOpened"] = new_opened

    # shift DateClosed by the same delta (only where DateClosed exists)
    delta = new_opened - old_opened
    has_closed = df.loc[idx, "DateClosed"].notna()
    df.loc[idx[has_closed], "DateClosed"] = df.loc[idx[has_closed], "DateClosed"] + delta[has_closed]

df = df.sort_values("DateOpened").reset_index(drop=True)
out = "CX_Complaints_Synthetic_KenyaStyle.csv"
df.to_csv(out, index=False)
print("Saved:", out, "Rows:", len(df))