#!/bin/bash
# Re-runs whenever this file changes. Edit the list here to add or remove skills.
eval "$(/opt/homebrew/bin/brew shellenv)"
A="-g -a claude-code -a codex -a opencode -y"
npx skills add mattpocock/skills $A --skill grill-me --skill grilling \
  --skill improve-codebase-architecture --skill tdd --skill diagnosing-bugs \
  --skill code-review --skill handoff --skill prototype --skill codebase-design
npx skills add anthropics/skills $A --skill frontend-design --skill skill-creator
npx skills add vercel-labs/skills $A --skill find-skills
npx skills add vercel-labs/agent-browser $A
