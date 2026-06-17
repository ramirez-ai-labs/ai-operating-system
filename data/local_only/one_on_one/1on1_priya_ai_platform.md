# 1:1 Notes  -  Priya Nair, AI Platform Engineer
**Date:** Week of June 9, 2026
**Attendees:** Victor (Manager), Priya (AI Platform Engineer)

## Status

Priya is leading the LLM evaluation framework build and is also the primary point of contact for the LangSmith integration. Both are on track but she is being pulled into ad-hoc demos for the sales team.

Talking Point: The ad-hoc demo requests from sales are consuming 20-30% of Priya's week  -  we need a policy.
Talking Point: LLM evaluation framework: discuss coverage goals and whether we target recall@5 or MRR as the primary metric for Q3.
Talking Point: Priya raised the idea of publishing the eval framework as open source  -  discuss timing and IP clearance process.

## Actions from Last Week

Action: Priya to complete the Recall@5 baseline for the Director OS retrieval pipeline by June 18.
Action: Priya to document the LangSmith dataset schema so other teams can contribute eval cases.
Action: Victor to block Priya's calendar Tuesday/Thursday mornings as no-meeting focus time.

## Blockers

Blocker: The LangSmith API key provisioning for the staging environment is pending IT  -  opened 8 days ago.
Blocker: Priya cannot finalize the retrieval metric baseline without access to the production query logs, which require a data governance approval.

## Recognition

Kudos: Priya's prompt caching implementation on the Claude provider reduced per-request cost by 40% in load testing.
Kudos: Priya presented the AI OS architecture to the CISO team and unblocked the data residency approval.
