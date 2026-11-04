---
name: prompt-optimizer
description: Turn vague user goals into executable agent briefs. Use when the user knows the desired outcome but is unsure how to specify programming requirements, constraints, deliverables, verification, deployment, or agent instructions; also use to optimize prompts for Codex, Claude, Cursor, ChatGPT, or other coding agents before implementation.
---

# Prompt Optimizer

## Purpose

Convert an under-specified goal into a brief that another agent can execute with clear scope, success criteria, constraints, deliverables, and verification requirements.

Use this skill to write the prompt or task brief. Do not implement the target project unless the user explicitly asks you to continue into implementation.

## Workflow

1. Identify the user's real outcome.
2. Infer a conservative default execution path.
3. Fill missing engineering requirements that a beginner may not know to ask for.
4. Turn risky ambiguity into 2-3 concrete choices when needed.
5. Produce a ready-to-use agent prompt.
6. Self-check that the prompt can be executed and verified.

## Intake

Extract these fields from the user's request and local context when available:

- Goal: the desired final outcome in plain language.
- User level: beginner, technical, or expert.
- Inputs: files, URLs, screenshots, notes, repositories, examples, or source material.
- Target agent: Codex, Claude, Cursor, ChatGPT, generic agent, or unknown.
- Environment: local app, repo path, OS, framework, deployment target, or unknown.
- Constraints: scope, style, dependencies, privacy, budget, time, and safety boundaries.
- Deliverables: code, data, docs, tests, deployment steps, prompt, report, or design.
- Verification: commands, screenshots, manual checks, acceptance criteria, or evidence.

When fields are missing, choose a safe default instead of asking unless the missing answer changes the task materially.

## Default Assumptions

Use these defaults for beginner users:

- Prefer the simplest maintainable implementation.
- Prefer existing project patterns over adding new frameworks.
- Prefer static or low-dependency solutions for small websites and utilities.
- Require clear deliverables and verification evidence.
- Require a short README when the result is meant to be reused or shared.
- Require deployment notes when the user says publish, share, website, or GitHub.
- Protect private data by default: exclude secrets, local-only URLs, account pages, API keys, tokens, and personal dashboards.
- Ask before public publishing, destructive changes, paid services, or broad refactors.

## Output Shape

Return the optimized prompt in Chinese unless the user asks otherwise.

Use this structure:

```markdown
# Agent Task Brief

## Background
[Explain the user's situation and available inputs.]

## Goal
[State the final outcome in concrete terms.]

## Inputs
[List files, URLs, screenshots, examples, and what to read first.]

## Execution Requirements
[Describe the required workflow and implementation constraints.]

## Success Criteria
[List observable acceptance criteria.]

## Deliverables
[List exact files, docs, commands, or artifacts expected.]

## Verification
[Require real command output, screenshots, tests, or manual checks.]

## Prohibited Actions
[List scope boundaries and unsafe actions.]

## When Choices Are Needed
[Give default choices and ask only with 2-3 options.]
```

After the prompt, add a short note with:

- Recommended default plan.
- Open choices, only if truly needed.
- Main risks or boundaries.

## Choice Questions

When asking the user to decide, use no more than three choices. Each choice must include the tradeoff and a recommended default.

Use this format:

```markdown
One choice needs confirmation:

1. Option A (recommended): ...
2. Option B: ...
3. Option C: ...
```

Do not ask open-ended questions such as "What framework do you want?" for beginner users. Replace them with defaults and tradeoffs.

## Self-Check

Before finalizing the optimized prompt, verify that it answers these questions:

- Can another agent start without asking obvious follow-up questions?
- Does it define what "done" means?
- Does it name the input files or source material?
- Does it prevent uncontrolled scope expansion?
- Does it include verification based on real tools or observable evidence?
- Does it handle beginner maintenance and deployment needs?
- Does it protect secrets, private links, and risky public content where relevant?

If any answer is no, revise the prompt before returning it.

## Optional Reference

For reusable patterns and examples, read `references/brief-patterns.md`.
