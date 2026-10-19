#!/bin/bash
# Global agent skills.
set -euo pipefail

A=(-g -a claude-code -a codex -a opencode -y)
add() { npx --yes skills@latest add "$@" "${A[@]}"; }

# Workflow: align, plan, build, review, debug
add mattpocock/skills \
  --skill setup-matt-pocock-skills \
  --skill grill-me --skill grill-with-docs --skill grilling \
  --skill to-spec --skill to-tickets --skill implement --skill implement-spec \
  --skill tdd --skill code-review --skill diagnosing-bugs \
  --skill codebase-design --skill improve-codebase-architecture \
  --skill prototype --skill handoff --skill retro --skill teach

# Frontend: React, components, UI design
add vercel-labs/agent-skills \
  --skill vercel-react-best-practices --skill vercel-composition-patterns \
  --skill web-design-guidelines
add shadcn-ui/ui --skill shadcn
add pbakaus/impeccable --skill impeccable

# Browser testing
add vercel-labs/agent-browser

# Current library docs
add upstash/context7 --skill find-docs

