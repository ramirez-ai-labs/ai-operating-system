# Apex Platform — Risk Register

## Active Risks

### RISK-01 — Vendor Auth Middleware EOL
- Severity: P1
- Owner: Platform Team (lead TBD)
- Status: Scoped, not staffed
- Detail: Legacy authentication middleware vendor confirmed EOL as Q4 2026. Migration to the new identity platform is estimated at 3 sprints. No owner assigned yet. If migration does not begin in Q3, the platform carries compliance risk into next fiscal year.
- Next: identify migration lead; present staffing options to engineering directors by end of Week 18.

### RISK-02 — BU-6 Legal Data Classification Blocker
- Severity: P1
- Owner: Legal / Platform Team
- Status: Blocked — awaiting Legal review
- Detail: BU-6 onboarding surfaced PII fields in the new API gateway that were not in the original data inventory. Legal review SLA is 10 business days. Escalated to platform steering committee in Week 18.
- Next: steering committee to track weekly until resolved; expedited review requested.

### RISK-03 — SRE On-Call Alert Fatigue
- Severity: P2
- Owner: Sarah Chen
- Status: Mitigating — alerting thresholds recalibration in progress
- Detail: 5 simultaneous BU go-lives created alert noise that tripled false positive rate. SRE team is manually suppressing alerts each shift. Sarah is recalibrating thresholds; recovery sprint requested for Q3.
- Next: confirm recovery sprint in Q3 capacity plan; include in engineering director briefing.

### RISK-04 — BU-5 Integration Test Failures (Resolved Week 17)
- Severity: P2
- Owner: Jordan Lee
- Status: Resolved
- Detail: 3 failing edge cases in the product integration test suite against the new API schema. Resolved by Jordan's team; production gate cleared Week 17.

### RISK-05 — Canary Environment Cost Overrun (Resolved Week 17)
- Severity: P3
- Owner: Ops / Platform Team
- Status: Resolved
- Detail: Cloud spend was 18% above forecast due to over-provisioned replica sets. Right-sized in Week 17; now within 4% of forecast.

## Resolved This Quarter
- RISK-04 resolved Week 17
- RISK-05 resolved Week 17
