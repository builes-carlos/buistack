#!/usr/bin/env bash
# Idempotent installer for devaing's skills.
#
# Extended to close the gap against harnessing/install-contract.md, in place
# (bash, same mechanism, same file), not rewritten into another language --
# see that document and the change that added it for why a rewrite was not
# taken here.
#
# Usage:
#   ./install.sh            copy skills, report what changed, changed or not
#   ./install.sh --check    report only, write nothing, exit 1 if incomplete
set -euo pipefail

SKILLS_DIR="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

CHECK=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

# No ~/.claude at all: nothing to install onto, and not an error -- the same
# "skipped" verdict harnessing/install.py gives for the same situation.
if [ ! -d "$HOME/.claude" ]; then
  echo "  [skipped ] skills: no ~/.claude on this machine"
  exit 0
fi

# nullglob so a repo moved or a skills/ directory missing reports as "no
# skills found" rather than iterating over the literal, unexpanded glob
# string and trying to install a skill named "devaing-*".
shopt -s nullglob
skill_dirs=("$REPO_DIR"/skills/devaing-*/)

if [ ${#skill_dirs[@]} -eq 0 ]; then
  echo "  [missing ] skills: no devaing-* directories found under $REPO_DIR/skills -- wrong location?"
  exit 1
fi

# One of: absent | current | stale | obstructed -- the four states
# install-contract.md declares generic to any install mechanism. devaing
# copies rather than links, so the two link-specific states (linked,
# dangling) never apply here.
skill_state() {
  local src="$1" dest="$2" f base
  if [ -e "$dest" ] && [ ! -d "$dest" ]; then
    echo "obstructed"; return
  fi
  if [ ! -d "$dest" ]; then
    echo "absent"; return
  fi
  for f in "$src"*.md; do
    base="$(basename "$f")"
    if [ ! -f "$dest/$base" ] || ! cmp -s "$f" "$dest/$base"; then
      echo "stale"; return
    fi
  done
  echo "current"
}

incomplete=0

for skill in "${skill_dirs[@]}"; do
  name="$(basename "$skill")"
  dest="$SKILLS_DIR/$name"
  state="$(skill_state "$skill" "$dest")"

  case "$state" in
    current)
      echo "  [ok      ] $name: already up to date at $dest"
      ;;
    obstructed)
      echo "  [missing ] $name: $dest exists and is not a directory this installer owns -- not touching it"
      incomplete=1
      ;;
    absent|stale)
      if [ "$CHECK" -eq 1 ]; then
        if [ "$state" = "absent" ]; then
          echo "  [missing ] $name: would copy to $dest"
        else
          echo "  [missing ] $name: copied and stale at $dest; would update"
        fi
        incomplete=1
      else
        mkdir -p "$dest"
        for f in "$skill"*.md; do
          cp "$f" "$dest/"
        done
        if [ "$state" = "absent" ]; then
          echo "  [written ] $name: copied to $dest"
        else
          echo "  [updated ] $name: copied to $dest"
        fi
      fi
      ;;
  esac
done

if [ "$CHECK" -eq 1 ]; then
  echo ""
  if [ "$incomplete" -eq 1 ]; then
    echo "--check: some skills are not installed or are out of date."
    exit 1
  fi
  echo "--check: install is complete."
  exit 0
fi

if [ "$incomplete" -eq 1 ]; then
  exit 1
fi

echo ""
echo "Done. Restart Claude Code to pick up any new or updated skills."
echo ""
echo "Then run /devaing-init to start your first project."
