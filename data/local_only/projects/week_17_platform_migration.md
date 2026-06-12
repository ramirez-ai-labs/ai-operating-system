# Week 17 — Apex Platform Migration

## Wins
- Win: BU-4 security review re-check completed — Priya's team approved the updated data residency mapping; BU-4 is cleared for production gate next week.
- Win: vendor auth middleware migration scoped and estimated at 3 sprints; spike ticket merged, no architectural blockers identified.
- Win: platform team shipped the automated rollback script that was blocking the BU-5 readiness checklist; QA sign-off received.

## Risks
- Risk: BU-5 production gate is at risk — Jordan flagged that the product integration test suite has 3 failing edge cases against the new API schema; ETA for fix is 2 days but no buffer remains in the sprint.
- Risk: infrastructure cost overrun on the Canary environment — cloud spend is 18% above forecast due to over-provisioned replica sets; need ops review before BU-6 onboarding begins.
- Risk: the vendor auth middleware EOL is now confirmed Q4 2026; if migration does not start in Q3 we will carry compliance risk into next fiscal year.

## Next Steps
- Next: daily stand-up check-in with Jordan's team on the 3 failing integration test cases; escalate to weekly steering if not resolved by Wednesday.
- Next: ops review of Canary environment cost — right-size replica sets before BU-6 onboarding ticket is opened.
- Next: add vendor auth migration to the Q3 roadmap; present risk and timeline to steering committee in the Week 18 update.
- Next: prepare the BU-5 production gate checklist for sign-off meeting on Thursday.
