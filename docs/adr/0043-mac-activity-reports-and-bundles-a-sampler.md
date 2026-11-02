# Mac-activity reports and asks, and bundles a sampler

> **Status: Accepted** — maintainer decision (2026-11-01).

## Context

An 8 GB Mac running several Claude Code sessions kept running out of memory. The
worst incident reached a load average of about 417 with most of its swap in use. A
diagnosis by hand found the causes, and asking the sessions directly got one to stop
a heavy script.

That diagnosis taught four things:

- A session's "nothing else is planned" went stale within minutes.
- A successful cross-session send doesn't mean the session has read the message.
- `ps` RSS leaves out compressed and swapped memory. In one sample it showed about
  175 MB for a process whose footprint in `top` was 909 MB.
- Composing the sampling commands by hand is easy to get wrong.

## Decision

`/mac-activity` is a user-invoked skill that measures, asks and reports. It stops
nothing without the owner's OK for that item, and a session's reply is information,
never approval.

It bundles one stdlib Python script, `scripts/snapshot.py`, and is the first skill here
with code since the Python harness left the published surface. Joining `top`, `ps`,
`lsof` and `launchctl`, grouping by session and comparing samples is deterministic
work. Done by the model each time, it would cost more tokens and more mistakes, and it
is the wrong place to add load on a Mac already short of memory. The script also keeps
the safety bounds in one tested place: sample limits, timeouts, command lines that are
never stored, and refusing `vmmap` at high swap and `leaks` or `heap` without approval.

## Consequences

- The script's self-test runs in the `gate` workflow, which now also covers
  `skills/**/*.test.py`.
- Samples stay in a private local folder, so each run strengthens the next run's growth
  trend without any extra sampling. There is no always-on sampler. If the saved trend
  proves too sparse to catch leaks, one can be added as a separate decision.
- The skill is macOS-only, while the self-test uses canned output and runs anywhere.
- It reports what the `reap-stale-servers` hook in `claude-config` can't reach rather
  than duplicating it.
- This repo is public, so the skill text stays generic and holds no machine's data.
