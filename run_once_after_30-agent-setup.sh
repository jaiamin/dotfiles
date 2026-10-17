#!/bin/bash
eval "$(/opt/homebrew/bin/brew shellenv)"
claude mcp add --scope user --transport http context7 https://mcp.context7.com/mcp || true
agent-browser install || true
