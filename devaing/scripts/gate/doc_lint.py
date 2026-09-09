#!/usr/bin/env python3
"""devaing gate: enforce markdown link and traceability invariants across a repo's docs.

Runs one check unconditionally -- every relative markdown link must resolve to
a real file on disk -- and three more when a config file turns them on: a
child doc must link a matching parent doc (parent_links), a doc in one lane
must link back into named source lanes (lane_traces), and a doc must carry a
heading with at least one EARS-style acceptance statement (ears).

The EARS check is opt-in and narrow on purpose. It only works for a project
that keeps its acceptance criteria inside a spec file the linter can open and
read. A devaing project doesn't: the acceptance criteria for a unit of work
live in its GitHub issue, not in a markdown file in the repo, so a file-walking
linter has no way to see them. Reading issues would need network access and an
API token, which would turn this script into something that can only run with
an agent or a CI secret behind it -- it would stop being the stdlib-only,
session-free check that can run in any CI job with nothing else present. So
this check stays off unless a project's docs genuinely hold the criteria as
text, and the caller has to say so explicitly via config.

One check that is deliberately absent: validating a doc's frontmatter `type`
against the folder it lives in. That would bake in one particular spec-tree
shape (e.g. "a user-story file must sit under a stories/ folder") as if every
devaing project organized its docs the same way. They don't. parent_links and
lane_traces are config-driven glob rules instead, precisely so this linter
enforces traceability without also imposing a doc tree on the project.

A file can opt out of the config-driven checks with `doc-lint: skip` in its
frontmatter. It cannot opt out of the broken-link check -- see is_skipped.

Case sensitivity is the platform's, not this script's. `os.path.exists` is
case-insensitive on Windows and case-sensitive on Linux, so a link written as
`docs/Setup.md` against a file named `docs/setup.md` passes on a developer's
Windows machine and fails in CI. That is not a bug to work around here: CI is
the authority, because it matches the case rules of the host the docs are
served from. Expect the divergence and read the CI failure as correct.

No third-party dependencies (stdlib only).
"""
import json
import os
import re
import sys

ENV_CONFIG_PATH = "DEVAING_GATE_DOC_LINT_CONFIG"
DEFAULT_CONFIG_PATH = ".devaing/gate/doc_lint.json"
DEFAULT_EARS_SECTION = "Acceptance criteria"

ALLOWED_TOP_KEYS = {"roots", "exclude", "parent_links", "lane_traces", "ears"}
DEFAULT_EXCLUDED_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    "vendor", ".next",
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
SKIP_TARGET_PREFIXES = ("http://", "https://", "mailto:", "//")

REF_RE = re.compile(r"\{(\d+)\}")
H2_RE = re.compile(r"^##\s+")
EARS_RE = re.compile(r"\b(?:WHEN|IF|WHILE|WHERE)\b.*\bTHE SYSTEM SHALL\b")


class ConfigError(Exception):
    """Raised when the config file itself cannot be parsed at all."""


def to_posix(path):
    """Normalize a filesystem path to forward slashes for glob/pattern matching."""
    return path.replace(os.sep, "/").replace("\\", "/")


def strip_code_spans(text):
    """Remove fenced code blocks and inline code spans before any link scan."""
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))


def read_frontmatter(text):
    """Scan a leading '---' ... '---' block as flat key: value lines. Not YAML."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def is_skipped(text):
    """True if this file's frontmatter opts it out of the config-driven checks.

    `doc-lint: skip` exempts a file from parent_links, lane_traces and ears --
    the checks that encode a project's chosen doc shape, where a deliberate
    exception is a real thing. It does NOT exempt it from the broken-link
    check: a link that points at nothing is never a false positive worth
    suppressing, and a per-file, permanent opt-out on a deterministic check
    would hand back the very thing this gate exists to remove, which is
    enforcement that depends on someone remembering.
    """
    return read_frontmatter(text).get("doc-lint") == "skip"


def clean_link_target(raw):
    """Strip a raw markdown link target down to a checkable path, or None to skip it."""
    text = raw.strip()
    if not text:
        return None
    if text.startswith("<"):
        close = text.find(">")
        text = text[1:close] if close != -1 else text[1:]
    else:
        pieces = text.split()
        text = pieces[0] if pieces else ""
    text = text.split("#", 1)[0].strip()
    if not text or text.startswith(SKIP_TARGET_PREFIXES):
        return None
    return text


def resolve_link(file_rel, target):
    """Resolve a link target against its containing file into a repo-relative posix path."""
    joined = os.path.normpath(os.path.join(os.path.dirname(file_rel), target))
    return to_posix(joined)


def compile_glob(pattern):
    """Compile a repo-relative glob into a regex; each wildcard becomes a capture group.

    '**/' -> optional '.../' prefix, '**' -> anything, '*' -> one path segment
    (no '/'), '?' -> one character (no '/'). Returns (regex, wildcard_count);
    match with regex.fullmatch(path), never regex.match.
    """
    tokens = []
    count = 0
    i, n = 0, len(pattern)
    while i < n:
        if pattern.startswith("**/", i):
            tokens.append("((?:.*/)?)")
            count += 1
            i += 3
        elif pattern.startswith("**", i):
            tokens.append("(.*)")
            count += 1
            i += 2
        elif pattern[i] == "*":
            tokens.append("([^/]*)")
            count += 1
            i += 1
        elif pattern[i] == "?":
            tokens.append("([^/])")
            count += 1
            i += 1
        else:
            tokens.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(tokens)), count


def substitute_refs(template, captures):
    """Replace {1}, {2}, ... in a parent template with a matched child's captures."""
    return REF_RE.sub(lambda m: captures[int(m.group(1)) - 1], template)


def build_heading_regex(section):
    """Build a case-insensitive '## <section words>' matcher for a configured section name."""
    words = [re.escape(w) for w in section.split()]
    return re.compile(r"^##\s+" + r"\s+".join(words), re.IGNORECASE)


def _is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def load_raw_config(path):
    """Read and JSON-parse the config file. Raises ConfigError if it isn't valid JSON."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON ({exc})")


def validate_config(raw):
    """Validate and compile the parsed config. Returns (compiled_config, error_messages).

    On any error, compiled_config is None and every problem found is reported
    -- a config with three typos should say so three times, not stop at the
    first one.
    """
    errors = []
    if not isinstance(raw, dict):
        return None, ["config root must be a JSON object"]

    for key in sorted(set(raw) - ALLOWED_TOP_KEYS):
        errors.append(f"unknown top-level key '{key}'")

    roots = raw.get("roots", ["."])
    if not _is_str_list(roots) or not roots:
        errors.append("'roots' must be a non-empty list of strings")
        roots = ["."]

    exclude = raw.get("exclude", [])
    if not _is_str_list(exclude):
        errors.append("'exclude' must be a list of strings")
        exclude = []

    parent_links = []
    pl_raw = raw.get("parent_links", [])
    if not isinstance(pl_raw, list):
        errors.append("'parent_links' must be a list")
        pl_raw = []
    for i, rule in enumerate(pl_raw):
        label = f"parent_links[{i}]"
        if not isinstance(rule, dict):
            errors.append(f"{label} must be an object")
            continue
        children = rule.get("children")
        parent = rule.get("parent")
        if not isinstance(children, str) or not children:
            errors.append(f"{label}.children must be a non-empty string")
            continue
        if not isinstance(parent, str) or not parent:
            errors.append(f"{label}.parent must be a non-empty string")
            continue
        children_regex, group_count = compile_glob(children)
        bad_refs = sorted(
            {int(n) for n in REF_RE.findall(parent)} - set(range(1, group_count + 1))
        )
        if bad_refs:
            errors.append(
                f"{label}.parent references {{{bad_refs[0]}}} but children pattern "
                f"'{children}' only has {group_count} wildcard(s)"
            )
            continue
        parent_links.append({"children_regex": children_regex, "parent_template": parent})

    lane_traces = []
    lt_raw = raw.get("lane_traces", [])
    if not isinstance(lt_raw, list):
        errors.append("'lane_traces' must be a list")
        lt_raw = []
    for i, rule in enumerate(lt_raw):
        label = f"lane_traces[{i}]"
        if not isinstance(rule, dict):
            errors.append(f"{label} must be an object")
            continue
        from_pattern = rule.get("from")
        to_patterns = rule.get("to")
        if not isinstance(from_pattern, str) or not from_pattern:
            errors.append(f"{label}.from must be a non-empty string")
            continue
        if not _is_str_list(to_patterns) or not to_patterns:
            errors.append(f"{label}.to must be a non-empty list of strings")
            continue
        from_regex, _ = compile_glob(from_pattern)
        to_regexes = [compile_glob(p)[0] for p in to_patterns]
        lane_traces.append(
            {"from_regex": from_regex, "to_regexes": to_regexes, "to_patterns": to_patterns}
        )

    ears = None
    if "ears" in raw:
        ears_raw = raw["ears"]
        if not isinstance(ears_raw, dict):
            errors.append("'ears' must be an object")
        else:
            files_pattern = ears_raw.get("files")
            section = ears_raw.get("section", DEFAULT_EARS_SECTION)
            if not isinstance(files_pattern, str) or not files_pattern:
                errors.append("ears.files must be a non-empty string")
            elif not isinstance(section, str) or not section:
                errors.append("ears.section must be a non-empty string")
            else:
                files_regex, _ = compile_glob(files_pattern)
                ears = {"files_regex": files_regex, "section": section}

    if errors:
        return None, errors
    return {
        "roots": roots,
        "exclude": exclude,
        "parent_links": parent_links,
        "lane_traces": lane_traces,
        "ears": ears,
    }, []


def discover_markdown_files(roots, extra_excludes):
    """Walk roots for *.md files, pruning default and configured excluded directories."""
    bare_excludes = set(DEFAULT_EXCLUDED_DIR_NAMES)
    prefix_excludes = []
    for entry in extra_excludes:
        cleaned = entry.strip().strip("/")
        if not cleaned:
            continue
        if "/" in cleaned:
            prefix_excludes.append(cleaned)
        else:
            bare_excludes.add(cleaned)

    found = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = to_posix(os.path.normpath(dirpath))
            if rel_dir == ".":
                rel_dir = ""
            kept = []
            for d in dirnames:
                child = f"{rel_dir}/{d}" if rel_dir else d
                if d in bare_excludes or any(
                    child == p or child.startswith(p + "/") for p in prefix_excludes
                ):
                    continue
                kept.append(d)
            dirnames[:] = kept
            for name in filenames:
                if name.endswith(".md"):
                    found.add(f"{rel_dir}/{name}" if rel_dir else name)
    return found


def check_broken_links(files, file_texts):
    """Resolve every relative link in every file. Returns (errors, resolved_count, link_index)."""
    errors = []
    resolved_count = 0
    link_index = {}
    for f in files:
        stripped = strip_code_spans(file_texts[f])
        resolved_targets = []
        for match in LINK_RE.finditer(stripped):
            target = clean_link_target(match.group(1))
            if target is None:
                continue
            candidate = resolve_link(f, target)
            if os.path.exists(candidate):
                resolved_targets.append(candidate)
                resolved_count += 1
            else:
                errors.append(f"BROKEN LINK   {f} -> {target}")
        link_index[f] = resolved_targets
    return errors, resolved_count, link_index


def check_parent_links(rules, files, link_index):
    """Each file matching a rule's children glob must link a file matching its parent glob."""
    errors = []
    for rule in rules:
        for f in files:
            match = rule["children_regex"].fullmatch(f)
            if not match:
                continue
            resolved_pattern = substitute_refs(rule["parent_template"], match.groups())
            parent_regex, _ = compile_glob(resolved_pattern)
            satisfied = any(
                t != f and parent_regex.fullmatch(t) for t in link_index.get(f, [])
            )
            if not satisfied:
                errors.append(
                    f"NO PARENT LINK   {f} (must link a parent matching {resolved_pattern})"
                )
    return errors


def check_lane_traces(rules, files, link_index):
    """Each file matching a rule's from glob must link a file matching one of its to globs."""
    errors = []
    for rule in rules:
        for f in files:
            if not rule["from_regex"].fullmatch(f):
                continue
            satisfied = any(
                t != f and any(rx.fullmatch(t) for rx in rule["to_regexes"])
                for t in link_index.get(f, [])
            )
            if not satisfied:
                targets = ", ".join(rule["to_patterns"])
                errors.append(f"NO TRACE   {f} (must link one of: {targets})")
    return errors


def check_ears(cfg, files, file_texts):
    """Each matching file must carry the configured section, containing an EARS statement."""
    errors = []
    files_regex = cfg["files_regex"]
    section = cfg["section"]
    heading_re = build_heading_regex(section)
    for f in files:
        if not files_regex.fullmatch(f):
            continue
        lines = file_texts[f].splitlines()
        start = next((i for i, ln in enumerate(lines) if heading_re.match(ln)), None)
        if start is None:
            errors.append(f"NO ACCEPTANCE CRITERIA   {f} (missing a '## {section}' heading)")
            continue
        end = next((j for j in range(start + 1, len(lines)) if H2_RE.match(lines[j])), len(lines))
        body = "\n".join(lines[start + 1:end])
        if not EARS_RE.search(body):
            errors.append(
                f"NO EARS CRITERIA   {f} (the '## {section}' section has no "
                "WHEN/IF/WHILE/WHERE ... THE SYSTEM SHALL statement)"
            )
    return errors


def print_failure(errors, closing_lines):
    print("doc_lint FAILED:")
    for e in errors:
        print(f"  {e}")
    print()
    for line in closing_lines:
        print(f"  {line}")


def main():
    config_path = os.environ.get(ENV_CONFIG_PATH, DEFAULT_CONFIG_PATH)
    compiled_config = None

    if os.path.exists(config_path):
        try:
            raw = load_raw_config(config_path)
        except ConfigError as exc:
            print_failure(
                [f"BAD CONFIG   {exc}"],
                [
                    f"{config_path} is malformed -- fix it and re-run.",
                    "A config that fails silently would disable checks without telling anyone.",
                ],
            )
            return 1
        compiled_config, config_errors = validate_config(raw)
        if config_errors:
            print_failure(
                [f"BAD CONFIG   {m}" for m in config_errors],
                [
                    f"{config_path} is malformed -- fix it and re-run.",
                    "A config that fails silently would disable checks without telling anyone.",
                ],
            )
            return 1

    roots = compiled_config["roots"] if compiled_config else ["."]
    exclude = compiled_config["exclude"] if compiled_config else []

    all_files = sorted(discover_markdown_files(roots, exclude))
    file_texts = {}
    skipped = set()
    for f in all_files:
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
        file_texts[f] = text
        if is_skipped(text):
            skipped.add(f)
    files = sorted(file_texts)
    # Broken links run on every file, opted out or not. The opt-out only covers
    # the config-driven checks (see is_skipped).
    rule_files = [f for f in files if f not in skipped]

    errors, resolved_count, link_index = check_broken_links(files, file_texts)

    if compiled_config:
        errors.extend(check_parent_links(compiled_config["parent_links"], rule_files, link_index))
        errors.extend(check_lane_traces(compiled_config["lane_traces"], rule_files, link_index))
        if compiled_config["ears"]:
            errors.extend(check_ears(compiled_config["ears"], rule_files, file_texts))

    if errors:
        print_failure(
            errors,
            [
                "Fix the flagged files -- resolve broken links, add the missing",
                "parent/lane links, or add EARS acceptance criteria -- and re-run.",
            ],
        )
        return 1

    summary = f"{len(files)} markdown files, {resolved_count} links resolved"
    if skipped:
        summary += f", {len(skipped)} opted out of rule checks"
    if compiled_config is None:
        note = f"broken-link check only -- no {config_path}"
    else:
        parts = []
        if compiled_config["parent_links"]:
            parts.append(f"{len(compiled_config['parent_links'])} parent-link rule(s)")
        if compiled_config["lane_traces"]:
            parts.append(f"{len(compiled_config['lane_traces'])} lane-trace rule(s)")
        if compiled_config["ears"]:
            ears_regex = compiled_config["ears"]["files_regex"]
            ears_count = sum(1 for f in rule_files if ears_regex.fullmatch(f))
            parts.append(f"EARS check on {ears_count} file(s)")
        note = ", ".join(parts) if parts else "config present, no rules configured"
    print(f"doc_lint OK: {summary} ({note}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
