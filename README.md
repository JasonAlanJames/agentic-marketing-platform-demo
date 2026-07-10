# Capital Group Agentic Marketing Demo

A portfolio project demonstrating a production-style agentic AI workflow for financial marketing content generation.

## Features

- LangGraph stateful orchestration
- Amazon Bedrock with Amazon Nova Lite
- Financial marketing writer agent
- Compliance reviewer agent
- Conditional revision loop
- Structured Pydantic outputs
- Langfuse observability and tracing
- Environment-based credential management

## Workflow

```text
Source Document
    ↓
Writer Agent
    ↓
Compliance Reviewer
    ↓
Approved?
├── Yes → Finalize
└── No  → Revision Loop → Writer