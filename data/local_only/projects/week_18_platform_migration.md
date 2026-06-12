# Week 18 — Apex Platform Migration

## Wins
- Win: BU-5 cleared production gate — Jordan's team resolved all 3 failing integration test cases and received final QA sign-off on Wednesday.
- Win: Canary environment cost reduced by 22% after right-sizing replica sets; now within 4% of forecast.
- Win: 5 of 8 Business Units are now live on Apex Platform; ahead of the original Q2 target of 4 BUs.

## Risks
- Risk: BU-6 onboarding is blocked on a missing data classification approval from Legal — the new API gateway surfaces PII fields that were not in scope during the original data inventory; Legal review SLA is 10 business days.
- Risk: vendor auth middleware migration has not been formally staffed; Q3 roadmap is full and there is no owner; EOL risk is now a compliance concern, not just a technical one.
- Risk: Sarah flagged that SRE on-call rotation is stretched — 3 simultaneous BU go-lives in Q2 created alert fatigue; team morale risk if the pace continues into Q3 without a recovery sprint.

## Next Steps
- Next: escalate BU-6 Legal data classification blocker to the platform steering committee; request expedited review given Q2 milestone dependencies.
- Next: identify a vendor auth migration lead from the platform team — present staffing options to engineering directors by end of week.
- Next: schedule a Q3 planning session to scope a recovery sprint for the SRE team; include Sarah in capacity planning discussion.
- Next: draft the Q2 milestone summary for the executive briefing; highlight the 5-of-8 BU achievement and the outstanding risks going into Q3.
