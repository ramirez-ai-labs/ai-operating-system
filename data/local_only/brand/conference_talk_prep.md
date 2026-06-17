# Conference Talk Prep  -  AI-Native Platform Engineering

## Event: Oakland Tech Summit  -  July 2026

### Talk title
"From Keyword Matching to Agentic Retrieval: Building AI-Native Developer Platforms"

### Core thesis
Most enterprise AI integrations are wrappers around a single LLM call. The real unlock is building systems where AI has structured access to your internal knowledge  -  project notes, risk logs, 1:1s  -  and can retrieve, synthesize, and route that information with observable, auditable behavior.

### Key points to land
- Win: the layered model approach (local Ollama for routing, Claude for synthesis) cuts API costs without sacrificing output quality  -  show the token comparison.
- Win: MCP as a composability primitive  -  demo connecting the platform to Claude Desktop in under 5 minutes.
- Win: evaluation frameworks as the trust layer  -  committed eval results are the difference between "we tried AI" and "we ship AI responsibly."

### Demo flow
- Start with a cold `/orchestrate` call against toy data  -  show the trace.
- Switch to the ChromaDB backend with realistic enterprise data  -  show semantic search finding the vendor auth migration risk even when the query says "compliance dependency."
- Trigger `use_mcp=true`  -  show Claude reading files via tool calls in the operator trace.
- Close with the eval results JSON  -  "this is what production AI accountability looks like."

### Risks to prep for
- Risk: live demo fails on stage  -  have a pre-recorded backup of the full trace output.
- Risk: audience is skeptical of toy data  -  the realistic enterprise scenario is the answer; prep talking points on data generation approach.
- Risk: time  -  35-minute slot with 10 minutes Q&A; demo needs to be under 12 minutes.

### Next steps
- Next: finalize slide deck outline by June 20.
- Next: record backup demo video by June 27.
- Next: submit abstract and bio to conference organizers by June 15  -  deadline is firm.
