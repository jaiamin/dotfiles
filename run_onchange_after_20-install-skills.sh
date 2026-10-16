#!/bin/bash
# Re-runs whenever this file changes. Edit the list here to add or remove skills.
eval "$(/opt/homebrew/bin/brew shellenv)"
A="-g -a claude-code -a codex -a opencode -y"
npx skills add mattpocock/skills $A --skill grill-me --skill grilling \
  --skill to-spec --skill to-tickets --skill implement --skill implement-spec \
  --skill setup-matt-pocock-skills --skill tdd --skill code-review \
  --skill diagnosing-bugs --skill prototype --skill handoff --skill codebase-design \
  --skill improve-codebase-architecture --skill teach --skill retro
npx skills add anthropics/skills $A --skill frontend-design
npx skills add vercel-labs/agent-browser $A
