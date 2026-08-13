#!/usr/bin/env python3
"""swarm-kb dashboard — a local, READ-ONLY viewer for the git coordination
substrate (tasks / claims / ready / bounced / merges / decisions).

Run:  python3 dashboard.py [--repo PATH] [--port 8787] [--no-fetch]

It never mutates the substrate. The only network op is a best-effort
`git fetch` of the coordination refspecs (read). Everything else is
`git for-each-ref` / `git log` / `git show -s` and reading files. Binds to
127.0.0.1 only. stdlib only.
"""

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# config (populated by main)
# ---------------------------------------------------------------------------
REPO = os.getcwd()
TTL_MIN = int(os.environ.get("CLAIM_TTL_MIN", "45"))
REMOTE = os.environ.get("REMOTE", "origin")

# coordination refspecs — the exact set the swarm scripts fetch (read-only).
FETCH_REFSPECS = [
    "+refs/claims/*:refs/claims/*",
    "+refs/ready/*:refs/ready/*",
    "+refs/bounced/*:refs/bounced/*",
    "+refs/heads/*:refs/remotes/" + REMOTE + "/*",
]


# ---------------------------------------------------------------------------
# git helpers (READ-ONLY)
# ---------------------------------------------------------------------------
def git(args, timeout=15):
    """Run a read-only git command; return (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(
            ["git", "-C", REPO] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # pragma: no cover - defensive
        return 1, "", str(e)


def git_out(args, timeout=15):
    return git(args, timeout=timeout)[1]


def git_fetch():
    """Best-effort read-only fetch of coordination refs. Never crashes."""
    rc, _out, err = git(
        ["fetch", "-q", "--prune", REMOTE] + FETCH_REFSPECS, timeout=45
    )
    return {"ok": rc == 0, "error": (err.strip() if rc != 0 else "")}


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------
def now_utc():
    return _dt.datetime.now(_dt.timezone.utc)


def iso_now():
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def parse_frontmatter(text):
    """Parse a simple YAML-ish frontmatter block into a flat dict of strings."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # strip wrapping quotes
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
    return fm


def parse_iso(s):
    """Best-effort ISO-8601 -> aware datetime, else None."""
    if not s:
        return None
    s = s.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = _dt.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return d
    except Exception:
        return None


def age_minutes_from_epoch(ts):
    try:
        return int((now_utc().timestamp() - float(ts)) / 60)
    except Exception:
        return None


def human_age(minutes):
    if minutes is None:
        return "?"
    if minutes < 0:
        minutes = 0
    if minutes < 60:
        return "%dm" % minutes
    h = minutes // 60
    m = minutes % 60
    if h < 24:
        return "%dh%02dm" % (h, m)
    d = h // 24
    h = h % 24
    return "%dd%02dh" % (d, h)


# ---------------------------------------------------------------------------
# state collectors
# ---------------------------------------------------------------------------
def _task_from_text(text, relpath, fn, is_done):
    """Parse one task file's text into a task dict; None if not a task file."""
    fm = parse_frontmatter(text)
    if not fm and not is_done:
        return None  # no frontmatter => not a task file
    created = parse_iso(fm.get("created_at", ""))
    age_min = None
    if created:
        age_min = int((now_utc() - created).total_seconds() / 60)
    status = fm.get("status", "done" if is_done else "unknown")
    return {
        "id": fm.get("id", fn[:-3]),
        "title": fm.get("title", fn[:-3]),
        "status": status,
        "type": fm.get("type", ""),
        "priority": fm.get("priority", ""),
        "claimed_by": fm.get("claimed_by", ""),
        "blocked_on": fm.get("blocked_on", ""),
        "created_at": fm.get("created_at", ""),
        "age": human_age(age_min),
        "file": relpath,
        "done_dir": is_done,
    }


def _is_task_path(path):
    """(True, is_done) for a real task file path; (False, _) otherwise.
    Real tasks are tasks/<file>.md and tasks/done/<file>.md — NOT proposals/,
    templates, or READMEs."""
    if not path.endswith(".md"):
        return False, False
    fn = os.path.basename(path)
    if fn.startswith("_") or fn == "README.md":
        return False, False
    rest = path[len("tasks/"):] if path.startswith("tasks/") else path
    if rest.startswith("done/"):
        # tasks/done/<file>.md (no deeper nesting)
        return ("/" not in rest[len("done/"):]), True
    # tasks/<file>.md directly (excludes proposals/, done/, any subdir)
    return ("/" not in rest), False


def collect_tasks():
    """Read task files from origin/main (the live substrate) so the board is
    not stale on a checkout that lags origin. Returns (tasks, source) where
    source is 'origin/main' or 'local' (working-tree fallback)."""
    ref = main_ref()
    if ref:
        out = git_out(
            ["ls-tree", "-r", "--name-only", ref, "--", "tasks/"]
        )
        paths = [p for p in out.splitlines() if p.strip()]
        # only trust this path if the ref actually resolved to tasks content
        if paths:
            tasks = []
            for path in sorted(paths):
                ok, is_done = _is_task_path(path)
                if not ok:
                    continue
                text = git_blob(ref, path)
                t = _task_from_text(text, path, os.path.basename(path), is_done)
                if t is not None:
                    tasks.append(t)
            return tasks, ref

    # fallback: read the local working tree (origin unavailable)
    tasks = []
    dirs = [
        (os.path.join(REPO, "tasks"), False),
        (os.path.join(REPO, "tasks", "done"), True),
    ]
    for d, is_done in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md") or fn.startswith("_") or fn == "README.md":
                continue
            path = os.path.join(d, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception:
                continue
            t = _task_from_text(text, os.path.relpath(path, REPO), fn, is_done)
            if t is not None:
                tasks.append(t)
    return tasks, "local"


_CLAIM_MSG_RE = re.compile(r"^claim\s+(\S+)\s+by\s+(\S+)\s+at\s+(\S+)")


def collect_refs(namespace):
    """Return a list of {name, sha, agent, at, epoch, age_minutes, stale, subject}
    for refs under refs/<namespace>/*."""
    out = git_out(
        [
            "for-each-ref",
            "refs/%s" % namespace,
            "--format=%(refname:short)%09%(objectname)%09%(creatordate:unix)%09%(subject)",
        ]
    )
    items = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        short = parts[0] if len(parts) > 0 else ""
        sha = parts[1] if len(parts) > 1 else ""
        cdate = parts[2] if len(parts) > 2 else ""
        subject = parts[3] if len(parts) > 3 else ""
        # short looks like "claims/task-T0001"; strip the namespace prefix
        name = short.split("/", 1)[1] if "/" in short else short
        agent = ""
        at = ""
        epoch = cdate
        m = _CLAIM_MSG_RE.match(subject)
        if m:
            name = m.group(1)
            agent = m.group(2)
            at = m.group(3)
        age = age_minutes_from_epoch(epoch)
        items.append(
            {
                "name": name,
                "sha": sha[:8],
                "agent": agent,
                "at": at,
                "epoch": epoch,
                "age_minutes": age,
                "age": human_age(age),
                "stale": (age is not None and age > TTL_MIN),
                "subject": subject,
            }
        )
    items.sort(key=lambda x: (x["epoch"] or ""), reverse=False)
    return items


def collect_merges(limit=15):
    ref = REMOTE + "/main"
    # verify the ref exists, else fall back to HEAD/main
    if git(["rev-parse", "--verify", "-q", ref])[0] != 0:
        for alt in ["main", "HEAD"]:
            if git(["rev-parse", "--verify", "-q", alt])[0] == 0:
                ref = alt
                break
        else:
            return []
    out = git_out(
        [
            "log",
            ref,
            "-n",
            str(limit),
            "--date=iso-strict",
            "--pretty=%h%x09%an%x09%ad%x09%s",
        ]
    )
    merges = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        d = parse_iso(parts[2])
        age = None
        if d:
            age = int((now_utc() - d).total_seconds() / 60)
        merges.append(
            {
                "sha": parts[0],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
                "age": human_age(age),
            }
        )
    return merges


def collect_agent_activity(limit=6):
    d = os.path.join(REPO, "logs")
    if not os.path.isdir(d):
        return []
    entries = []
    for fn in os.listdir(d):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        path = os.path.join(d, fn)
        try:
            st = os.stat(path)
        except Exception:
            continue
        first = ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        first = line.strip().lstrip("#").strip()
                        break
        except Exception:
            pass
        entries.append(
            {
                "file": fn,
                "agent": fn[:-3],
                "first": first,
                "mtime": st.st_mtime,
            }
        )
    entries.sort(key=lambda x: x["mtime"], reverse=True)
    for e in entries:
        age = age_minutes_from_epoch(e.pop("mtime"))
        e["age"] = human_age(age)
    return entries[:limit]


def collect_decisions(limit=8):
    # Prefer origin/main so the feed matches the live substrate, not the checkout.
    text = ""
    ref = main_ref()
    if ref:
        text = git_blob(ref, "protocols/DECISIONS.md")
    if not text:
        path = os.path.join(REPO, "protocols", "DECISIONS.md")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception:
                text = ""
    if not text:
        return []
    # entries start with "### " headers; newest at top per the file convention.
    blocks = re.split(r"(?m)^###\s+", text)
    entries = []
    for b in blocks[1:]:
        b = b.strip()
        if not b:
            continue
        lines = b.splitlines()
        header = lines[0].strip()
        body = [ln.strip() for ln in lines[1:] if ln.strip()]
        entries.append({"header": header, "body": body[:6]})
    return entries[:limit]


def main_ref():
    """Resolve the ref to read main history from (prefer the remote-tracking
    origin/main so we see integrator merges other machines pushed)."""
    ref = REMOTE + "/main"
    if git(["rev-parse", "--verify", "-q", ref])[0] == 0:
        return ref
    for alt in ["main", "HEAD"]:
        if git(["rev-parse", "--verify", "-q", alt])[0] == 0:
            return alt
    return None


def epoch_to_iso(epoch):
    try:
        return _dt.datetime.fromtimestamp(
            float(epoch), _dt.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def git_blob(ref, path):
    """Read a file blob at a git ref (read-only). '' if absent."""
    rc, out, _err = git(["show", "%s:%s" % (ref, path)])
    return out if rc == 0 else ""


def logs_in_tree(ref):
    """List logs/*.md session-log paths present at a ref (best-effort)."""
    out = git_out(["ls-tree", "-r", "--name-only", ref, "logs/"])
    return [
        p
        for p in out.splitlines()
        if p.startswith("logs/") and p.endswith(".md") and p != "logs/README.md"
    ]


def merge_files(parent, sha):
    """Files the merge introduced onto main = diff first-parent..merge."""
    out = git_out(
        ["diff-tree", "-r", "--no-commit-id", "--name-status", parent, sha]
    )
    files = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) >= 2:
            files.append({"status": p[0], "path": p[-1]})
    return files


_ROLE_RE = re.compile(r"\b(PLANNER|WORKER|INTEGRATOR)\b", re.I)
_AGENT_RE = re.compile(r"([0-9]{12}-[0-9a-fA-F]{4})")


def infer_role(paths, log_text):
    """Infer the role of an agent unit: trust the session log's header first,
    then fall back to which parts of the tree the commit wrote."""
    if log_text:
        m = _ROLE_RE.search(log_text[:400])
        if m:
            return m.group(1).lower()
    real_task = any(
        re.match(r"tasks/T\d{4}-", p) or p.startswith("tasks/done/") for p in paths
    )
    governance = any(
        p.startswith("protocols/QUESTIONS") or p.startswith("protocols/DECISIONS")
        for p in paths
    )
    kb = any(
        p.startswith("kb/") and not p.endswith("index.generated.md") for p in paths
    )
    if real_task or governance:
        return "planner"
    if kb:
        return "worker"
    return "agent"


def merge_unit(subject):
    """Extract the (unit-label, agent-id) a merge commit integrated."""
    agent = ""
    ma = re.search(r"agent\s+([0-9]{12}-[0-9a-fA-F]{4})", subject)
    if ma:
        agent = ma.group(1)
    mp = re.search(r"plan[-\s]([0-9]{12}-[0-9a-fA-F]{4})", subject, re.I)
    mt = re.search(r"\bT\d{4}\b", subject)
    if mp:
        unit = "plan-" + mp.group(1)
        if not agent:
            agent = mp.group(1)
    elif mt:
        unit = mt.group(0)
    elif re.search(r"planner pass", subject, re.I):
        unit = "planner pass"
    else:
        unit = ""
    return unit, agent


def parse_main_commits(ref, limit):
    """One git-log pass: metadata + parents + per-commit name-status."""
    out = git_out(
        [
            "log",
            ref,
            "-n",
            str(limit),
            "--date=iso-strict",
            "--pretty=C%x09%H%x09%P%x09%ad%x09%s",
            "--name-status",
        ]
    )
    commits = []
    cur = None
    for line in out.split("\n"):
        if line.startswith("C\t"):
            parts = line.split("\t")
            cur = {
                "sha": parts[1] if len(parts) > 1 else "",
                "parents": parts[2].split() if len(parts) > 2 and parts[2] else [],
                "date": parts[3] if len(parts) > 3 else "",
                "subject": parts[4] if len(parts) > 4 else "",
                "files": [],
            }
            commits.append(cur)
        elif cur is not None and line.strip():
            p = line.split("\t")
            if len(p) >= 2:
                cur["files"].append({"status": p[0], "path": p[-1]})
    return commits


def _age_row(iso_date):
    d = parse_iso(iso_date)
    if not d:
        return 0.0, "?"
    ts = d.timestamp()
    return ts, human_age(int((now_utc() - d).total_seconds() / 60))


def collect_timeline(claims, ready, bounced, limit=25):
    """One row per UNIT of work, newest first. Derived SOLELY from git each
    call (no cache): in-flight claims + queued ready/bounced at the top, then
    completed units from origin/main history — integrator MERGE commits as
    their own rows, worker/planner commits (identified by an added logs/<id>.md)
    as their own rows with the full session log inline."""
    rows = []

    # 1. in-flight — live claims (newest first)
    for c in sorted(claims, key=lambda x: (x.get("epoch") or ""), reverse=True):
        name = c.get("name", "")
        if name == "integrator":
            role = "integrator"
        elif name == "planner":
            role = "planner"
        elif name.startswith("task-"):
            role = "worker"
        else:
            role = "agent"
        ts = float(c["epoch"]) if c.get("epoch") else 0.0
        rows.append(
            {
                "cls": "in_progress",
                "role": role,
                "when": c.get("at") or epoch_to_iso(c.get("epoch")),
                "age": c.get("age", "?"),
                "ts": ts,
                "agent": c.get("agent", ""),
                "unit": name[5:] if name.startswith("task-") else name,
                "subject": c.get("subject", ""),
                "files": [],
                "log": "",
                "stale": bool(c.get("stale")),
                "note": "in progress now",
            }
        )

    # 2. queued for integration — ready then bounced (read each unit's log)
    for refs, label in [(ready, "ready"), (bounced, "bounced")]:
        for r in sorted(refs, key=lambda x: (x.get("epoch") or "")):
            refpath = "refs/%s/%s" % (label, r["name"])
            log_text = ""
            agent = r.get("agent", "")
            lps = logs_in_tree(refpath)
            if lps:
                log_text = git_blob(refpath, lps[-1])
                agent = os.path.basename(lps[-1])[:-3]
            role = infer_role([], log_text)
            ts = float(r["epoch"]) if r.get("epoch") else 0.0
            rows.append(
                {
                    "cls": "queued",
                    "role": role if role != "agent" else "integrator",
                    "when": epoch_to_iso(r.get("epoch")),
                    "age": r.get("age", "?"),
                    "ts": ts,
                    "agent": agent,
                    "unit": r["name"],
                    "subject": r.get("subject", ""),
                    "files": [],
                    "log": log_text,
                    "stale": False,
                    "note": ("in integrator merge queue" if label == "ready"
                             else "bounced back for rework"),
                }
            )

    # 3. completed units — origin/main history, newest first (git log order)
    ref = main_ref()
    if ref:
        for c in parse_main_commits(ref, limit):
            paths = [f["path"] for f in c["files"]]
            ts, age = _age_row(c["date"])
            short = c["sha"][:8]
            if len(c["parents"]) >= 2:
                unit, agent = merge_unit(c["subject"])
                rows.append(
                    {
                        "cls": "unit",
                        "role": "integrator",
                        "when": c["date"],
                        "age": age,
                        "ts": ts,
                        "agent": agent,
                        "unit": unit,
                        "subject": c["subject"],
                        "files": merge_files(c["parents"][0], c["sha"]),
                        "log": "",
                        "stale": False,
                        "note": "merge " + short,
                    }
                )
                continue
            log_paths = [
                p
                for p in paths
                if p.startswith("logs/")
                and p.endswith(".md")
                and p != "logs/README.md"
            ]
            if log_paths:
                lp = log_paths[0]
                agent = os.path.basename(lp)[:-3]
                log_text = git_blob(c["sha"], lp)
                rows.append(
                    {
                        "cls": "unit",
                        "role": infer_role(paths, log_text),
                        "when": c["date"],
                        "age": age,
                        "ts": ts,
                        "agent": agent,
                        "unit": "",
                        "subject": c["subject"],
                        "files": c["files"],
                        "log": log_text,
                        "stale": False,
                        "note": short,
                    }
                )
            else:
                rows.append(
                    {
                        "cls": "unit",
                        "role": "system",
                        "when": c["date"],
                        "age": age,
                        "ts": ts,
                        "agent": "",
                        "unit": "",
                        "subject": c["subject"],
                        "files": c["files"],
                        "log": "",
                        "stale": False,
                        "note": short,
                    }
                )
    return rows


def cross_reference_claims(tasks, claims, ready=None, bounced=None):
    """A task's file `status:` lags reality — it only flips on the worker's
    branch and doesn't reach main until an integrator merges. Three live git
    signals outrank the lagging file status, in order of pipeline progress:
      - refs/bounced/<id>: the integrator rejected the work (needs rework)
      - refs/ready/<id>:   completed work sitting in the integrator merge queue
      - refs/claims/task-<id>: a worker is actively holding the task right now
    For any task carrying one of these, set effective_status='claimed' so the
    board groups it under "In progress" and attach a badge (queue / claim),
    while keeping the raw file status visible."""
    ready = ready or []
    bounced = bounced or []
    # index each signal by the task id it covers (ready/bounced ref name == id)
    by_claim = {}
    for c in claims:
        name = c.get("name", "")
        if name.startswith("task-"):
            by_claim[name[len("task-"):]] = c
    by_ready = {r.get("name", ""): r for r in ready}
    by_bounced = {r.get("name", ""): r for r in bounced}
    for t in tasks:
        t["effective_status"] = t.get("status", "")
        t["claim_agent"] = ""
        t["claim_age"] = ""
        t["claim_stale"] = False
        t["queue"] = ""
        t["queue_age"] = ""
        tid = t.get("id", "")
        raw = (t.get("status", "") or "").lower()
        if raw == "done":
            continue  # already merged to main; live signals no longer apply
        rb = by_bounced.get(tid)
        rr = by_ready.get(tid)
        c = by_claim.get(tid)
        if rb:  # bounced back for rework — most urgent to surface
            t["effective_status"] = "claimed"
            t["queue"] = "bounced"
            t["queue_age"] = rb.get("age", "")
        elif rr:  # completed work awaiting the integrator merge
            t["effective_status"] = "claimed"
            t["queue"] = "ready"
            t["queue_age"] = rr.get("age", "")
        elif c and raw != "ready":  # a worker is actively holding it
            t["effective_status"] = "claimed"
            t["claim_agent"] = c.get("agent", "")
            t["claim_age"] = c.get("age", "")
            t["claim_stale"] = bool(c.get("stale"))
    return tasks


def build_state():
    tasks, tasks_source = collect_tasks()
    claims = collect_refs("claims")
    ready = collect_refs("ready")
    bounced = collect_refs("bounced")
    cross_reference_claims(tasks, claims, ready, bounced)
    return {
        "generated_at": iso_now(),
        "repo": REPO,
        "remote": REMOTE,
        "ttl_min": TTL_MIN,
        "tasks": tasks,
        "task_count": len(tasks),
        "tasks_source": tasks_source,
        "claims": claims,
        "claim_count": len(claims),
        "ready": ready,
        "bounced": bounced,
        "merges": collect_merges(),
        "agents": collect_agent_activity(),
        "decisions": collect_decisions(),
        "timeline": collect_timeline(claims, ready, bounced),
    }


# ---------------------------------------------------------------------------
# HTML (self-contained: inline CSS + JS, no external resources)
# ---------------------------------------------------------------------------
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>swarm-kb dashboard</title>
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --panel2:#fafbfc; --border:#e2e5ea;
  --text:#1c2430; --muted:#697180; --accent:#2f6feb; --accent-soft:#e7effd;
  --ok:#1f9d55; --warn:#c9781a; --danger:#d43a3a; --shadow:0 1px 2px rgba(20,30,50,.06);
  --open:#8a6d3b; --claimed:#2f6feb; --inprog:#7a3fd4; --ready:#1f9d55; --done:#697180; --blocked:#d43a3a;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0e1117; --panel:#161b22; --panel2:#12161d; --border:#262d38;
    --text:#e6edf3; --muted:#8b97a7; --accent:#4d8bff; --accent-soft:#182338;
    --ok:#3fb96b; --warn:#e0a24a; --danger:#f06d6d; --shadow:0 1px 2px rgba(0,0,0,.4);
    --open:#d0a765; --claimed:#4d8bff; --inprog:#b17df0; --ready:#3fb96b; --done:#8b97a7; --blocked:#f06d6d;
  }
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--text);font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
header{position:sticky;top:0;z-index:10;background:var(--panel);border-bottom:1px solid var(--border);padding:10px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;box-shadow:var(--shadow)}
header h1{font-size:15px;margin:0;font-weight:650;letter-spacing:.2px}
header .repo{color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
header .spacer{flex:1}
.pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;background:var(--panel2);border:1px solid var(--border);color:var(--muted);font-size:11px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted);display:inline-block}
.dot.live{background:var(--ok);box-shadow:0 0 0 3px color-mix(in srgb,var(--ok) 22%,transparent)}
.dot.err{background:var(--danger)}
button{font:inherit;cursor:pointer;border:1px solid var(--border);background:var(--panel2);color:var(--text);padding:5px 12px;border-radius:7px;transition:.12s}
button:hover{border-color:var(--accent);color:var(--accent)}
button:disabled{opacity:.5;cursor:default}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
button.primary:hover{opacity:.9;color:#fff}
main{padding:14px 16px;max-width:1600px;margin:0 auto}
.grid{display:grid;gap:14px}
.cols{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:11px;box-shadow:var(--shadow);overflow:hidden}
.panel > h2{margin:0;font-size:12px;font-weight:650;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);padding:11px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
.panel > h2 .count{margin-left:auto;background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:20px;padding:1px 9px;font-size:11px;font-weight:600;letter-spacing:0}
.panel .body{padding:10px 12px;max-height:520px;overflow:auto}
.none{color:var(--muted);font-style:italic;padding:8px 2px}

/* task board */
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.board .col{background:var(--panel);border:1px solid var(--border);border-radius:11px;box-shadow:var(--shadow);display:flex;flex-direction:column;min-height:70px}
.board .col > h3{margin:0;font-size:11px;text-transform:uppercase;letter-spacing:.6px;padding:9px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:7px;font-weight:650}
.board .col > h3 .count{margin-left:auto;color:var(--muted);font-weight:600}
.board .col .cards{padding:9px;display:flex;flex-direction:column;gap:8px;overflow:auto;max-height:460px}
.card{background:var(--panel2);border:1px solid var(--border);border-left:3px solid var(--st);border-radius:8px;padding:8px 10px}
.card .id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted)}
.card .title{font-weight:550;margin:2px 0 5px;word-break:break-word}
.card .meta{display:flex;flex-wrap:wrap;gap:5px;font-size:10.5px}
.tag{background:var(--panel);border:1px solid var(--border);color:var(--muted);border-radius:5px;padding:1px 6px}
.tag.who{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 40%,var(--border))}
.tag.rdy{color:var(--ready);border-color:color-mix(in srgb,var(--ready) 45%,var(--border))}
.tag.blk{color:var(--danger);border-color:color-mix(in srgb,var(--danger) 40%,var(--border))}

.st-open{--st:var(--open)} .st-open h3{color:var(--open)}
.st-claimed{--st:var(--claimed)} .st-claimed h3{color:var(--claimed)}
.st-in_progress{--st:var(--inprog)} .st-in_progress h3{color:var(--inprog)}
.st-ready{--st:var(--ready)} .st-ready h3{color:var(--ready)}
.st-done{--st:var(--done)} .st-done h3{color:var(--done)}
.st-blocked{--st:var(--blocked)} .st-blocked h3{color:var(--blocked)}

/* claims */
.claim{padding:8px 4px;border-bottom:1px solid var(--border)}
.claim:last-child{border-bottom:0}
.claim .top{display:flex;align-items:baseline;gap:8px}
.claim .name{font-weight:600;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.claim .age{margin-left:auto;font-size:11px;color:var(--muted)}
.claim .who{font-size:11px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.claim.stale .name{color:var(--danger)}
.bar{height:5px;border-radius:4px;background:var(--panel2);border:1px solid var(--border);margin-top:6px;overflow:hidden}
.bar > i{display:block;height:100%;background:var(--ok)}
.bar.warn > i{background:var(--warn)}
.bar.stale > i{background:var(--danger)}
.stalebadge{color:var(--danger);font-weight:600;font-size:10px;border:1px solid color-mix(in srgb,var(--danger) 45%,var(--border));border-radius:5px;padding:0 6px}

/* rows */
.row{padding:7px 4px;border-bottom:1px solid var(--border)}
.row:last-child{border-bottom:0}
.row .l1{display:flex;gap:8px;align-items:baseline}
.row .sha{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);font-size:11px}
.row .age{margin-left:auto;color:var(--muted);font-size:11px;white-space:nowrap}
.row .sub{word-break:break-word}
.row .who{color:var(--muted);font-size:11px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.qname{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600}
.dec .hdr{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--accent);word-break:break-word}
.dec ul{margin:4px 0 0;padding-left:16px;color:var(--muted)}
.dec li{font-size:11.5px}
.srcnote{margin-left:10px;font-weight:500;text-transform:none;letter-spacing:0;font-size:10.5px;color:var(--muted)}
.srcnote.warn{color:var(--warn)}
.err-banner{background:color-mix(in srgb,var(--danger) 12%,var(--panel));border:1px solid color-mix(in srgb,var(--danger) 40%,var(--border));color:var(--danger);padding:6px 12px;border-radius:8px;font-size:11.5px;margin-bottom:12px}

/* timeline */
.tl{display:flex;flex-direction:column}
.tl .u{display:flex;gap:11px;padding:10px 6px;border-bottom:1px solid var(--border)}
.tl .u:last-child{border-bottom:0}
.tl .u.inflight{background:color-mix(in srgb,var(--accent) 7%,transparent)}
.tl .u.queued{background:color-mix(in srgb,var(--warn) 8%,transparent)}
.tl .rail{flex:0 0 92px;display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.tl .when{color:var(--muted);font-size:10.5px;white-space:nowrap}
.tl .main{flex:1;min-width:0}
.tl .hd{display:flex;flex-wrap:wrap;gap:7px;align-items:baseline}
.tl .unit{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600}
.tl .agent{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted)}
.tl .subj{margin-top:3px;word-break:break-word}
.tl .now{margin-left:auto;font-size:10px;color:var(--muted)}
.badge{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-radius:5px;padding:1px 7px;border:1px solid var(--bd,var(--border));color:var(--bd,var(--muted));white-space:nowrap}
.role-integrator{--bd:var(--inprog)}
.role-planner{--bd:var(--claimed)}
.role-worker{--bd:var(--ready)}
.role-system{--bd:var(--muted)}
.role-agent{--bd:var(--muted)}
.tl .files{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px}
.tl .f{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;color:var(--muted);background:var(--panel2);border:1px solid var(--border);border-radius:4px;padding:0 5px}
.tl .f b{font-weight:700;margin-right:3px}
.tl .f.A b{color:var(--ok)} .tl .f.M b{color:var(--warn)} .tl .f.D b{color:var(--danger)} .tl .f.R b{color:var(--accent)}
.tl details{margin-top:7px}
.tl summary{cursor:pointer;color:var(--accent);font-size:11px;width:max-content}
.tl pre{margin:6px 0 0;padding:9px 11px;background:var(--panel2);border:1px solid var(--border);border-radius:7px;overflow:auto;max-height:340px;font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
.tl .stalebadge{margin-left:0}
</style>
</head>
<body>
<header>
  <h1>swarm-kb</h1>
  <span class="repo" id="repo">…</span>
  <span class="pill"><span class="dot" id="statusdot"></span><span id="statustxt">connecting…</span></span>
  <span class="pill" id="ttlpill">TTL …</span>
  <span class="spacer"></span>
  <span class="pill" id="refreshed">—</span>
  <button class="primary" id="fetchbtn">Fetch &amp; refresh</button>
</header>
<main>
  <div id="errbox"></div>
  <section class="panel" style="margin-bottom:14px">
    <h2>Task board <span class="count" id="taskcount">0</span><span id="tasksrc" class="srcnote"></span></h2>
    <div class="body"><div class="board" id="board"></div></div>
  </section>
  <section class="panel" style="margin-bottom:14px">
    <h2>Activity timeline <span class="count" id="tlcount">0</span></h2>
    <div class="body" style="max-height:640px"><div class="tl" id="timeline"></div></div>
  </section>
  <div class="grid cols">
    <section class="panel">
      <h2>Claims <span class="count" id="claimcount">0</span></h2>
      <div class="body" id="claims"></div>
    </section>
    <section class="panel">
      <h2>Ready &amp; bounced <span class="count" id="queuecount">0</span></h2>
      <div class="body" id="queue"></div>
    </section>
    <section class="panel">
      <h2>Recent merges (main) <span class="count" id="mergecount">0</span></h2>
      <div class="body" id="merges"></div>
    </section>
    <section class="panel">
      <h2>Agent activity <span class="count" id="agentcount">0</span></h2>
      <div class="body" id="agents"></div>
    </section>
    <section class="panel">
      <h2>Decisions <span class="count" id="deccount">0</span></h2>
      <div class="body" id="decisions"></div>
    </section>
  </div>
</main>
<script>
const $=(id)=>document.getElementById(id);
function esc(s){return (s==null?'':String(s)).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
const STATUSES=[['open','open'],['claimed','In progress'],['blocked','blocked'],['done','done']];

let TTL=45;

function taskStatusGroup(t){
  // effective_status is claim-aware: a live refs/claims/task-<id> outranks the
  // lagging file status, so an actively-worked task lands in "claimed".
  let eff=(t.effective_status||t.status||'').toLowerCase();
  if(eff==='claimed') return 'claimed';
  let s=(t.status||'').toLowerCase();
  if(s==='open' && t.claimed_by) return 'claimed';
  if(s==='in_progress'||s==='ready') return 'claimed';  // main only shows open/done; these are transient worker-branch states
  if(['open','blocked','done'].includes(s)) return s;
  if(t.done_dir) return 'done';
  return 'open';
}

function renderBoard(tasks){
  const groups={};
  STATUSES.forEach(([k])=>groups[k]=[]);
  tasks.forEach(t=>{const g=taskStatusGroup(t);(groups[g]||(groups[g]=[])).push(t);});
  const board=$('board'); board.innerHTML='';
  const byId=(a,b)=>String(a.id||'').localeCompare(String(b.id||''),undefined,{numeric:true});
  STATUSES.forEach(([key,label])=>{
    const list=(groups[key]||[]).slice().sort(byId);
    const col=document.createElement('div');
    col.className='col st-'+key;
    let cards='';
    if(!list.length){ cards='<div class="none" style="padding:8px">none</div>'; }
    list.forEach(t=>{
      const claimed=(t.effective_status||'')==='claimed' && t.claim_agent;
      let meta='';
      if(t.type) meta+=`<span class="tag">${esc(t.type)}</span>`;
      if(t.priority) meta+=`<span class="tag">${esc(t.priority)}</span>`;
      // pipeline badges: queued (awaiting merge) / bounced / actively-claimed
      // tasks all render under "In progress"; the raw file status (which lags
      // until merged to main) is kept as a secondary tag.
      if(t.queue==='ready'){
        meta+=`<span class="tag rdy" title="completed work sitting in the integrator merge queue (refs/ready) — not yet merged to main">\u23f3 awaiting merge ${esc(t.queue_age||'')}</span>`;
        meta+=`<span class="tag" title="raw file status (lags until merged to main)">file: ${esc(t.status||'?')}</span>`;
      } else if(t.queue==='bounced'){
        meta+=`<span class="tag blk" title="the integrator bounced this work back for rework (refs/bounced)">\u21a9 bounced ${esc(t.queue_age||'')}</span>`;
        meta+=`<span class="tag" title="raw file status (lags until merged to main)">file: ${esc(t.status||'?')}</span>`;
      } else if(claimed){
        meta+=`<span class="tag who">@${esc(t.claim_agent)}</span>`;
        meta+=`<span class="tag ${t.claim_stale?'blk':''}">claim ${esc(t.claim_age)}${t.claim_stale?' STALE':''}</span>`;
        meta+=`<span class="tag" title="raw file status (lags until merged to main)">file: ${esc(t.status||'?')}</span>`;
      } else {
        if(t.claimed_by) meta+=`<span class="tag who">@${esc(t.claimed_by)}</span>`;
        if(t.age && t.age!=='?') meta+=`<span class="tag">${esc(t.age)}</span>`;
      }
      if(t.blocked_on) meta+=`<span class="tag blk">blocked: ${esc(t.blocked_on)}</span>`;
      cards+=`<div class="card"><div class="id">${esc(t.id)}</div><div class="title">${esc(t.title)}</div><div class="meta">${meta}</div></div>`;
    });
    col.innerHTML=`<h3>${esc(label.replace('_',' '))}<span class="count">${list.length}</span></h3><div class="cards">${cards}</div>`;
    board.appendChild(col);
  });
}

function renderClaims(claims){
  $('claimcount').textContent=claims.length;
  const el=$('claims');
  if(!claims.length){el.innerHTML='<div class="none">no live claims</div>';return;}
  // newest first
  const sorted=claims.slice().sort((a,b)=>(b.epoch||0)-(a.epoch||0));
  el.innerHTML=sorted.map(c=>{
    const am=c.age_minutes==null?0:c.age_minutes;
    let pct=Math.min(100,Math.round(am/TTL*100));
    let cls='';if(c.stale)cls='stale';else if(pct>=70)cls='warn';
    const who=c.agent?`by ${esc(c.agent)}`:'';
    const stale=c.stale?`<span class="stalebadge">STALE &gt;${TTL}m</span>`:'';
    return `<div class="claim ${c.stale?'stale':''}"><div class="top"><span class="name">${esc(c.name)}</span> ${stale}<span class="age">${esc(c.age)}</span></div><div class="who">${who}</div><div class="bar ${cls}"><i style="width:${pct}%"></i></div></div>`;
  }).join('');
}

function renderQueue(ready,bounced){
  $('queuecount').textContent=(ready.length+bounced.length);
  const el=$('queue');
  let html='';
  html+=`<div style="font-size:11px;color:var(--muted);margin:0 0 4px">MERGE QUEUE — awaiting integrator (${ready.length})</div>`;
  if(!ready.length) html+='<div class="none">none ready</div>';
  ready.slice().sort((a,b)=>(a.epoch||0)-(b.epoch||0)).forEach(r=>{
    html+=`<div class="row"><div class="l1"><span class="qname">${esc(r.name)}</span><span class="age">${esc(r.age)} old</span></div><div class="who">${esc(r.sha)}</div></div>`;
  });
  html+=`<div style="font-size:11px;color:var(--muted);margin:10px 0 4px">BOUNCED (${bounced.length})</div>`;
  if(!bounced.length) html+='<div class="none">none bounced</div>';
  bounced.forEach(r=>{
    html+=`<div class="row"><div class="l1"><span class="qname" style="color:var(--danger)">${esc(r.name)}</span><span class="age">${esc(r.age)} old</span></div><div class="who">${esc(r.sha)}</div></div>`;
  });
  el.innerHTML=html;
}

function renderMerges(m){
  $('mergecount').textContent=m.length;
  const el=$('merges');
  if(!m.length){el.innerHTML='<div class="none">no history</div>';return;}
  el.innerHTML=m.map(x=>`<div class="row"><div class="l1"><span class="sha">${esc(x.sha)}</span><span class="age">${esc(x.age)} ago</span></div><div class="sub">${esc(x.subject)}</div><div class="who">${esc(x.author)}</div></div>`).join('');
}

function renderAgents(a){
  $('agentcount').textContent=a.length;
  const el=$('agents');
  if(!a.length){el.innerHTML='<div class="none">no session logs yet</div>';return;}
  el.innerHTML=a.map(x=>`<div class="row"><div class="l1"><span class="who">${esc(x.file)}</span><span class="age">${esc(x.age)} ago</span></div><div class="sub">${esc(x.first||'(empty)')}</div></div>`).join('');
}

function renderDecisions(d){
  $('deccount').textContent=d.length;
  const el=$('decisions');
  if(!d.length){el.innerHTML='<div class="none">none yet</div>';return;}
  el.innerHTML=d.map(x=>`<div class="row dec"><div class="hdr">${esc(x.header)}</div>${x.body&&x.body.length?('<ul>'+x.body.map(b=>`<li>${esc(b)}</li>`).join('')+'</ul>'):''}</div>`).join('');
}

function renderTimeline(rows){
  $('tlcount').textContent=rows.length;
  const el=$('timeline');
  if(!rows.length){el.innerHTML='<div class="none">no activity yet</div>';return;}
  // remember which logs are expanded so a 5s poll doesn't collapse them
  const open=new Set();
  el.querySelectorAll('details[open][data-key]').forEach(d=>open.add(d.getAttribute('data-key')));
  el.innerHTML=rows.map(r=>{
    const role=(r.role||'agent');
    let cls='u';
    if(r.cls==='in_progress')cls+=' inflight';
    else if(r.cls==='queued')cls+=' queued';
    // files
    let files='';
    (r.files||[]).slice(0,20).forEach(f=>{
      const st=(f.status||'?')[0];
      files+=`<span class="f ${esc(st)}"><b>${esc(st)}</b>${esc(f.path)}</span>`;
    });
    if((r.files||[]).length>20) files+=`<span class="f">+${r.files.length-20} more</span>`;
    // log expandable
    let log='';
    if(r.log && r.log.trim()){
      const key=esc((r.cls||'')+'|'+(r.agent||'')+'|'+(r.note||'')+'|'+(r.unit||''));
      log=`<details data-key="${key}"${open.has(key)?' open':''}><summary>session log (${esc((r.agent||'log'))})</summary><pre>${esc(r.log)}</pre></details>`;
    }
    const unit = r.unit?`<span class="unit">${esc(r.unit)}</span>`:'';
    const agent = r.agent?`<span class="agent">@${esc(r.agent)}</span>`:'';
    const stale = r.stale?`<span class="stalebadge">STALE</span>`:'';
    let now='';
    if(r.cls==='in_progress') now=`<span class="now">${esc(r.note)} · ${esc(r.age)}${stale?'':''}</span>`;
    else if(r.cls==='queued') now=`<span class="now">${esc(r.note)} · ${esc(r.age)} old</span>`;
    else now=`<span class="now">${esc(r.note)} · ${esc(r.age)} ago</span>`;
    return `<div class="${cls}">
      <div class="rail"><span class="badge role-${esc(role)}">${esc(role)}</span><span class="when">${esc((r.when||'').replace('T',' ').replace(/(\+.*|Z)$/,''))}</span></div>
      <div class="main"><div class="hd">${unit}${agent}${r.cls==='in_progress'?stale:''}${now}</div>
      <div class="subj">${esc(r.subject||'')}</div>
      ${files?`<div class="files">${files}</div>`:''}
      ${log}</div></div>`;
  }).join('');
}

function setStatus(ok,txt){
  const dot=$('statusdot');
  dot.className='dot '+(ok?'live':'err');
  $('statustxt').textContent=txt;
}

function render(s){
  TTL=s.ttl_min||45;
  $('repo').textContent=s.repo;
  $('ttlpill').textContent='TTL '+TTL+'m';
  $('taskcount').textContent=s.task_count;
  const src=$('tasksrc');
  if(s.tasks_source==='local'){src.className='srcnote warn';src.textContent='reading local checkout (origin unavailable)';}
  else{src.className='srcnote';src.textContent='from '+esc(s.tasks_source||'origin/main');}
  renderBoard(s.tasks||[]);
  renderTimeline(s.timeline||[]);
  renderClaims(s.claims||[]);
  renderQueue(s.ready||[],s.bounced||[]);
  renderMerges(s.merges||[]);
  renderAgents(s.agents||[]);
  renderDecisions(s.decisions||[]);
  const t=new Date();
  $('refreshed').textContent='updated '+t.toLocaleTimeString();
}

let inflight=false;
async function load(path){
  if(inflight) return;
  inflight=true;
  try{
    const r=await fetch(path||'/api/state',{cache:'no-store'});
    const s=await r.json();
    render(s);
    setStatus(true,'live');
    $('errbox').innerHTML = s.fetch && s.fetch.ok===false && s.fetch.error
       ? `<div class="err-banner">git fetch failed (showing cached refs): ${esc(s.fetch.error)}</div>` : '';
  }catch(e){
    setStatus(false,'offline');
  }finally{
    inflight=false;
  }
}

$('fetchbtn').addEventListener('click',async()=>{
  const b=$('fetchbtn'); b.disabled=true; b.textContent='Fetching…';
  await load('/api/fetch');
  b.disabled=false; b.textContent='Fetch & refresh';
});

load('/api/state');
setInterval(()=>load('/api/fetch'),10000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/" or path == "/index.html":
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        elif path == "/api/state":
            self._send_state(do_fetch=False)
        elif path == "/api/fetch":
            self._send_state(do_fetch=True)
        else:
            self._send(404, json.dumps({"error": "not found"}), "application/json")

    def _send_state(self, do_fetch):
        fetch_result = None
        if do_fetch:
            fetch_result = git_fetch()
        try:
            state = build_state()
        except Exception as e:  # pragma: no cover - defensive
            self._send(
                500, json.dumps({"error": str(e)}), "application/json"
            )
            return
        if fetch_result is not None:
            state["fetch"] = fetch_result
        self._send(
            200,
            json.dumps(state),
            "application/json; charset=utf-8",
        )

    def log_message(self, fmt, *args):  # quieter logs
        return


def main():
    global REPO, TTL_MIN, FETCH_REFSPECS
    ap = argparse.ArgumentParser(description="swarm-kb read-only dashboard")
    ap.add_argument("--repo", default=os.getcwd(), help="path to the swarm-kb git repo")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-fetch", action="store_true", help="skip the git fetch on startup")
    args = ap.parse_args()

    REPO = os.path.abspath(args.repo)
    TTL_MIN = int(os.environ.get("CLAIM_TTL_MIN", "45"))

    if git(["rev-parse", "--git-dir"])[0] != 0:
        print("warning: %s does not look like a git repo" % REPO)

    if not args.no_fetch:
        print("initial git fetch (best-effort)…")
        r = git_fetch()
        print("  fetch ok" if r["ok"] else "  fetch skipped: %s" % r["error"])

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("swarm-kb dashboard on http://127.0.0.1:%d  (repo=%s, TTL=%dm)"
          % (args.port, REPO, TTL_MIN))
    print("READ-ONLY viewer. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        server.shutdown()


if __name__ == "__main__":
    main()
