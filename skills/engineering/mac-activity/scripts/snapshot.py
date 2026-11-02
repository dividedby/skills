#!/usr/bin/env python3
"""Light, read-only memory and CPU sampler for a Mac. Stdlib only, no root.

  snapshot.py sample [--samples N] [--interval SECONDS] [--extras]
  snapshot.py inspect --tool footprint|vmmap|leaks|heap --pid N [--start EPOCH] [--approved]

Every command prints one JSON object with `ok` true or false. It stops nothing.

Sizes come from `top` (MEM, the physical footprint) rather than `ps` (RSS). Under
memory pressure RSS leaves out compressed and swapped memory and can read several
times too low.

Command lines are read to name and classify a process, then dropped: they can hold
secrets, so nothing here stores or prints them. Samples go in a private folder
(mode 0700, MAC_ACTIVITY_DIR or ~/.claude/mac-activity). Later runs compare against
them, which gives an hours-long growth trend without any extra sampling.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

MB = 1024 * 1024
MAX_SAMPLES = 10
MIN_INTERVAL = 30
MAX_INTERVAL = 300
MAX_RUN_SECONDS = 900
KEEP_SAMPLES = 200
KEEP_DAYS = 14
STORE_MIN_MB = 30
LSOF_LIMIT = 60
HIGH_SWAP_PCT = 90
LARGE_MB = 500
LONG_RUNNING_S = 6 * 3600
GROW_MIN_MB = 50
GROW_MIN_FRACTION = 0.10
GROW_MIN_SPAN_S = 240
GROW_MIN_POINTS = 3
GROW_RISING_STEPS = 0.7
GROW_ALLOWED_DIP = 0.98
IDLE_CPU_PCT = 5
START_JITTER_S = 5

INTERPRETERS = {"node", "python", "python3", "bun", "deno", "ruby", "perl"}
SHELLS = {"bash", "zsh", "sh", "dash", "fish"}
PACKAGE_RUNNERS = {"npm", "npx", "pnpm", "pnpx", "uvx"}
GENERIC_SCRIPTS = {"index", "cli", "main", "server", "bin", "start", "run"}
VALUELESS_FLAGS = {"-y", "--yes", "-q", "--quiet"}
INLINE_CODE_FLAGS = {"-c", "-e", "-p", "--eval", "--print"}
WATCH_FLAGS = {"--watch", "--watchAll"}
PACKAGE_RE = re.compile(r"@?[\w.-]+(/[\w.-]+)?(@[\w.-]+)?")
SAMPLE_FILE_RE = re.compile(r"\d+\.json")
SCRIPT_RE = re.compile(r"/|\.(js|mjs|cjs|ts|py|rb|pl)$")
SERVER_RE = re.compile(
    r"(language-server|langserver|tsserver|^gopls$|^rust-analyzer$|pyright|^vite$|^vitest$|"
    r"^next-server$|^nodemon$|^webpack|^eslint_d$|^typingsInstaller$)"
)
BUILD_NAMES = {
    "swift-frontend", "swiftc", "swift-build", "xcodebuild", "clang", "clang++", "ld",
    "cc1", "cc1plus", "rustc", "cargo", "make", "ninja", "ibtool", "actool",
}
SYSTEM_PREFIXES = ("/System/", "/usr/", "/sbin/", "/bin/", "/Library/Apple/", "/private/var/")
WORKTREE_RE = re.compile(r"(?:^|[\s=\"'])(/[^\s]*?/\.claude/worktrees/[^/\s\"']+)")
TOP_ROW_RE = re.compile(
    r"^\s*(\d+)\*?\s+(\d+)\s+(.+?)\s+(\d[\d.]*[BKMGT]?)[+-]?\s+(\d[\d.]*[BKMGT]?)[+-]?\s+([\d.]+)\s*$"
)
DU_PATHS = (
    "~/Library/Developer/Xcode/DerivedData",
    "~/Library/Developer/CoreSimulator/Devices",
    "~/Library/Caches",
    "~/.npm",
    "~/Library/pnpm/store",
    "~/.cache",
)
TOOLS_NEEDING_APPROVAL = ("leaks", "heap")


class Refused(Exception):
    pass


def run(cmd, args, timeout=10):
    """Run a command from an argument list. Returns (returncode, stdout, stderr), never raises.

    On timeout the tool gets SIGTERM before SIGKILL, so vmmap, heap or leaks can resume
    the process they paused.
    """
    try:
        proc = subprocess.Popen([cmd] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    except OSError as err:
        return 127, "", str(err)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        return 124, "", f"{cmd} timed out after {timeout}s"


def data_dir():
    return os.environ.get("MAC_ACTIVITY_DIR") or os.path.expanduser("~/.claude/mac-activity")


def tilde(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path and path.startswith(home) else path


def size_mb(text):
    match = re.fullmatch(r"([\d.]+)\s*([BKMGT]?)B?", text.strip())
    if not match:
        return 0.0
    scale = {"": 1 / MB, "B": 1 / MB, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}[match.group(2)]
    return float(match.group(1)) * scale


def parse_etime(text):
    days, _, rest = text.strip().rpartition("-")
    parts = [int(p) for p in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def parse_top(text):
    """Use the last block: top's first block has no CPU figures yet."""
    block = text[text.rfind("Processes:"):] if "Processes:" in text else text
    header = {}
    procs = {}
    for line in block.splitlines():
        if line.startswith("Load Avg:"):
            header["load"] = [float(v) for v in re.findall(r"[\d.]+", line)[:3]]
        elif line.startswith("PhysMem:"):
            used = re.search(r"([\d.]+[BKMGT]) used", line)
            compressor = re.search(r"([\d.]+[BKMGT]) compressor", line)
            unused = re.search(r"([\d.]+[BKMGT]) unused", line)
            header["used_mb"] = round(size_mb(used.group(1))) if used else None
            header["compressor_mb"] = round(size_mb(compressor.group(1))) if compressor else None
            header["unused_mb"] = round(size_mb(unused.group(1))) if unused else None
        elif line.startswith("VM:"):
            swapouts = re.search(r"(\d+)\(\d+\) swapouts", line)
            header["swapouts"] = int(swapouts.group(1)) if swapouts else None
        else:
            row = TOP_ROW_RE.match(line)
            if row:
                procs[int(row.group(1))] = {
                    "mem": round(size_mb(row.group(4))),
                    "cmprs": round(size_mb(row.group(5))),
                    "cpu": float(row.group(6)),
                }
    return header, procs


def parse_swap(text):
    total = re.search(r"total = ([\d.]+[BKMGT])", text)
    used = re.search(r"used = ([\d.]+[BKMGT])", text)
    if not total or not used:
        return None, None
    return round(size_mb(total.group(1))), round(size_mb(used.group(1)))


def parse_ps(text):
    procs = {}
    for line in text.splitlines():
        fields = line.split(None, 4)
        if len(fields) == 5 and fields[0].isdigit():
            procs[int(fields[0])] = {
                "ppid": int(fields[1]),
                "uid": int(fields[2]),
                "age": parse_etime(fields[3]),
                "comm": fields[4],
            }
    return procs


def parse_args_table(text):
    table = {}
    for line in text.splitlines():
        fields = line.split(None, 1)
        if len(fields) == 2 and fields[0].isdigit():
            table[int(fields[0])] = fields[1]
    return table


def parse_launchctl(text):
    labels = {}
    for line in text.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit():
            labels[int(fields[0])] = fields[2]
    return labels


def parse_lsof_cwd(text):
    cwds = {}
    pid = None
    for line in text.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            cwds[pid] = line[1:]
    return cwds


def arguments_after(comm, args):
    """The words after the executable. A path with spaces is why this starts from comm."""
    tail = args[len(comm):] if args.startswith(comm) else " ".join(args.split()[1:])
    return tail.split()


def is_claude(comm):
    return os.path.basename(comm) == "claude" or bool(re.search(r"/claude/versions/[^/]+$", comm))


def name_and_kind(comm, args):
    # Only a name is kept, so nothing here may pick up a flag's value: it could be a secret.
    base = os.path.basename(comm) if "/" in comm else comm.split()[0]
    words = arguments_after(comm, args)
    name = base
    # npm rewrites its process title, so comm itself can read "npm exec pkg@1.2.3 mcp"
    retitled = re.match(r"^(?:npm|npx|pnpm) exec (.*)$", comm)
    if retitled:
        words = retitled.group(1).split() + words
        name = package_name(words) or base
    elif base in PACKAGE_RUNNERS:
        name = package_name([w for w in words if w != "exec"]) or base
    elif base in INTERPRETERS:
        name = script_name(words) or base
    elif is_claude(comm):
        name = "claude"
    if "mcp" in words or "mcp" in name.lower():
        kind = "mcp"
    elif SERVER_RE.search(name) or WATCH_FLAGS & set(words):
        kind = "server"
    elif name in BUILD_NAMES or base in BUILD_NAMES:
        kind = "build"
    elif base in SHELLS:
        kind = "shell"
    elif name == "claude":
        kind = "claude"
    else:
        kind = "other"
    return name, kind


def package_name(words):
    for word in words:
        if word in VALUELESS_FLAGS or (word.startswith("-") and "=" in word):
            continue
        if word.startswith("-") or not PACKAGE_RE.fullmatch(word):
            return None
        return re.sub(r"(?<=.)@[^/]*$", "", word)
    return None


def script_name(words):
    for index, word in enumerate(words):
        if word in INLINE_CODE_FLAGS:
            return None
        if word == "-m":
            following = words[index + 1] if index + 1 < len(words) else ""
            return following if re.fullmatch(r"[\w.]+", following) else None
        if not word.startswith("-") and SCRIPT_RE.search(word):
            return script_stem(word)
    return None


def script_stem(script):
    if "/.bin/" in script:
        return os.path.basename(script)
    stem = os.path.splitext(os.path.basename(script))[0]
    if stem in GENERIC_SCRIPTS and "node_modules/" in script:
        parts = script.rsplit("node_modules/", 1)[1].split("/")
        return "/".join(parts[:2]) if parts[0].startswith("@") else parts[0]
    return stem


def app_of(comm):
    if "CoreSimulator" in comm or "SimulatorRuntime" in comm or os.path.basename(comm) == "launchd_sim":
        return "iOS Simulator"
    if "/Application Support/Claude/claude-code/" in comm:
        return "Claude Code sessions"
    bundle = re.search(r"/([^/]+)\.app/", comm)
    if bundle:
        return bundle.group(1)
    if comm.startswith(SYSTEM_PREFIXES):
        return "macOS"
    return os.path.basename(comm) if "/" in comm else comm.split()[0]


def session_of(pid, table):
    """The outermost `claude` above pid, so a claude that a session started counts as that session's."""
    found = None
    seen = set()
    while pid in table and pid not in seen:
        seen.add(pid)
        if is_claude(table[pid]["comm"]):
            found = pid
        pid = table[pid]["ppid"]
    return found


def folder_of(cwd):
    if not cwd:
        return None
    worktree = re.match(r"^(.*)/\.claude/worktrees/([^/]+)", cwd)
    if worktree:
        return f"{tilde(worktree.group(1))} [worktree {worktree.group(2)}]"
    home = os.path.expanduser("~")
    repo = re.match(re.escape(home) + r"/repos/[^/]+", cwd)
    if repo:
        return tilde(repo.group(0))
    if cwd in ("/", home) or cwd.startswith(home + "/Library/"):
        return None
    return tilde(cwd)


def worktree_gone(args, cwd, kind):
    # A shell's command line is a script, so a path in it says nothing about the shell itself
    for text in ("" if kind == "shell" else args, cwd or ""):
        for path in WORKTREE_RE.findall(text):
            if not os.path.exists(path):
                return True
    return False


def take_machine():
    machine = {}
    code, out, _ = run("sysctl", ["-n", "vm.swapusage", "vm.loadavg", "hw.memsize", "hw.ncpu"])
    lines = out.splitlines() if code == 0 else []
    if len(lines) >= 4:
        machine["swap_total_mb"], machine["swap_used_mb"] = parse_swap(lines[0])
        machine["memory_mb"] = int(lines[2]) // MB
        machine["cpus"] = int(lines[3])
    code, out, _ = run("sysctl", ["-n", "kern.memorystatus_vm_pressure_level"])
    if code == 0 and out.strip().isdigit():
        machine["pressure"] = {1: "normal", 2: "warning", 4: "critical"}.get(int(out.strip()), out.strip())
    return machine


def swap_pct(machine):
    """None when swap couldn't be read. A Mac that hasn't swapped yet has a total of 0."""
    total = machine.get("swap_total_mb")
    if total is None:
        return None
    return round(100 * machine.get("swap_used_mb", 0) / total) if total else 0


def swap_too_full(pct):
    return pct is None or pct > HIGH_SWAP_PCT


def take_sample(cwd_cache):
    now = int(time.time())
    machine = take_machine()
    code, top_text, err = run("top", ["-l", "2", "-s", "1", "-stats", "pid,ppid,command,mem,cmprs,cpu"], timeout=20)
    if code != 0:
        raise Refused(f"top failed, so there is no sample: {err.strip()[:200]}")
    header, top = parse_top(top_text)
    machine.update(header)
    machine["swap_pct"] = swap_pct(machine)

    _, ps_text, _ = run("ps", ["-axo", "pid=,ppid=,uid=,etime=,comm="])
    table = parse_ps(ps_text)
    _, args_text, _ = run("ps", ["-axww", "-o", "pid=,args="])
    args_table = parse_args_table(args_text)
    _, launch_text, _ = run("launchctl", ["list"])
    launch = parse_launchctl(launch_text)

    me = os.getuid()
    procs = []
    for pid, info in table.items():
        figures = top.get(pid, {"mem": 0, "cmprs": 0, "cpu": 0.0})
        name, kind = name_and_kind(info["comm"], args_table.get(pid, info["comm"]))
        procs.append({
            "pid": pid,
            "ppid": info["ppid"],
            "start": now - info["age"],
            "age_s": info["age"],
            "name": name,
            "kind": kind,
            "app": app_of(info["comm"]),
            "mem": figures["mem"],
            "cmprs": figures["cmprs"],
            "cpu": figures["cpu"],
            "mine": info["uid"] == me,
            "session": session_of(pid, table),
        })

    fill_cwds(procs, cwd_cache)
    for proc in procs:
        comm = table[proc["pid"]]["comm"]
        args = args_table.get(proc["pid"], "")
        proc["flags"] = process_flags(proc, comm, args, launch)
        if "launch_agent" in proc["flags"]:
            proc["launch_label"] = launch[proc["pid"]]
    return {"at": now, "machine": machine, "procs": procs}


def fill_cwds(procs, cache):
    wanted = [p for p in procs if p["mine"]]
    wanted.sort(key=lambda p: (p["session"] is None, -p["mem"]))
    missing = [p for p in wanted[:LSOF_LIMIT] if (p["pid"], p["start"]) not in cache]
    if missing:
        pids = ",".join(str(p["pid"]) for p in missing)
        _, out, _ = run("lsof", ["-a", "-n", "-P", "-d", "cwd", "-Fpn", "-p", pids])
        found = parse_lsof_cwd(out)
        for proc in missing:
            cache[(proc["pid"], proc["start"])] = found.get(proc["pid"])
    for proc in procs:
        proc["cwd"] = cache.get((proc["pid"], proc["start"]))


def process_flags(proc, comm, args, launch):
    flags = []
    user_program = proc["mine"] and not comm.startswith(SYSTEM_PREFIXES + ("/Library/",)) and ".app/" not in comm
    if proc["ppid"] == 1 and user_program and proc["pid"] not in launch:
        flags.append("orphaned")
    # `application.*` entries are ordinary open apps, which `apps` already counts
    if proc["pid"] in launch and not launch[proc["pid"]].startswith(("com.apple.", "application.")):
        flags.append("launch_agent")
    if proc["mine"] and worktree_gone(args, proc["cwd"], proc["kind"]):
        flags.append("worktree_gone")
    if proc["age_s"] >= LONG_RUNNING_S and user_program:
        flags.append("long_running")
    if proc["mem"] >= LARGE_MB:
        flags.append("large")
    return flags


def public(proc):
    """What a report or a saved sample may hold about one process."""
    fields = ("pid", "ppid", "start", "age_s", "name", "kind", "app", "mem", "cmprs", "cpu", "session", "flags")
    out = {k: proc[k] for k in fields if k in proc}
    if proc.get("cwd"):
        out["cwd"] = tilde(proc["cwd"])
    if proc.get("launch_label"):
        out["launch_label"] = proc["launch_label"]
    return out


def add_up(procs, key):
    groups = {}
    for proc in procs:
        name = key(proc)
        if name is None:
            continue
        group = groups.setdefault(name, {"name": name, "count": 0, "mem": 0, "cmprs": 0, "cpu": 0.0})
        group["count"] += 1
        group["mem"] += proc["mem"]
        group["cmprs"] += proc["cmprs"]
        group["cpu"] = round(group["cpu"] + proc["cpu"], 1)
    return sorted(groups.values(), key=lambda g: -g["mem"])


def summarize_sessions(procs):
    sessions = []
    by_pid = {p["pid"]: p for p in procs}
    for session in sorted({p["session"] for p in procs if p["session"]}):
        tree = [p for p in procs if p["session"] == session]
        root = by_pid[session]
        children = {}
        for proc in tree:
            if proc["pid"] == session:
                continue
            child = children.setdefault(
                (proc["name"], proc["kind"]),
                {"name": proc["name"], "kind": proc["kind"], "count": 0, "mem": 0, "cpu": 0.0, "pids": [], "oldest_s": 0},
            )
            child["count"] += 1
            child["mem"] += proc["mem"]
            child["cpu"] = round(child["cpu"] + proc["cpu"], 1)
            child["oldest_s"] = max(child["oldest_s"], proc["age_s"])
            if len(child["pids"]) < 8:
                child["pids"].append(proc["pid"])
        folders = sorted(set(filter(None, (folder_of(p.get("cwd")) for p in tree))))
        sessions.append({
            "pid": session,
            "cwd": tilde(root.get("cwd") or "") or None,
            "folders": folders,
            "total_mb": sum(p["mem"] for p in tree),
            "claude_mb": root["mem"],
            "processes": len(tree),
            "cpu": round(sum(p["cpu"] for p in tree), 1),
            "children": sorted(children.values(), key=lambda c: -c["mem"])[:12],
        })
    return sorted(sessions, key=lambda s: -s["total_mb"])


def session_repeats(procs):
    """The same helper running once per session, which one shared or disabled copy would save."""
    seen = {}
    for proc in procs:
        if proc["session"] and proc["pid"] != proc["session"] and proc["kind"] in ("mcp", "server"):
            entry = seen.setdefault(proc["name"], {"name": proc["name"], "kind": proc["kind"], "sessions": set(), "mem": 0, "copies": 0})
            entry["sessions"].add(proc["session"])
            entry["mem"] += proc["mem"]
            entry["copies"] += 1
    repeats = [
        {"name": e["name"], "kind": e["kind"], "sessions": len(e["sessions"]), "copies": e["copies"], "mem": e["mem"]}
        for e in seen.values() if len(e["sessions"]) >= 2
    ]
    return sorted(repeats, key=lambda r: -r["mem"])


def history(directory):
    folder = os.path.join(directory, "samples")
    samples = []
    try:
        names = sorted(n for n in os.listdir(folder) if SAMPLE_FILE_RE.fullmatch(n))
    except OSError:
        return samples
    for name in names[-KEEP_SAMPLES:]:
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                sample = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(sample, dict) and isinstance(sample.get("procs"), list) and isinstance(sample.get("at"), int):
            samples.append(sample)
    return samples


def save_sample(sample, directory):
    folder = os.path.join(directory, "samples")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    os.chmod(folder, 0o700)
    stored = {
        "at": sample["at"],
        "machine": sample["machine"],
        "procs": [public(p) for p in sample["procs"] if p["mem"] >= STORE_MIN_MB or "orphaned" in p["flags"]],
    }
    path = os.path.join(folder, f"{sample['at']}.json")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(stored, handle)
    prune(folder, sample["at"])


def prune(folder, now):
    names = sorted(n for n in os.listdir(folder) if SAMPLE_FILE_RE.fullmatch(n))
    cutoff = now - KEEP_DAYS * 86400
    for index, name in enumerate(names):
        if index < len(names) - KEEP_SAMPLES or int(name.split(".")[0]) < cutoff:
            os.unlink(os.path.join(folder, name))


def growth(samples):
    """Sort processes by trend. A process is the same one only if its pid and start time both match."""
    series = {}
    for sample in samples:
        for proc in sample["procs"]:
            start = proc.get("start")
            if not isinstance(start, int):
                continue
            entries = series.setdefault(proc.get("pid"), [])
            # start is worked out from a one-second etime read a moment after `now`, so it jitters
            entry = next((e for e in entries if abs(e["start"] - start) <= START_JITTER_S), None)
            if entry is None:
                entry = {"start": start, "pid": proc.get("pid"), "name": proc.get("name"), "app": proc.get("app"), "session": proc.get("session"), "points": []}
                entries.append(entry)
            entry["points"].append((sample["at"], proc.get("mem", 0), proc.get("cpu", 0)))
    growing, steady = [], []
    for entry in (e for entries in series.values() for e in entries):
        points = sorted(entry["points"])
        if len(points) < GROW_MIN_POINTS or points[-1][0] - points[0][0] < GROW_MIN_SPAN_S:
            continue
        first, last = points[0][1], points[-1][1]
        span = points[-1][0] - points[0][0]
        steps = list(zip(points, points[1:]))
        rising = sum(1 for a, b in steps if b[1] >= a[1] * GROW_ALLOWED_DIP) / len(steps)
        cpu = sum(p[2] for p in points) / len(points)
        row = {
            "pid": entry["pid"],
            "start": entry["start"],
            "name": entry["name"],
            "app": entry["app"],
            "session": entry["session"],
            "first_mb": first,
            "last_mb": last,
            "points": len(points),
            "span_min": round(span / 60),
            "mb_per_hour": round((last - first) * 3600 / span),
            "cpu_avg": round(cpu, 1),
        }
        delta = last - first
        if delta >= GROW_MIN_MB and delta >= first * GROW_MIN_FRACTION and rising >= GROW_RISING_STEPS:
            row["class"] = "growing_idle" if cpu < IDLE_CPU_PCT else "growing_busy"
            growing.append(row)
        elif last >= LARGE_MB:
            row["class"] = "large_not_growing"
            steady.append(row)
    return {
        "growing": sorted(growing, key=lambda r: r["last_mb"] - r["first_mb"], reverse=True)[:12],
        "large_not_growing": sorted(steady, key=lambda r: -r["last_mb"])[:12],
    }


def extras(machine):
    out = {}
    code, text, _ = run("df", ["-k", "/"])
    rows = text.splitlines() if code == 0 else []
    if len(rows) >= 2:
        fields = rows[-1].split()
        out["disk_free_gb"] = round(int(fields[3]) / (1024 * 1024)) if len(fields) > 3 and fields[3].isdigit() else None

    if swap_too_full(swap_pct(machine)):
        out["sizes_note"] = f"swap is over {HIGH_SWAP_PCT}% full or unreadable, so folder sizes were skipped to avoid adding load"
    else:
        sizes = {}
        for path in DU_PATHS:
            full = os.path.expanduser(path)
            if os.path.isdir(full):
                sizes[path] = folder_size_mb(full)
        out["folder_sizes_mb"] = sizes

    out["worktrees"] = count_worktrees()

    caps = {}
    for key in ("IDEBuildOperationMaxNumberOfConcurrentCompileTasks", "PBXNumberOfParallelBuildSubtasks"):
        code, text, _ = run("defaults", ["read", "com.apple.dt.Xcode", key], timeout=5)
        caps[key] = text.strip() if code == 0 else None
    out["xcode_parallel_caps"] = caps

    log = os.path.expanduser("~/.claude/reap-stale-servers.log")
    try:
        with open(log, encoding="utf-8", errors="replace") as handle:
            lines = sum(1 for _ in handle)
        out["reap_log"] = {"lines": lines, "last_write": datetime.fromtimestamp(os.path.getmtime(log)).isoformat(timespec="minutes")}
    except OSError:
        out["reap_log"] = None
    return out


def folder_size_mb(path):
    # du exits 1 after a permission-denied subfolder but still prints the total it could read
    code, text, _ = run("du", ["-sk", path], timeout=8)
    fields = text.split()
    if fields and fields[0].isdigit():
        return round(int(fields[0]) / 1024)
    return "timed out" if code == 124 else "unreadable"


def count_worktrees():
    root = os.path.expanduser("~/repos")
    found = {}
    try:
        repos = os.listdir(root)
    except OSError:
        return found
    now = time.time()
    for repo in repos:
        folder = os.path.join(root, repo, ".claude", "worktrees")
        try:
            entries = [e for e in os.scandir(folder) if e.is_dir()]
        except OSError:
            continue
        if entries:
            oldest = min(e.stat().st_mtime for e in entries)
            found[repo] = {"count": len(entries), "oldest_days": round((now - oldest) / 86400)}
    return found


def build_summary(samples, directory, older, extra):
    latest = samples[-1]
    procs = latest["procs"]
    machine = dict(latest["machine"])
    machine["at"] = datetime.fromtimestamp(latest["at"]).isoformat(timespec="seconds")
    first_out, last_out = samples[0]["machine"].get("swapouts"), machine.get("swapouts")
    if first_out is not None and last_out is not None and len(samples) > 1:
        machine["swapouts_during_run"] = last_out - first_out
    machine.pop("swapouts", None)

    def app_key(proc):
        return "Claude Code sessions" if proc["session"] else proc["app"]

    def loose_folder(proc):
        return folder_of(proc.get("cwd")) if not proc["session"] and proc["mine"] and proc["app"] != "macOS" else None

    top_mem = sorted(procs, key=lambda p: -p["mem"])[:20]
    top_cpu = [p for p in sorted(procs, key=lambda p: -p["cpu"])[:8] if p["cpu"] >= 10]
    summary = {
        "ok": True,
        "samples": len(samples),
        "machine": machine,
        "apps": add_up(procs, app_key)[:15],
        "sessions": summarize_sessions(procs),
        "repeated_per_session": session_repeats(procs),
        "folders": add_up(procs, loose_folder)[:10],
        "orphans": [public(p) for p in procs if "orphaned" in p["flags"] or "worktree_gone" in p["flags"]],
        "launch_agents": [public(p) for p in sorted(procs, key=lambda p: -p["mem"]) if "launch_agent" in p["flags"]][:10],
        "long_running": [public(p) for p in sorted(procs, key=lambda p: -p["mem"]) if "long_running" in p["flags"]][:10],
        "top_memory": [public(p) for p in top_mem],
        "top_cpu": [public(p) for p in top_cpu],
        "growth": growth(older + [{"at": s["at"], "procs": [public(p) for p in s["procs"]]} for s in samples]),
        "history_samples": len(older),
        "data_dir": tilde(directory),
    }
    if extra is not None:
        summary["extras"] = extra
    return summary


def cmd_sample(options):
    if not 1 <= options.samples <= MAX_SAMPLES:
        raise Refused(f"--samples must be 1 to {MAX_SAMPLES}")
    if not MIN_INTERVAL <= options.interval <= MAX_INTERVAL:
        raise Refused(f"--interval must be {MIN_INTERVAL} to {MAX_INTERVAL} seconds")
    if options.samples * options.interval > MAX_RUN_SECONDS:
        raise Refused(f"--samples x --interval must stay within {MAX_RUN_SECONDS} seconds")
    directory = data_dir()
    os.makedirs(directory, mode=0o700, exist_ok=True)
    older = history(directory)
    cache = {}
    samples = []
    for index in range(options.samples):
        if index:
            time.sleep(options.interval)
        sample = take_sample(cache)
        save_sample(sample, directory)
        samples.append(sample)
    extra = extras(samples[-1]["machine"]) if options.extras else None
    return build_summary(samples, directory, older, extra)


def parse_footprint(text):
    out: dict = {"tool": "footprint"}
    total = re.search(r"Footprint: ([\d.]+ \w+)", text)
    if total:
        out["footprint_mb"] = round(size_mb(total.group(1)))
    peak = re.search(r"phys_footprint_peak: ([\d.]+ \w+)", text)
    if peak:
        out["peak_mb"] = round(size_mb(peak.group(1)))
    regions = []
    for line in text.splitlines():
        row = re.match(r"^\s*([\d.]+ \w+)\s+[\d.]+ \w+\s+[\d.]+ \w+\s+\d+\s+(.+?)\s*$", line)
        if row and row.group(2) != "TOTAL":
            regions.append({"category": row.group(2), "dirty_mb": round(size_mb(row.group(1)), 1)})
    out["categories"] = sorted(regions, key=lambda r: -r["dirty_mb"])[:6]
    return out


def parse_vmmap(text):
    out: dict = {"tool": "vmmap"}
    total = re.search(r"^Physical footprint:\s+(\S+)", text, re.MULTILINE)
    peak = re.search(r"^Physical footprint \(peak\):\s+(\S+)", text, re.MULTILINE)
    if total:
        out["footprint_mb"] = round(size_mb(total.group(1)))
    if peak:
        out["peak_mb"] = round(size_mb(peak.group(1)))
    regions = []
    for line in text.split("REGION TYPE", 1)[-1].splitlines():
        row = re.match(r"^(\S.*?)\s+(\S+[BKMGT])\s+(\S+[BKMGT])\s+(\S+[BKMGT])\s+(\S+[BKMGT])\s+\S+\s+\S+\s+\S+\s+\d+\s*$", line)
        if row and not row.group(1).startswith("TOTAL"):
            dirty = size_mb(row.group(4)) + size_mb(row.group(5))
            if dirty:
                regions.append({"region": row.group(1), "dirty_plus_swapped_mb": round(dirty, 1)})
        elif row:
            break
    out["regions"] = sorted(regions, key=lambda r: -r["dirty_plus_swapped_mb"])[:6]
    return out


def parse_leaks(text):
    row = re.search(r"(\d+) leaks? for (\d+) total leaked bytes", text)
    if not row:
        return {"tool": "leaks", "leaks": None}
    return {"tool": "leaks", "leaks": int(row.group(1)), "leaked_mb": round(int(row.group(2)) / MB, 1)}


def parse_heap(text):
    row = re.search(r"All zones: (\d+) nodes \((\d+) bytes\)", text)
    if not row:
        return {"tool": "heap", "nodes": None}
    return {"tool": "heap", "nodes": int(row.group(1)), "allocated_mb": round(int(row.group(2)) / MB, 1)}


INSPECT_TOOLS = {
    "footprint": {"flags": ["-p"], "timeout": 15, "parse": parse_footprint, "figure": "footprint_mb"},
    "vmmap": {"flags": ["--summary"], "timeout": 20, "parse": parse_vmmap, "figure": "footprint_mb"},
    "heap": {"flags": ["--quiet"], "timeout": 60, "parse": parse_heap, "figure": "nodes"},
    "leaks": {"flags": ["--quiet"], "timeout": 60, "parse": parse_leaks, "figure": "leaks"},
}


def cmd_inspect(options):
    name, pid = options.tool, options.pid
    tool = INSPECT_TOOLS[name]
    if pid <= 1:
        raise Refused("--pid must be a process number above 1")
    if name in TOOLS_NEEDING_APPROVAL and not options.approved:
        raise Refused(f"{name} pauses the process and can pull swapped memory back in, so it needs the owner's OK for this process, then --approved")
    if name in TOOLS_NEEDING_APPROVAL and options.start is None:
        raise Refused(f"{name} needs --start, the start time from the sample, to be sure this is the process the owner approved")
    code, out, _ = run("ps", ["-o", "uid=,state=,etime=", "-p", str(pid)])
    fields = out.split()
    if code != 0 or len(fields) < 3:
        raise Refused(f"process {pid} isn't running")
    if int(fields[0]) != os.getuid():
        raise Refused(f"process {pid} belongs to another user, and inspecting it would need root")
    if options.start is not None and abs(time.time() - parse_etime(fields[2]) - options.start) > START_JITTER_S:
        raise Refused(f"process {pid} started at a different time, so it's a different process using the same number")
    if name == "vmmap":
        pct = swap_pct(take_machine())
        if swap_too_full(pct):
            raise Refused(f"swap is {'unreadable' if pct is None else f'{pct}% full'}; vmmap could add to the problem, so try again when swap is at or below {HIGH_SWAP_PCT}%")
    code, text, err = run(name, tool["flags"] + [str(pid)], timeout=tool["timeout"])
    result = tool["parse"](text)
    result["pid"] = pid
    # Checked before any failure too: a tool that timed out is the likeliest to leave a process paused
    _, state, _ = run("ps", ["-o", "state=", "-p", str(pid)])
    paused = f"process {pid} is still paused after {name}; tell the owner" if state.strip().startswith("T") else None
    # `leaks` exits 1 when it finds leaks, so only a missing figure counts as failure
    if result.get(tool["figure"]) is None:
        message = (err.strip().splitlines() or [f"exit code {code}"])[0]
        failure = f"{name} couldn't read process {pid}, so this is unknown rather than clean: {tilde(message)[:200]}"
        raise Refused(f"{failure}. {paused}" if paused else failure)
    if paused:
        result["warning"] = paused
    result["ok"] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Mac memory sampler")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample")
    sample.add_argument("--samples", type=int, default=1)
    sample.add_argument("--interval", type=int, default=60)
    sample.add_argument("--extras", action="store_true")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--tool", choices=sorted(INSPECT_TOOLS), required=True)
    inspect.add_argument("--pid", type=int, required=True)
    inspect.add_argument("--start", type=int)
    inspect.add_argument("--approved", action="store_true")
    options = parser.parse_args(argv)
    try:
        result = cmd_sample(options) if options.command == "sample" else cmd_inspect(options)
    except Refused as err:
        print(json.dumps({"ok": False, "error": str(err)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
