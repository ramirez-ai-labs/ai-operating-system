# 1:1 Notes — Sarah Chen, SRE Lead

## June 9 — Week 17

### Decisions
- Decision: adopt Terraform 1.9 for all new Apex Platform infrastructure modules; Sarah will update the runbook and deprecate the Terraform 1.6 templates by end of sprint.
- Decision: add a 2-hour on-call buffer to the SRE rotation schedule during BU go-live weeks to reduce alert fatigue; effective starting Week 18.

### Risks raised by Sarah
- Risk: the current alerting thresholds on the API gateway were tuned for 2 BUs; with 5 BUs live, false positive rate has tripled — team is manually suppressing alerts every shift.
- Risk: SRE team has not had a full sprint without a go-live since Week 12; burnout risk is real; Sarah recommends a recovery sprint in Q3 before BU-7 onboarding begins.

### Action items
- Next: Sarah to publish updated Terraform 1.9 runbook by June 20.
- Next: Sarah to recalibrate API gateway alerting thresholds for 5-BU load by end of week.
- Next: I will raise the recovery sprint ask in the Q3 planning discussion with engineering directors.

## May 26 — Week 15

### Decisions
- Decision: SRE team will own the automated rollback script for all BU go-lives going forward; removes dependency on the platform team for incident response.

### Risks raised by Sarah
- Risk: the BU-3 SAML federation issue exposed a gap in the pre-go-live checklist — identity provider config is not validated before the production gate; two other BUs may have the same gap.

### Action items
- Next: Sarah to add identity provider validation step to the production readiness checklist template.
- Next: retroactively validate BU-1 and BU-2 identity provider configs; close any open gaps before BU-4 onboarding.
