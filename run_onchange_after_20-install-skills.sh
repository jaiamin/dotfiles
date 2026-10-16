#!/bin/bash
# Re-runs whenever this file changes. Edit the list here to add or remove skills.
eval "$(/opt/homebrew/bin/brew shellenv)"
A="-g -a claude-code -a codex -a opencode -y"
npx skills add mattpocock/skills $A --skill grill-me --skill grilling --skill grill-with-docs \
  --skill improve-codebase-architecture --skill tdd
npx skills add anthropics/skills $A --skill frontend-design
npx skills add vercel-labs/skills $A --skill find-skills
npx skills add vercel-labs/agent-browser $A
