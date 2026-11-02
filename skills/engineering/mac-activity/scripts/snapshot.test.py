#!/usr/bin/env python3
"""Self-tests for snapshot.py. Canned command output only, so they run anywhere.

Run: python3 -B skills/engineering/mac-activity/scripts/snapshot.test.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snapshot  # noqa: E402

ME = os.getuid()
HOME = os.path.expanduser("~")
CLAUDE = f"{HOME}/Library/Application Support/Claude/claude-code/2.1/x/claude.app/Contents/MacOS/claude"
GONE = "/tmp/no-such-repo/.claude/worktrees/agent-1"

TOP = """Processes: 5 total
Load Avg: 1.00, 2.00, 3.00
PhysMem: 1M used (1M wired, 1M compressor), 1M unused.
PID PPID COMMAND MEM CMPRS %CPU
100 1 stale 999M 0B 0.0
Processes: 9 total, 3 running
Load Avg: 42.94, 74.91, 53.05
PhysMem: 7308M used (1739M wired, 1949M compressor), 328M unused.
VM: 289T vsize, 57G framework vsize, 474564(0) swapins, 741937(0) swapouts.
PID    PPID  COMMAND          MEM   CMPRS %CPU
100    1     Claude Helper (R 909M+ 366M- 1.5
200    1     claude           468M  223M  12.0
201    200   node             322M  295M  0.0
202    200   npm exec rea-age 12M   10M   0.0
203    200   bash             2048K 0B    55.5
300    1     claude           299M  198M  0.0
301    300   node             239M  217M  0.0
400    1     node             77M   10M   0.0
500    1     firefox          1.5G  485M  3.0
600    1     node             80M   1M    0.0
700    1     kernel_task      3M    0B    30.0
"""
PS = f"""  100 1 {ME} 03:25:59 /Applications/Claude.app/Contents/Frameworks/Claude Helper (Renderer).app/Contents/MacOS/Claude Helper (Renderer)
  200 1 {ME} 01:49:43 {CLAUDE}
  201 200 {ME} 01-02:03:04 /opt/homebrew/bin/node
  202 200 {ME} 00:10 /opt/homebrew/bin/npm
  203 200 {ME} 00:05 /bin/bash
  300 1 {ME} 03:24:55 {CLAUDE}
  301 300 {ME} 03:24:55 /opt/homebrew/bin/node
  400 1 {ME} 09:00:00 /opt/homebrew/bin/node
  500 1 {ME} 02:00:00 /Applications/Firefox.app/Contents/MacOS/firefox
  600 1 {ME} 09:00:00 /opt/homebrew/bin/node
  700 0 0 09:00:00 /kernel_task
"""
ARGS = f"""  100 /Applications/Claude.app/Contents/Frameworks/Claude Helper (Renderer).app/Contents/MacOS/Claude Helper (Renderer) --type=renderer
  200 {CLAUDE} --resume=abc --api-token=SECRETVALUE
  201 /opt/homebrew/bin/node {HOME}/.npm/_npx/a1/node_modules/.bin/rea mcp --password=SECRETVALUE
  202 /opt/homebrew/bin/npm exec rea-agents@6.7.0 mcp
  203 /bin/bash -c export TOKEN=SECRETVALUE; run.sh
  300 {CLAUDE} --resume=def
  301 /opt/homebrew/bin/node {HOME}/.npm/_npx/a1/node_modules/.bin/rea mcp
  400 /opt/homebrew/bin/node {GONE}/server.js
  500 /Applications/Firefox.app/Contents/MacOS/firefox
  600 /opt/homebrew/bin/node {HOME}/agent/index.js
  700 /kernel_task
"""
LSOF = f"p200\nfcwd\nn{HOME}/repos/sideload\np201\nfcwd\nn{HOME}/repos/sideload/.claude/worktrees/w1\np300\nfcwd\nn{HOME}/repos/reddit\np400\nfcwd\nn{GONE}\n"
LAUNCH = "PID\tStatus\tLabel\n-\t0\tcom.apple.idle\n600\t0\tcom.example.agent\n"
SWAP = "total = 4096.00M  used = 3712.50M  free = 383.50M  (encrypted)"
FOOTPRINT = """claude [47569]: 64-bit    Footprint: 224 MB (16384 bytes per page)

  Dirty      Clean  Reclaimable    Regions    Category
    ---        ---          ---        ---    ---
 189 MB        0 B      2080 KB         12    App-Specific Tag 1
8144 KB        0 B          0 B         32    Malloc Small
    ---        ---          ---        ---    ---
 224 MB        0 B      2080 KB       1000    TOTAL
    phys_footprint: 224 MB
    phys_footprint_peak: 245 MB
"""
VMMAP = """Physical footprint:         224.2M
Physical footprint (peak):  245.5M
REGION TYPE                        SIZE     SIZE     SIZE     SIZE     SIZE     SIZE     SIZE    COUNT (non-coalesced)
===========                     ======= ========    =====  ======= ========   ======    =====  =======
App-Specific Tag 1               516.4M   128.9M   127.0M    62.5M       0K       0K       0K        8
Malloc Small                      35.9M     784K     784K    3200K       0K       0K       0K       14
TOTAL                            392.6G   349.5M   127.9M    96.4M       0K      32K       0K     1996
"""


class FakeCommands:
    def __init__(self, swap=SWAP):
        self.swap = swap
        self.state = "S"
        self.calls = []
        self.overrides = {}

    def __call__(self, cmd, args, timeout=10):
        self.calls.append((cmd, args))
        if cmd in self.overrides:
            return self.overrides[cmd]
        if cmd == "sysctl":
            if "vm.swapusage" in args:
                return 0, f"{self.swap}\n{{ 1 2 3 }}\n8589934592\n8\n", ""
            return 0, "2\n", ""
        if cmd == "top":
            return 0, TOP, ""
        if cmd == "ps" and "-axo" in args:
            return 0, PS, ""
        if cmd == "ps" and "-axww" in args:
            return 0, ARGS, ""
        if cmd == "ps":
            return 0, f"{ME} {self.state} 00:10\n" if "uid=,state=,etime=" in args else f"{self.state}\n", ""
        if cmd == "lsof":
            return 0, LSOF, ""
        if cmd == "launchctl":
            return 0, LAUNCH, ""
        if cmd == "df":
            return 0, "Filesystem 1K Used Avail\n/dev/x 1 1 31457280\n", ""
        if cmd == "footprint":
            return 0, FOOTPRINT, ""
        if cmd == "vmmap":
            return 0, VMMAP, ""
        if cmd == "leaks":
            return 1, "Process 5: 3 leaks for 2097152 total leaked bytes.\n", ""
        if cmd == "heap":
            return 0, "All zones: 9559 nodes (1936688 bytes)\n", ""
        return 1, "", "not faked"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["MAC_ACTIVITY_DIR"] = self.tmp.name
        self.addCleanup(os.environ.pop, "MAC_ACTIVITY_DIR", None)
        self.fake = FakeCommands()
        original = snapshot.run
        snapshot.run = self.fake
        self.addCleanup(setattr, snapshot, "run", original)

    def invoke(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = snapshot.main(list(argv))
        return code, json.loads(buffer.getvalue()), buffer.getvalue()


class Parsing(unittest.TestCase):
    def test_top_uses_the_last_block_and_handles_spaces_and_suffixes(self):
        header, procs = snapshot.parse_top(TOP)
        self.assertEqual(procs[100], {"mem": 909, "cmprs": 366, "cpu": 1.5})
        self.assertEqual(procs[203]["mem"], 2)
        self.assertEqual(procs[500]["mem"], 1536)
        self.assertEqual(header["load"], [42.94, 74.91, 53.05])
        self.assertEqual(header["compressor_mb"], 1949)
        self.assertEqual(header["swapouts"], 741937)

    def test_elapsed_time_forms(self):
        self.assertEqual(snapshot.parse_etime("00:13"), 13)
        self.assertEqual(snapshot.parse_etime("03:25:59"), 12359)
        self.assertEqual(snapshot.parse_etime("01-09:36:29"), 120989)

    def test_names_and_kinds(self):
        node = "/opt/homebrew/bin/node"
        cases = [
            (node, f"{node} /x/node_modules/.bin/rea mcp", "rea", "mcp"),
            ("/opt/homebrew/bin/npm", "/opt/homebrew/bin/npm exec rea-agents@6.7.0 mcp", "rea-agents", "mcp"),
            ("npm exec rea-agents@6.7.0 mcp", "npm exec rea-agents@6.7.0 mcp", "rea-agents", "mcp"),
            (node, f"{node} /opt/lib/node_modules/typescript/lib/tsserver.js --x", "tsserver", "server"),
            (node, f"{node} /x/node_modules/@scope/pkg/index.js", "@scope/pkg", "other"),
            (node, f"{node} --max-old-space-size=9 /x/app.js", "app", "other"),
            ("/usr/bin/clang", "/usr/bin/clang -c a.c", "clang", "build"),
            ("/bin/bash", "/bin/bash repro.sh", "bash", "shell"),
            (node, f"{node} /x/node_modules/.bin/tsc --watch", "tsc", "server"),
            (node, f"{node} /x/node_modules/.bin/jest --watchAll", "jest", "server"),
            (f"{HOME}/.local/share/claude/versions/2.1.309", f"{HOME}/.local/share/claude/versions/2.1.309 -p hi", "claude", "claude"),
            (CLAUDE, f"{CLAUDE} --resume=1", "claude", "claude"),
        ]
        for comm, args, name, kind in cases:
            self.assertEqual(snapshot.name_and_kind(comm, args), (name, kind), args)

    def test_a_flag_value_is_never_taken_for_a_name(self):
        node = "/opt/homebrew/bin/node"
        python = "/usr/bin/python3"
        npx = "/opt/homebrew/bin/npx"
        cases = [
            (node, f"{node} --token abc app.js", "node"),
            (node, f"{node} --token abc", "node"),
            (node, f"{node} --token abc/def", "node"),
            (node, f"{node} -pe process.env.T='a/b'", "node"),
            (node, f"{node} --require ./hook.js server.js", "node"),
            (node, f"{node} https://h/x?token=abc", "node"),
            (node, f"{node} --no-warnings --inspect /x/app.js", "app"),
            (python, f"{python} -u /x/tool.py", "tool"),
            (npx, f"{npx} --registry abc pkg", "npx"),
            (npx, f"{npx} -y pkg@1.2", "pkg"),
            (python, f"{python} -c print('/a/b')", "python3"),
            (python, f"{python} -m http.server", "http.server"),
            ("npm exec --token abc", "npm exec --token abc", "npm"),
            ("npm exec --token a/b", "npm exec --token a/b", "npm"),
            ("npm exec --registry https://h/x?token=abc", "npm exec --registry https://h/x?token=abc", "npm"),
            ("/opt/homebrew/bin/node --token a/b", "/opt/homebrew/bin/node --token a/b", "node"),
        ]
        for comm, args, name in cases:
            self.assertEqual(snapshot.name_and_kind(comm, args)[0], name, args)
        self.assertEqual(snapshot.app_of("npm exec --token a/b"), "npm")
        self.assertEqual(snapshot.app_of("/opt/homebrew/bin/node --token a/b"), "node")

    def test_apps(self):
        self.assertEqual(snapshot.app_of("/Applications/Xcode.app/Contents/Developer/usr/bin/clang"), "Xcode")
        self.assertEqual(snapshot.app_of(CLAUDE), "Claude Code sessions")
        self.assertEqual(snapshot.app_of("/private/var/run/x/com.apple.SimulatorRuntime/SpringBoard.app/SpringBoard"), "iOS Simulator")
        self.assertEqual(snapshot.app_of("/usr/libexec/trustd"), "macOS")

    def test_folders(self):
        self.assertEqual(snapshot.folder_of(f"{HOME}/repos/a/src"), "~/repos/a")
        self.assertEqual(snapshot.folder_of(f"{HOME}/repos/a/.claude/worktrees/w/src"), "~/repos/a [worktree w]")
        self.assertIsNone(snapshot.folder_of(HOME))
        self.assertIsNone(snapshot.folder_of("/"))

    def test_worktree_gone_reads_absolute_paths_and_ignores_shell_scripts(self):
        self.assertTrue(snapshot.worktree_gone(f"node {GONE}/x.js", None, "other"))
        self.assertTrue(snapshot.worktree_gone("node", GONE, "other"))
        self.assertFalse(snapshot.worktree_gone(f"zsh -c cd {GONE}", None, "shell"))
        self.assertFalse(snapshot.worktree_gone("node ~/repos/a/.claude/worktrees/b/x.js", None, "other"))
        self.assertFalse(snapshot.worktree_gone("node", None, "other"))

    def test_system_wide_services_started_by_launchd_are_not_orphans(self):
        proc = {"pid": 9, "ppid": 1, "mine": True, "kind": "other", "cwd": None, "age_s": 0, "mem": 1}
        self.assertEqual(snapshot.process_flags(proc, "/Library/Developer/PrivateFrameworks/Sim", "", {}), [])
        self.assertEqual(snapshot.process_flags(proc, "/opt/homebrew/bin/node", "", {}), ["orphaned"])
        self.assertEqual(snapshot.process_flags(proc, "/Applications/Foo.app/Contents/MacOS/Foo", "", {9: "application.foo"}), [])

    def test_inspect_parsers(self):
        footprint = snapshot.parse_footprint(FOOTPRINT)
        self.assertEqual(footprint["footprint_mb"], 224)
        self.assertEqual(footprint["peak_mb"], 245)
        self.assertEqual([c["category"] for c in footprint["categories"]], ["App-Specific Tag 1", "Malloc Small"])
        vmmap = snapshot.parse_vmmap(VMMAP)
        self.assertEqual(vmmap["peak_mb"], 246)
        self.assertEqual(vmmap["regions"][0]["region"], "App-Specific Tag 1")
        self.assertNotIn("TOTAL", [r["region"] for r in vmmap["regions"]])


class Growth(unittest.TestCase):
    def sample(self, at, mem, cpu=0.0, pid=1, start=1000):
        return {"at": at, "procs": [{"pid": pid, "start": start, "name": "x", "app": "x", "mem": mem, "cpu": cpu}]}

    def test_steady_rise_while_idle(self):
        samples = [self.sample(1000 + i * 600, 400 + i * 40) for i in range(4)]
        row = snapshot.growth(samples)["growing"][0]
        self.assertEqual(row["class"], "growing_idle")
        self.assertEqual(row["mb_per_hour"], 240)

    def test_busy_process_is_not_called_idle(self):
        samples = [self.sample(1000 + i * 600, 400 + i * 40, cpu=50) for i in range(4)]
        self.assertEqual(snapshot.growth(samples)["growing"][0]["class"], "growing_busy")

    def test_large_and_flat_is_not_growth(self):
        result = snapshot.growth([self.sample(1000 + i * 600, 900) for i in range(4)])
        self.assertEqual(result["growing"], [])
        self.assertEqual(result["large_not_growing"][0]["class"], "large_not_growing")

    def test_a_sawtooth_is_not_growth(self):
        memory = [400, 900, 450, 950, 500]
        result = snapshot.growth([self.sample(1000 + i * 600, m) for i, m in enumerate(memory)])
        self.assertEqual(result["growing"], [])

    def test_too_few_points_or_too_short_says_nothing(self):
        self.assertEqual(snapshot.growth([self.sample(1000, 100), self.sample(1600, 900)])["growing"], [])
        self.assertEqual(snapshot.growth([self.sample(1000 + i * 30, 100 + i * 300) for i in range(4)])["growing"], [])

    def test_start_time_jitter_is_still_the_same_process(self):
        samples = [self.sample(1000 + i * 600, 400 + i * 40, start=1004 + i) for i in range(4)]
        self.assertEqual(len(snapshot.growth(samples)["growing"]), 1)

    def test_a_reused_pid_is_a_different_process(self):
        samples = [self.sample(1000, 100), self.sample(1600, 200), self.sample(2200, 300, start=2100), self.sample(2800, 400, start=2100)]
        self.assertEqual(snapshot.growth(samples)["growing"], [])


class Sample(Base):
    def test_groups_sessions_and_flags(self):
        code, result, _ = self.invoke("sample")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        machine = result["machine"]
        self.assertEqual(machine["swap_pct"], 91)
        self.assertEqual(machine["pressure"], "warning")

        sessions = {s["pid"]: s for s in result["sessions"]}
        self.assertEqual(set(sessions), {200, 300})
        self.assertEqual(sessions[200]["total_mb"], 468 + 322 + 12 + 2)
        self.assertEqual(sessions[200]["cwd"], "~/repos/sideload")
        self.assertIn("~/repos/sideload [worktree w1]", sessions[200]["folders"])
        self.assertEqual(sessions[200]["children"][0]["name"], "rea")

        repeats = {r["name"]: r for r in result["repeated_per_session"]}
        self.assertEqual(repeats["rea"]["sessions"], 2)
        self.assertEqual(repeats["rea"]["mem"], 322 + 239)

        apps = {a["name"]: a for a in result["apps"]}
        self.assertEqual(apps["Claude"]["mem"], 909)
        self.assertEqual(apps["Firefox"]["mem"], 1536)
        self.assertEqual(apps["Claude Code sessions"]["count"], 6)

        orphans = {p["pid"]: p for p in result["orphans"]}
        self.assertEqual(set(orphans), {201, 400})
        self.assertEqual(sorted(orphans[400]["flags"]), ["long_running", "orphaned", "worktree_gone"])
        self.assertNotIn("orphaned", orphans[201]["flags"])
        self.assertEqual([p["pid"] for p in result["launch_agents"]], [600])
        self.assertEqual(result["launch_agents"][0]["launch_label"], "com.example.agent")
        self.assertNotIn("launch_agent", snapshot.process_flags(
            {"pid": 9, "ppid": 1, "mine": True, "kind": "other", "cwd": None, "age_s": 0, "mem": 1},
            "/Applications/Foo.app/Contents/MacOS/Foo", "", {9: "application.foo"},
        ))
        self.assertEqual([p["pid"] for p in result["top_cpu"]], [203, 700, 200])

    def test_command_lines_are_never_printed_or_saved(self):
        _, _, printed = self.invoke("sample", "--extras")
        self.assertNotIn("SECRETVALUE", printed)
        self.assertNotIn("--resume", printed)
        for path in Path(self.tmp.name).rglob("*.json"):
            self.assertNotIn("SECRETVALUE", path.read_text())

    def test_saved_samples_are_private(self):
        self.invoke("sample")
        folder = Path(self.tmp.name) / "samples"
        self.assertEqual(oct(folder.stat().st_mode & 0o777), "0o700")
        for path in folder.iterdir():
            self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600")

    def test_later_runs_read_saved_samples(self):
        self.invoke("sample")
        _, second, _ = self.invoke("sample")
        self.assertEqual(second["history_samples"], 1)

    def test_a_malformed_saved_sample_is_skipped(self):
        self.invoke("sample")
        folder = Path(self.tmp.name) / "samples"
        (folder / "1.json").write_text("{not json")
        (folder / "2.json").write_text('{"at": "soon", "procs": 3}')
        code, result, _ = self.invoke("sample")
        self.assertEqual(code, 0)
        self.assertEqual(result["history_samples"], 1)

    def test_old_samples_are_pruned(self):
        folder = Path(self.tmp.name) / "samples"
        folder.mkdir()
        (folder / "1000.json").write_text("{}")
        self.invoke("sample")
        self.assertFalse((folder / "1000.json").exists())

    def test_extras_skip_folder_sizes_when_swap_is_high(self):
        _, result, _ = self.invoke("sample", "--extras")
        self.assertIn("sizes_note", result["extras"])
        self.assertNotIn("du", [c for c, _ in self.fake.calls])
        self.assertEqual(result["extras"]["disk_free_gb"], 30)

    def test_folder_sizes_keep_the_total_after_a_permission_error(self):
        self.fake.overrides["du"] = (1, "2048\t/x\n", "du: /x/y: Permission denied")
        self.assertEqual(snapshot.folder_size_mb("/x"), 2)
        self.fake.overrides["du"] = (124, "", "du timed out")
        self.assertEqual(snapshot.folder_size_mb("/x"), "timed out")
        self.fake.overrides["du"] = (1, "", "no such folder")
        self.assertEqual(snapshot.folder_size_mb("/x"), "unreadable")

    def test_commands_are_only_the_read_only_ones(self):
        self.invoke("sample", "--extras")
        used = {cmd for cmd, _ in self.fake.calls}
        self.assertLessEqual(used, {"sysctl", "top", "ps", "lsof", "launchctl", "df", "du", "defaults"})
        for cmd, args in self.fake.calls:
            if cmd == "defaults":
                self.assertEqual(args[0], "read")

    def test_bounds_are_refused(self):
        for argv in (["--samples", "0"], ["--samples", "11"], ["--interval", "5"], ["--interval", "301"], ["--samples", "10", "--interval", "100"]):
            code, result, _ = self.invoke("sample", *argv)
            self.assertEqual(code, 1, argv)
            self.assertFalse(result["ok"])
        self.assertEqual(self.fake.calls, [])

    def test_a_failed_top_is_an_error_not_an_empty_report(self):
        self.fake.overrides["top"] = (1, "", "no top here")
        code, result, _ = self.invoke("sample")
        self.assertEqual(code, 1)
        self.assertIn("no top here", result["error"])


class Inspect(Base):
    def test_footprint_runs_without_approval(self):
        code, result, _ = self.invoke("inspect", "--tool", "footprint", "--pid", "5")
        self.assertEqual(code, 0)
        self.assertEqual(result["footprint_mb"], 224)

    def test_leaks_and_heap_need_approval_and_do_not_run_without_it(self):
        for tool in ("leaks", "heap"):
            code, result, _ = self.invoke("inspect", "--tool", tool, "--pid", "5")
            self.assertEqual(code, 1)
            self.assertIn("owner", result["error"])
            self.assertNotIn(tool, [c for c, _ in self.fake.calls])

    def approved(self, tool="leaks"):
        return self.invoke("inspect", "--tool", tool, "--pid", "5", "--approved", "--start", str(int(time.time()) - 10))

    def test_approved_tools_need_the_start_time(self):
        code, result, _ = self.invoke("inspect", "--tool", "leaks", "--pid", "5", "--approved")
        self.assertEqual(code, 1)
        self.assertIn("--start", result["error"])
        self.assertNotIn("leaks", [c for c, _ in self.fake.calls])

    def test_a_reused_pid_is_refused(self):
        code, result, _ = self.invoke("inspect", "--tool", "leaks", "--pid", "5", "--approved", "--start", "1000")
        self.assertEqual(code, 1)
        self.assertIn("different process", result["error"])
        self.assertNotIn("leaks", [c for c, _ in self.fake.calls])

    def test_approved_leaks_counts_exit_one_as_a_result(self):
        code, result, _ = self.approved()
        self.assertEqual(code, 0)
        self.assertEqual(result["leaks"], 3)
        self.assertEqual(result["leaked_mb"], 2.0)

    def test_vmmap_is_refused_when_swap_is_high(self):
        code, result, _ = self.invoke("inspect", "--tool", "vmmap", "--pid", "5")
        self.assertEqual(code, 1)
        self.assertIn("swap", result["error"])
        self.assertNotIn("vmmap", [c for c, _ in self.fake.calls])

    def test_vmmap_is_refused_when_swap_is_unreadable(self):
        self.fake.overrides["sysctl"] = (1, "", "")
        code, result, _ = self.invoke("inspect", "--tool", "vmmap", "--pid", "5")
        self.assertEqual(code, 1)
        self.assertIn("unreadable", result["error"])

    def test_vmmap_runs_on_a_mac_that_has_not_swapped_yet(self):
        self.fake.swap = "total = 0.00M  used = 0.00M  free = 0.00M"
        code, _, _ = self.invoke("inspect", "--tool", "vmmap", "--pid", "5")
        self.assertEqual(code, 0)

    def test_a_paused_process_is_reported_even_when_the_tool_failed(self):
        self.fake.overrides["leaks"] = (124, "", "leaks timed out after 60s")
        self.fake.state = "T"
        code, result, _ = self.approved()
        self.assertEqual(code, 1)
        self.assertIn("still paused", result["error"])

    def test_a_paused_process_is_reported_after_a_good_result(self):
        self.fake.state = "T"
        code, result, _ = self.approved()
        self.assertEqual(code, 0)
        self.assertIn("still paused", result["warning"])

    def test_vmmap_runs_when_swap_has_room(self):
        self.fake.swap = "total = 4096.00M  used = 100.00M  free = 3996.00M"
        code, result, _ = self.invoke("inspect", "--tool", "vmmap", "--pid", "5")
        self.assertEqual(code, 0)
        self.assertEqual(result["footprint_mb"], 224)

    def test_another_users_process_is_refused(self):
        self.fake.overrides["ps"] = (0, f"{ME + 1} S 00:10\n", "")
        code, result, _ = self.invoke("inspect", "--tool", "footprint", "--pid", "5")
        self.assertEqual(code, 1)
        self.assertIn("root", result["error"])

    def test_missing_process_and_bad_pid_are_refused(self):
        self.fake.overrides["ps"] = (1, "", "")
        code, result, _ = self.invoke("inspect", "--tool", "footprint", "--pid", "5")
        self.assertEqual(code, 1)
        self.assertIn("isn't running", result["error"])
        code, _, _ = self.invoke("inspect", "--tool", "footprint", "--pid", "1")
        self.assertEqual(code, 1)

    def test_a_tool_that_cannot_read_is_unknown_not_clean(self):
        self.fake.overrides["leaks"] = (1, "", "cannot examine process: not permitted")
        code, result, _ = self.approved()
        self.assertEqual(code, 1)
        self.assertIn("unknown rather than clean", result["error"])


if __name__ == "__main__":
    unittest.main()
