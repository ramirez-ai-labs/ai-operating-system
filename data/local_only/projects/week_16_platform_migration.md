# Week 16  -  Apex Platform Migration

## Wins
- Win: completed Canary environment cutover for Business Units 1 and 2  -  both passed production readiness gates with zero P1 incidents in the first 72 hours.
- Win: unblocked the BU-3 onboarding after resolving the SAML federation issue with the identity provider; security team signed off same day.
- Win: merged the shared infrastructure module that reduces per-BU setup time from 3 days to 4 hours.

## Risks
- Risk: BU-4 security review is stalled  -  Priya's team flagged a data residency ambiguity in the new API gateway config; estimated 1-week delay to production gate.
- Risk: vendor API deprecation notice received for the legacy auth middleware  -  EOL is Q4 2026, earlier than the original Q1 2027 estimate; migration path not yet scoped.
- Risk: two senior engineers (Tariq and Dani) are on PTO next sprint, reducing platform team capacity by 40%; BU-5 readiness review may slip.

## Next Steps
- Next: schedule BU-4 security review re-check with Priya for Tuesday; prepare data residency mapping doc in advance.
- Next: open a scoping ticket for the vendor auth middleware migration; assign to Marcus's team for initial spike.
- Next: confirm BU-5 readiness review timeline with Jordan; adjust sprint capacity plan if Tariq and Dani overlap extends.
- Next: publish the Week 16 leadership summary to the platform steering committee by Friday.
