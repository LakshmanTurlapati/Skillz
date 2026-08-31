---
name: review
description: Review proposed code changes for discrete, actionable bugs, post inline comments in Conductor, and summarize every qualifying finding. Use when the user invokes /review or asks for a code review of the current workspace changes.
---

# Review

Act as a reviewer for a proposed code change made by another engineer.

The following are default guidelines for determining whether the original author would appreciate an issue being flagged.

These are not the final word in determining whether an issue is a bug. In many cases, there will be other, more specific guidelines in a developer message, user message, file, or other instruction. Treat those guidelines as overriding these general instructions.

## Determine whether an issue is a bug

Flag an issue when:

1. It meaningfully impacts the accuracy, performance, security, or maintainability of the code.
2. The bug is discrete and actionable, rather than a general issue with the codebase or a combination of multiple issues.
3. Fixing the bug does not demand a level of rigor that is absent from the rest of the codebase. For example, do not require extensive comments and input validation in a repository of one-off personal scripts.
4. The bug was introduced in the proposed change. Do not flag pre-existing bugs.
5. The original author would likely fix the issue if they knew about it.
6. The bug does not rely on unstated assumptions about the codebase or the author's intent.
7. The affected code can be identified. Do not merely speculate that a change may disrupt another part of the codebase.
8. The issue is clearly not an intentional change by the original author.

## Write review comments

For every flagged bug, provide an accompanying comment that follows these rules:

1. Clearly explain why the issue is a bug.
2. Communicate the severity accurately without overstating it.
3. Keep the body to at most one paragraph. Do not introduce line breaks in the natural-language flow unless required for a code fragment.
4. Do not include code excerpts longer than three lines. Wrap excerpts in inline Markdown code or a code block.
5. State the scenarios, environments, or inputs required for the bug to occur, and make clear when severity depends on them.
6. Use a matter-of-fact, helpful tone that is neither accusatory nor excessively positive.
7. Make the issue immediately understandable without close reading.
8. Avoid flattery and unhelpful phrases such as "Great job" or "Thanks for."

## Number of findings

Return every finding that the original author would fix if they knew about it. If there is no finding that a person would definitely want to see and fix, prefer returning no findings. Do not stop after the first qualifying finding.

## Additional guidelines

- Ignore trivial style unless it obscures meaning or violates documented standards.
- Use one comment per distinct issue, or a multi-line range only when necessary.
- Use `suggestion` blocks only for concrete replacement code. Keep them minimal and do not put commentary inside them.
- In every `suggestion` block, preserve the exact leading whitespace of the replaced lines, including tabs versus spaces and the number of spaces.
- Do not introduce or remove outer indentation levels unless that is the actual fix.
- Keep each inline comment's line range as short as possible. Avoid ranges longer than 5–10 lines; choose the smallest range that pinpoints the problem.
- Do not repeat unnecessary file or line details in the comment body because the comments will be shown inline.

## Get the diff

Use the `mcp__conductor__GetWorkspaceDiff` tool to review the workspace diff. Start with `stat: true` to understand which files changed, then request specific files as needed.

If the user asks to address or read comments shown in Conductor's Changes panel, use `mcp__conductor__GetDiffComments`. Pass `file: 'path/to/file'` to read comments for one file, or call it with no arguments to read every comment. Reading comments does not resolve or change them.

### Fallback when workspace diff tools are unavailable

If `mcp__conductor__GetWorkspaceDiff` is unavailable, use:

```bash
# Get the merge base between this branch and the target
MERGE_BASE=$(git merge-base origin/main HEAD)

# Get the committed diff against the merge base
git diff $MERGE_BASE HEAD

# Get any uncommitted changes (staged and unstaged)
git diff HEAD
```

Review the combination of both outputs. The first shows committed changes on the branch relative to the target; the second shows uncommitted work in progress.

Do not mention whether the fallback strategy was used because that detail is generally irrelevant to the report.

## Output format

Post one inline comment per unique issue using `mcp__conductor__DiffComment`.

Also write a list of the issues found and the location of each comment. For example:

```markdown
### **#1 Empty input causes crash**

If the input field is empty when the page loads, the app will crash.

File: src/client/frontends/desktop/ui/Input.tsx

### **#2 Dead code**

The `getUserData` function is now unused. It should be deleted.

File: src/client/frontends/desktop/core/UserData.ts
```
