#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()  { echo -e "${CYAN}ℹ${RESET}  $*"; }
ok()    { echo -e "${GREEN}✓${RESET}  $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET}  $*"; }
err()   { echo -e "${RED}✗${RESET}  $*" >&2; }

failures=0
warnings=0

record_failure() {
  err "$*"
  failures=$((failures + 1))
}

record_warning() {
  warn "$*"
  warnings=$((warnings + 1))
}

if ! command -v python3 >/dev/null 2>&1; then
  record_failure "python3 is required for validation"
  exit 1
fi

info "Validating packaged agent surfaces from $ROOT_DIR"

if python3 -m json.tool .claude-plugin/plugin.json >/dev/null 2>&1; then
  ok ".claude-plugin/plugin.json is valid JSON"
else
  record_failure ".claude-plugin/plugin.json is not valid JSON"
fi

if python3 -m json.tool marketplace-entry.json >/dev/null 2>&1; then
  ok "marketplace-entry.json is valid JSON"
else
  record_failure "marketplace-entry.json is not valid JSON"
fi

manifest_tmp="$(mktemp)"
python3 - <<'PY' > "$manifest_tmp"
import json
with open('.claude-plugin/plugin.json') as f:
    data = json.load(f)
for skill in data.get('skills', []):
    print(f"{skill['name']}\t{skill['path']}")
PY

manifest_count=$(wc -l < "$manifest_tmp" | tr -d ' ')

# The manifest declares the CORE surface only. Activating a front copies its
# staged skills into .claude/skills/, so a raw count there is inflated by however
# many fronts are active right now. Subtract them, or this check fires in normal
# use every time someone activates a front.
core_skill_count=$(python3 - <<'PY'
import glob, json, os, re

def frontmatter_list(path, key):
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            text = f.read().replace("\r\n", "\n")
    except OSError:
        return []
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return []
    for line in m.group(1).split("\n"):
        km = re.match(r"^%s:\s*\[(.*)\]\s*$" % re.escape(key), line)
        if km:
            inner = km.group(1).strip()
            return [x.strip() for x in inner.split(",")] if inner else []
    return []

try:
    with open("fronts/.activated.json", encoding="utf-8-sig") as f:
        state = json.load(f)
    active = state if isinstance(state, dict) else {}
except (OSError, ValueError):
    active = {}

from_fronts = set()
for front_id in active:
    pack = f"fronts/{front_id}.md"
    if os.path.isfile(pack):
        from_fronts.update(frontmatter_list(pack, "skills"))

shipped = {os.path.basename(os.path.dirname(p)) for p in glob.glob(".claude/skills/*/SKILL.md")}
print(len(shipped - from_fronts))
PY
)

if [[ "$manifest_count" == "$core_skill_count" ]]; then
  ok "Plugin manifest skill count matches shipped core skills ($manifest_count)"
else
  record_failure "Plugin manifest declares $manifest_count skills but .claude/skills contains $core_skill_count core SKILL.md files (front-owned skills excluded)"
fi

while IFS=$'\t' read -r name path; do
  [[ -z "$name" ]] && continue
  # Python on Windows writes CRLF to stdout; strip the CR or every -f test fails.
  path="${path%$'\r'}"

  if [[ -f "$path" ]]; then
    ok "Manifest path exists for $name → $path"
  else
    record_failure "Manifest path missing for $name → $path"
  fi

  if grep -Fq "### /$name" AGENTS.md; then
    ok "AGENTS.md documents /$name"
  else
    record_failure "AGENTS.md is missing /$name"
  fi
done < "$manifest_tmp"

rm -f "$manifest_tmp"

plugin_version=$(python3 - <<'PY'
import json
with open('.claude-plugin/plugin.json') as f:
    print(json.load(f)['version'])
PY
)
marketplace_version=$(python3 - <<'PY'
import json
with open('marketplace-entry.json') as f:
    print(json.load(f)['version'])
PY
)
cog_version=$(tr -d '[:space:]' < BRAINIA-VERSION)

if [[ "$plugin_version" == "$marketplace_version" && "$plugin_version" == "$cog_version" ]]; then
  ok "Version is aligned across plugin.json, marketplace-entry.json, and BRAINIA-VERSION ($cog_version)"
else
  record_failure "Version mismatch: plugin.json=$plugin_version marketplace-entry.json=$marketplace_version BRAINIA-VERSION=$cog_version"
fi

# .github/MARKETPLACE.md is gitignored, so listing it here made rg fail on a fresh
# clone and the check pass silently. Only tracked docs belong in this list.
if rg -n "agents\.md" README.md SETUP.md CONTRIBUTING.md >/dev/null 2>&1; then
  record_failure "Found lowercase 'agents.md' references in packaging docs; use AGENTS.md consistently"
else
  ok "Packaging docs consistently use AGENTS.md casing"
fi

kiro_count=$(find .kiro/powers -name POWER.md | wc -l | tr -d ' ')
gemini_commands_count=$(find .gemini/commands -type f | wc -l | tr -d ' ')
gemini_skills_count=$(find .gemini/skills -type f | wc -l | tr -d ' ')

if [[ "$kiro_count" == "7" ]]; then
  ok "Kiro core surface count is $kiro_count"
else
  record_warning "Expected 7 Kiro powers, found $kiro_count"
fi

if [[ "$gemini_commands_count" == "7" && "$gemini_skills_count" == "7" ]]; then
  ok "Gemini core surface counts are aligned (commands=$gemini_commands_count, skills=$gemini_skills_count)"
else
  record_warning "Expected 7 Gemini commands and 7 Gemini skills, found commands=$gemini_commands_count skills=$gemini_skills_count"
fi

if [[ -f docs/AGENT-SUPPORT.md ]]; then
  ok "docs/AGENT-SUPPORT.md exists"
else
  record_failure "docs/AGENT-SUPPORT.md is missing"
fi

echo
info "Validating fronts layer"

if [[ -f fronts/_template.md ]]; then
  ok "fronts/_template.md exists"
else
  record_failure "fronts/_template.md is missing"
fi

if [[ -f fronts/_profile-template.md ]]; then
  ok "fronts/_profile-template.md exists"
else
  record_failure "fronts/_profile-template.md is missing"
fi

if [[ -d .claude/roles ]]; then
  record_failure ".claude/roles exists; the job-title axis was removed and must not come back"
else
  ok ".claude/roles does not exist"
fi

# Front packs (fronts/*.md, excluding _-prefixed templates), core skills, and the
# nurse-test lint all need real parsing, not grep. Do it once in Python and emit
# tagged, tab-separated result lines for the bash loop below to react to.
fronts_tmp="$(mktemp)"
python3 - <<'PY' > "$fronts_tmp"
import glob
import json
import os
import re

REQUIRED_FRONT_KEYS = [
    "front_id", "display_name", "aliases", "sibling",
    "writes_to", "methodology", "skills", "profiles",
]

RETIRED_ROLE_IDS = [
    "role_pack", "product-manager", "engineering-lead",
    "engineer", "designer", "marketer", "founder",
]


def read_text(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return f.read()


def parse_frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return None, None, "missing opening ---"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, None, "missing closing ---"
    data = {}
    for ln in lines[1:end]:
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            data[key] = [x.strip() for x in inner.split(",")] if inner else []
        else:
            data[key] = val
    body = "\n".join(lines[end + 1:])
    return data, body, None


results = []
packs = {}

front_files = sorted(
    f for f in glob.glob("fronts/*.md")
    if not os.path.basename(f).startswith("_")
)

for f in front_files:
    expected_id = os.path.basename(f)[:-3]
    data, body, err = parse_frontmatter(read_text(f))
    if err:
        results.append(("PACK_PARSE_FAIL", f, err))
        continue
    missing = [k for k in REQUIRED_FRONT_KEYS if k not in data]
    if missing:
        results.append(("PACK_MISSING_KEYS", f, ",".join(missing)))
        continue
    results.append(("PACK_PARSE_OK", f))

    front_id = data["front_id"]
    if front_id == expected_id:
        results.append(("PACK_ID_MATCH", f))
    else:
        results.append(("PACK_ID_MISMATCH", f, front_id, expected_id))

    packs[front_id] = data

    for sk in data["skills"]:
        path = f"fronts/{front_id}/skills/{sk}/SKILL.md"
        tag = "FRONT_SKILL_OK" if os.path.isfile(path) else "FRONT_SKILL_MISSING"
        results.append((tag, front_id, sk, path))

    for pr in data["profiles"]:
        path = f"fronts/{front_id}/profiles/{pr}.md"
        tag = "FRONT_PROFILE_OK" if os.path.isfile(path) else "FRONT_PROFILE_MISSING"
        results.append((tag, front_id, pr, path))

    methodology = data["methodology"]
    if methodology and methodology != "none":
        tag = "METHODOLOGY_DOC_OK" if methodology in body else "METHODOLOGY_DOC_MISSING"
        results.append((tag, front_id, methodology))

# Orphans: any staged skill/profile not declared by its front's pack (or by no
# pack at all) is a drift between disk and declaration, in either direction.
for skills_dir in sorted(glob.glob("fronts/*/skills/*")):
    if not os.path.isdir(skills_dir):
        continue
    parts = skills_dir.replace("\\", "/").split("/")
    front_id, name = parts[1], parts[3]
    declared = packs.get(front_id, {}).get("skills", [])
    if name not in declared:
        results.append(("ORPHAN_SKILL", front_id, name, skills_dir))

for profile_file in sorted(glob.glob("fronts/*/profiles/*.md")):
    parts = profile_file.replace("\\", "/").split("/")
    front_id = parts[1]
    name = os.path.basename(profile_file)[:-3]
    declared = packs.get(front_id, {}).get("profiles", [])
    if name not in declared:
        results.append(("ORPHAN_PROFILE", front_id, name, profile_file))

# Activation state (fronts/.activated.json): front_id -> [skill names it
# installed into .claude/skills/]. Absence means nothing is active, not an
# error -- activation is normal usage, not an anomaly.
active_fronts = set()
state_path = "fronts/.activated.json"
if os.path.isfile(state_path):
    try:
        state = json.loads(read_text(state_path))
        if isinstance(state, dict):
            active_fronts = set(state.keys())
    except (ValueError, OSError):
        pass

# Which front declares which skill name, per the packs already parsed above.
skill_owner = {}
for front_id, data in packs.items():
    for sk in data["skills"]:
        skill_owner[sk] = front_id

# Core skills: every one must declare front: all, UNLESS it is a skill an
# active front installed (front: <that front id> expected instead), and none
# may keep the removed roles: key. A skill owned by an INACTIVE front is a
# stale copy left behind after deactivation -- that judgment belongs to the
# dedup check below, not here, so it is skipped in this loop entirely.
core_names = []
for skill_md in sorted(glob.glob(".claude/skills/*/SKILL.md")):
    name = os.path.basename(os.path.dirname(skill_md))
    core_names.append(name)
    data, _body, err = parse_frontmatter(read_text(skill_md))
    if err:
        results.append(("CORE_SKILL_PARSE_FAIL", skill_md, err))
        continue
    owner = skill_owner.get(name)
    if owner is not None and owner not in active_fronts:
        continue  # stale copy from a deactivated front; the dedup check owns this
    front_val = data.get("front")
    if owner in active_fronts:
        if front_val == owner:
            results.append(("CORE_SKILL_FRONT_OK_OWNED", skill_md, owner))
        else:
            results.append(("CORE_SKILL_FRONT_BAD", skill_md, front_val or "(missing)", owner))
    else:
        if front_val == "all":
            results.append(("CORE_SKILL_FRONT_OK", skill_md))
        else:
            results.append(("CORE_SKILL_FRONT_BAD", skill_md, front_val or "(missing)", "all"))
    if "roles" in data:
        results.append(("CORE_SKILL_HAS_ROLES_KEY", skill_md))

# A name staged under fronts/*/skills/ and also present in .claude/skills/ is
# exactly what activation produces -- expected while the owning front is
# active. It is a stale copy only once that front is no longer active.
for skills_dir in sorted(glob.glob("fronts/*/skills/*")):
    if not os.path.isdir(skills_dir):
        continue
    name = os.path.basename(skills_dir)
    if name not in core_names:
        continue
    front_id = skills_dir.replace("\\", "/").split("/")[1]
    if front_id in active_fronts:
        results.append(("DUP_ACTIVE_OK", name, front_id))
    else:
        results.append(("DUP_FRONT_CORE_SKILL", name, front_id))

# The nurse test, as a lint: retired job-title ids must not reappear in the
# core as identifiers. Word occurrences alone are not evidence -- "engineer"
# and "founder" are ordinary English words the onboarding skill legitimately
# uses in prose. Only flag identifier-shaped usage: YAML list membership,
# role_id:/roles: keys, quoted literals, or front/skills-style paths.
for path in sorted(glob.glob(".claude/skills/**/*", recursive=True)):
    if not os.path.isfile(path):
        continue
    text = read_text(path)
    for rid in RETIRED_ROLE_IDS:
        esc = re.escape(rid)
        patterns = [
            r"\brole_pack\b",
            rf"role_id:\s*[\"']?{esc}\b",
            rf"roles:\s*\[[^\]]*\b{esc}\b",
            rf"(?:\[|,)\s*[\"']?{esc}[\"']?\s*(?:,|\])",
            rf"skills/{esc}(?:/|\b)",
            rf"profiles/{esc}\.md",
            rf"[\"']{esc}[\"']",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                snippet = m.group(0).strip()
                results.append(("LINT_HIT", path, rid, snippet))
                break

for row in results:
    # Normalize to forward slashes: bash's ok()/record_failure() print via
    # `echo -e`, which would otherwise interpret a native Windows path like
    # "fronts\biz.md" as containing the backspace escape \b and corrupt output.
    print("\t".join(str(x).replace("\\", "/") for x in row))
PY

pack_checked=0
lint_hits=0
while IFS=$'\t' read -r tag f1 f2 f3 f4; do
  [[ -z "$tag" ]] && continue
  tag="${tag%$'\r'}"; f1="${f1%$'\r'}"; f2="${f2%$'\r'}"; f3="${f3%$'\r'}"; f4="${f4%$'\r'}"

  case "$tag" in
    PACK_PARSE_FAIL)
      record_failure "Front pack $f1 has invalid frontmatter: $f2" ;;
    PACK_MISSING_KEYS)
      record_failure "Front pack $f1 is missing required frontmatter keys: $f2" ;;
    PACK_PARSE_OK)
      ok "Front pack $f1 has parseable frontmatter with required keys"
      pack_checked=$((pack_checked + 1)) ;;
    PACK_ID_MATCH)
      ok "Front pack $f1 front_id matches its filename" ;;
    PACK_ID_MISMATCH)
      record_failure "Front pack $f1 declares front_id '$f2' but the filename implies '$f3'" ;;
    FRONT_SKILL_OK)
      ok "Front '$f1' skill '$f2' exists at $f3" ;;
    FRONT_SKILL_MISSING)
      record_failure "Front '$f1' declares skill '$f2' but $f3 is missing" ;;
    FRONT_PROFILE_OK)
      ok "Front '$f1' profile '$f2' exists at $f3" ;;
    FRONT_PROFILE_MISSING)
      record_failure "Front '$f1' declares profile '$f2' but $f3 is missing" ;;
    METHODOLOGY_DOC_OK)
      ok "Front '$f1' pack documents its methodology '$f2' in the body text" ;;
    METHODOLOGY_DOC_MISSING)
      record_failure "Front '$f1' declares methodology '$f2' but never mentions it in the pack body" ;;
    ORPHAN_SKILL)
      record_failure "Undeclared skill directory $f3 is not listed in fronts/$f1.md skills" ;;
    ORPHAN_PROFILE)
      record_failure "Undeclared profile file $f3 is not listed in fronts/$f1.md profiles" ;;
    CORE_SKILL_PARSE_FAIL)
      record_failure "Core skill $f1 has invalid frontmatter: $f2" ;;
    CORE_SKILL_FRONT_OK)
      ok "Core skill $f1 declares front: all" ;;
    CORE_SKILL_FRONT_OK_OWNED)
      ok "Core skill $f1 declares front: $f2, matching its owning active front '$f2'" ;;
    CORE_SKILL_FRONT_BAD)
      record_failure "Core skill $f1 declares front: $f2 (must be '$f3')" ;;
    CORE_SKILL_HAS_ROLES_KEY)
      record_failure "Core skill $f1 still declares the removed 'roles:' key" ;;
    DUP_ACTIVE_OK)
      ok "Skill '$f1' is installed in .claude/skills/ because front '$f2' is active (staged at fronts/$f2/skills/$f1/)" ;;
    DUP_FRONT_CORE_SKILL)
      record_failure "Skill '$f1' exists in .claude/skills/ but owning front '$f2' is not active (stale copy left behind; deactivate or remove it)" ;;
    LINT_HIT)
      record_failure "Retired role identifier '$f2' found in $f1 (matched: $f3) -- the core must not reintroduce job-title identifiers"
      lint_hits=$((lint_hits + 1)) ;;
    *)
      record_failure "Unrecognized fronts-validation result: $tag $f1 $f2 $f3 $f4" ;;
  esac
done < "$fronts_tmp"

if [[ $pack_checked -gt 0 ]]; then
  ok "Checked $pack_checked front pack(s) under fronts/"
fi

if [[ $lint_hits -eq 0 ]]; then
  ok "No retired role identifiers found in .claude/skills"
fi

rm -f "$fronts_tmp"

if [[ $failures -gt 0 ]]; then
  echo
  err "Validation failed with $failures error(s) and $warnings warning(s)"
  exit 1
fi

echo
ok "Validation passed with $warnings warning(s)"
