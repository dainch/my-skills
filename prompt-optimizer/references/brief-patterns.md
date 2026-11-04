# Brief Patterns

Use this reference when a task needs a domain-specific prompt pattern.

## Coding Project

Include:

- Repository path and files to inspect first.
- Current behavior and desired behavior.
- Scope boundaries.
- Dependency policy.
- Test or verification commands.
- Final response requirements.

Default success criteria:

- Code is changed only where needed.
- Existing style is preserved.
- Relevant tests or checks have real output.
- The final answer names changed files and verification evidence.

## Beginner Website

Include:

- What the first screen should do.
- Who will maintain it.
- Whether deployment is required.
- Data source and update workflow.
- Mobile and desktop expectations.
- Privacy and public-content boundaries.

Default success criteria:

- The site runs locally.
- The user can edit content without understanding the whole codebase.
- README explains local run, edit workflow, and deployment.
- Public data excludes secrets, private dashboards, local URLs, and risky content.

## Prompt Optimization

Include:

- Original user goal.
- Target agent or model.
- Required output format.
- Execution boundaries.
- Success criteria.
- Verification requirements.

Default success criteria:

- The optimized prompt is directly reusable.
- It replaces open-ended technical gaps with safe defaults.
- It asks at most three choice-based questions when user input is required.
- It includes explicit deliverables and evidence requirements.

## GitHub Sharing

Include:

- Project name.
- License.
- README audience.
- Installation or usage steps.
- Example use cases.
- What must not be committed.

Default success criteria:

- Repository has a clear README.
- Project structure is obvious from the root.
- License is present.
- Sensitive files are ignored.
- Public publishing requires explicit confirmation before push.
