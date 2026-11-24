#!/usr/bin/env node
// repo-audit UI probe: measures one screen state at one width and theme and
// prints one JSON cell. Method, install and schema: probe.md. Nothing here is
// installed in the audited repo: Playwright and axe-core come from the scratch
// install named by --modules or PROBE_MODULES.
//
// Page code only COLLECTS raw data; every judgement is a pure helper below,
// unit-tested in probe.test.mjs without a browser.
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const { pathToFileURL } = require("node:url");

const CAP = 20;
const ABBREVIATIONS = new Set(
  "e.g i.e etc vs mr mrs ms dr prof st approx fig cf inc ltd".split(" "),
);
const NAMED = { white: "#ffffff", black: "#000000" };

const hex2 = (n) => Math.round(n).toString(16).padStart(2, "0");
const round1 = (n) => Math.round(n * 10) / 10;

// ---------- pure helpers (exported, tested) ----------

function countWords(text) {
  return text.split(/\s+/).filter((t) => /[\p{L}\p{N}]/u.test(t)).length;
}

// Splits on . ? ! followed by whitespace or the end. A dot inside a decimal
// ("3.5") has no whitespace after it, and common abbreviations do not end a
// sentence.
function splitSentences(text) {
  const out = [];
  let start = 0;
  const re = /[.!?]+["')\]]*(?=\s|$)/g;
  let m;
  while ((m = re.exec(text))) {
    const before = text.slice(start, m.index).split(/\s+/).pop().toLowerCase();
    const stem = before.replace(/^[("'[]+/, "");
    if (m[0][0] === "." && (ABBREVIATIONS.has(stem) || /^[a-z]$/.test(stem))) {
      continue;
    }
    out.push(text.slice(start, m.index + m[0].length).trim());
    start = m.index + m[0].length;
  }
  if (text.slice(start).trim()) out.push(text.slice(start).trim());
  return out.filter((s) => countWords(s) > 0);
}

function copyMetrics(blocks, longAt = 25) {
  const counts = blocks.map(countWords);
  const sentences = blocks.flatMap(splitSentences).map(countWords);
  const total = sentences.reduce((a, b) => a + b, 0);
  return {
    visibleWords: counts.reduce((a, b) => a + b, 0),
    longestBlockWords: counts.length ? Math.max(...counts) : 0,
    longSentences: sentences.filter((n) => n > longAt).length,
    meanSentenceWords: sentences.length ? round1(total / sentences.length) : 0,
  };
}

// Scripts written without spaces between words: a space-delimited word or
// sentence count means nothing for them. Hangul is space-delimited, so it is
// not listed.
const UNSPACED =
  /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Thai}\p{Script=Lao}\p{Script=Khmer}\p{Script=Myanmar}]/gu;

// False when more than half the letters on the screen are in an unspaced
// script; the word and sentence thresholds do not apply to that text.
function isSpaceDelimited(text) {
  const letters = (text.match(/\p{L}/gu) ?? []).length;
  if (!letters) return true;
  return (text.match(UNSPACED) ?? []).length / letters <= 0.5;
}

// blocks: [{text, structured}]; structured marks a block inside a heading, list
// item or disclosure. Counts plain-prose blocks over `longAt` words, and the
// distinct blocks of `minRepeat` words or more that appear more than once (the
// same explanation twice on one screen). Block text is compared, never stored.
function blockFlags(blocks, { longAt = 60, minRepeat = 8 } = {}) {
  const seen = new Map();
  for (const b of blocks) {
    if (countWords(b.text) < minRepeat) continue;
    const key = b.text.toLowerCase().replace(/\s+/g, " ").trim();
    seen.set(key, (seen.get(key) ?? 0) + 1);
  }
  return {
    longUnstructuredBlocks: blocks.filter(
      (b) => !b.structured && countWords(b.text) > longAt,
    ).length,
    repeatedBlocks: [...seen.values()].filter((n) => n > 1).length,
    spaceDelimited: isSpaceDelimited(blocks.map((b) => b.text).join(" ")),
  };
}

// A cell's `copy` record. Word and sentence figures cover only the blocks in a
// space-delimited script, so a mixed-script screen is measured on its spaced
// text; `spaceDelimited` still describes the whole screen.
function copyFigures(blocks) {
  const spaced = blocks.filter((b) => isSpaceDelimited(b.text));
  return {
    ...copyMetrics(spaced.map((b) => b.text)),
    ...blockFlags(spaced),
    spaceDelimited: blockFlags(blocks).spaceDelimited,
  };
}

function hslToRgb(h, s, l) {
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) =>
    l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0) * 255, f(8) * 255, f(4) * 255];
}

function parseChannel(tok, scale) {
  return tok.endsWith("%") ? (parseFloat(tok) / 100) * scale : parseFloat(tok);
}

// "#rrggbb", or "#rrggbbaa" when the colour is translucent. Fully transparent
// and anything unparseable (named colours, oklch, ...) is null: the page
// resolves colours to rgb() before they reach this function.
function normaliseColour(str) {
  const c = parseColour(str);
  return c && c.hex ? c.hex : null;
}

// {hex}, {transparent: true} or null (unparseable).
function parseColour(str) {
  const s = String(str).trim().toLowerCase();
  if (s === "transparent") return { transparent: true };
  if (NAMED[s]) return { hex: NAMED[s] };
  let m = /^#([0-9a-f]{3,8})$/.exec(s);
  if (m) {
    let h = m[1];
    if (h.length === 3 || h.length === 4) h = [...h].map((c) => c + c).join("");
    if (h.length !== 6 && h.length !== 8) return null;
    if (h.length === 8 && h.slice(6) === "00") return { transparent: true };
    return {
      hex: "#" + (h.length === 8 && h.slice(6) === "ff" ? h.slice(0, 6) : h),
    };
  }
  m = /^(rgb|hsl)a?\(\s*([^)]*)\)$/.exec(s);
  if (!m) return null;
  const [main, alphaTok] = m[2].split("/").map((p) => p.trim());
  const parts = main.split(/[\s,]+/).filter(Boolean);
  const aTok = alphaTok ?? parts[3];
  if (parts.length < 3) return null;
  let alpha = aTok === undefined ? 1 : parseChannel(aTok, 1);
  alpha = Math.min(1, alpha);
  if (!(alpha > 0)) return { transparent: true };
  const rgb =
    m[1] === "rgb"
      ? parts.slice(0, 3).map((p) => parseChannel(p, 255))
      : hslToRgb(
          parseFloat(parts[0]),
          parseFloat(parts[1]) / 100,
          parseFloat(parts[2]) / 100,
        );
  if (rgb.some((n) => Number.isNaN(n))) return null;
  const base =
    "#" + rgb.map((n) => hex2(Math.max(0, Math.min(255, n)))).join("");
  return { hex: alpha < 1 ? base + hex2(alpha * 255) : base };
}

function matchesDeclared(colour, declaredSet) {
  const c = normaliseColour(colour);
  return c !== null && declaredSet.has(c);
}

// entries: [{value, selector, prop}] from the page; declared: colour strings.
function undeclaredColours(entries, declared) {
  const set = new Set(declared.map(normaliseColour).filter(Boolean));
  const groups = new Map();
  let unparsed = 0;
  for (const e of entries) {
    const parsed = parseColour(e.value);
    if (parsed === null) unparsed++;
    const c = parsed && parsed.hex;
    if (!c) continue;
    if (matchesDeclared(c, set)) continue;
    const g = groups.get(c) ?? { value: c, selector: e.selector, count: 0 };
    g.count++;
    groups.set(c, g);
  }
  const all = [...groups.values()].sort((a, b) => b.count - a.count);
  return { declared: set.size, unmatched: all, unparsed };
}

// rects: [{selector, w, h, disabled, inline}]. Disabled controls and links
// inside running text are exempt (WCAG 2.2 SC 2.5.8). The spacing exception
// (an undersized target with enough clear space around it passes) is NOT
// modelled, so the probe can over-report. A repo minimum that its UI doc ties
// to touch (repoMinPointer "coarse") applies only in a cell run with a coarse
// pointer; "any" applies in every cell.
function filterTargets(
  rects,
  { min = 24, repoMin = null, repoMinPointer = "any", pointer = "fine" } = {},
) {
  const live = rects.filter((r) => !r.disabled && !r.inline);
  const under = (limit) =>
    live
      .filter((r) => r.w < limit || r.h < limit)
      .map(({ selector, w, h }) => ({ selector, w, h }));
  const repoMinApplies =
    !!repoMin && (repoMinPointer === "any" || pointer === "coarse");
  return {
    small: under(min),
    belowRepoMin: repoMinApplies ? under(repoMin) : [],
    repoMin: repoMin ?? null,
    pointer,
    repoMinApplies,
  };
}

// boxes: [{selector, scrollWidth, clientWidth, dialog, wrapsTable}] from open
// dialogs and sideways scrollers. A box that scrolls or clips sideways inside
// itself is reported, except a scroller around a table or code block (an
// intended wrapper); a dialog is always reported. Widest excess first.
function findInnerOverflow(boxes) {
  return boxes
    .filter((b) => b.scrollWidth > b.clientWidth + 1)
    .filter((b) => b.dialog || !b.wrapsTable)
    .sort(
      (a, b) => b.scrollWidth - b.clientWidth - (a.scrollWidth - a.clientWidth),
    )
    .map(({ selector, scrollWidth, clientWidth, dialog }) => ({
      selector,
      scrollWidth,
      clientWidth,
      dialog: !!dialog,
    }));
}

// rects: [{selector, left, right, parentRight}]. Reports an element only when
// its parent fits, so the origin of the overflow is named, not its children.
function findOverflow(rects, viewportWidth, scrollWidth = null) {
  const over = rects
    .filter((r) => r.right > viewportWidth + 1)
    .filter((r) => r.parentRight == null || r.parentRight <= viewportWidth + 1)
    .map(({ selector, right }) => ({ selector, right: round1(right) }))
    .sort((a, b) => b.right - a.right);
  const present =
    scrollWidth === null ? over.length > 0 : scrollWidth > viewportWidth + 1;
  return {
    present,
    scrollWidth,
    clientWidth: viewportWidth,
    elements: present ? over : [],
  };
}

// steps: [{key, opaque?}] in tab order; key "body" is focus back on the document
// and `opaque` marks focus inside an iframe, whose contents the probe cannot
// see. A trap is a repeating cycle of distinct real elements that never returns
// to the document. Tab past the last stop always lands on the document, so a
// cycle through it is the normal wrap-around (focus left and came back). The
// page's tab-stop count is not used: it misses contenteditable and scrollers,
// so comparing against it hides real traps. A run of steps in an iframe is
// never reported: its stops are invisible, so it cannot be told from a loop. A
// modal dialog legitimately cycles: the keyboard log records whether Esc
// released it.
function detectTrap(steps) {
  const keys = steps.map((s) => s.key);
  for (let len = 1; len * 2 <= keys.length; len++) {
    const tail = keys.slice(-len);
    const prev = keys.slice(-2 * len, -len);
    if (tail.every((k, i) => k === prev[i])) {
      const opaque = steps.slice(-len).some((s) => s.opaque);
      return {
        trapped:
          !tail.includes("body") && !opaque && new Set(tail).size === len,
        cycleLength: len,
        elements: tail,
        ...(opaque ? { opaque: true } : {}),
      };
    }
  }
  return { trapped: false, cycleLength: null, elements: [] };
}

// Steps where focus jumps up the page by more than `px`: a hint that tab order
// differs from visual order. The wrap back to the start is expected once.
function tabOrderJumps(steps, px = 200) {
  const jumps = [];
  for (let i = 1; i < steps.length; i++) {
    if (steps[i - 1].y - steps[i].y > px) jumps.push(steps[i].n);
  }
  return jumps;
}

function stripQuery(text) {
  return String(text).replace(
    /(https?:\/\/[^\s?#"')]+|file:\/\/[^\s?#"')]+)[?#][^\s"')]*/g,
    "$1",
  );
}

const capList = (list, truncated, key) => {
  if (list.length > CAP) truncated.push(key);
  return list.slice(0, CAP);
};

// Failing checks of one cell, for the totals and failing-cell tables.
function summariseCell(cell) {
  // Word and sentence counts mean nothing for unspaced scripts: not a flag.
  const spaced = cell.copy.spaceDelimited !== false;
  const counts = {
    axe: cell.axe.length,
    // The page scrolling sideways, plus boxes that overflow inside themselves
    // (a cell from before `inner` existed has none).
    overflow:
      (cell.overflow.present ? Math.max(cell.overflow.elements.length, 1) : 0) +
      (cell.overflow.inner?.length ?? 0),
    smallTargets: cell.targets.small.length,
    belowRepoMin: cell.targets.belowRepoMin.length,
    console: cell.console.length,
    failedRequests: cell.failedRequests.length,
    longSentences: spaced ? cell.copy.longSentences : 0,
    longUnstructuredBlocks: spaced
      ? (cell.copy.longUnstructuredBlocks ?? 0)
      : 0,
    repeatedBlocks: cell.copy.repeatedBlocks ?? 0,
  };
  // The probe cannot know the main path, so long unstructured blocks are
  // counted but never fail a cell; the design lens flags them on primary flows.
  const failing = Object.entries(counts)
    .filter(([k, n]) => n > 0 && k !== "longUnstructuredBlocks")
    .map(([k]) => k);
  return {
    screen: cell.screen,
    state: cell.state,
    width: cell.width,
    theme: cell.theme,
    failing,
    counts,
  };
}

// cells: parsed cell JSON. One row per screen, failing screens first.
function summariseScreens(cells) {
  const screens = new Map();
  for (const cell of cells) {
    const s = summariseCell(cell);
    const row = screens.get(s.screen) ?? {
      screen: s.screen,
      cells: 0,
      failingCells: 0,
      totals: {},
      longestBlockWords: 0,
      maxMeanSentenceWords: 0,
      spaceDelimited: true,
    };
    row.cells++;
    if (s.failing.length) row.failingCells++;
    for (const [k, n] of Object.entries(s.counts))
      row.totals[k] = (row.totals[k] ?? 0) + n;
    // Word figures mean nothing for unspaced scripts: leave them out.
    if (cell.copy.spaceDelimited === false) row.spaceDelimited = false;
    else {
      row.longestBlockWords = Math.max(
        row.longestBlockWords,
        cell.copy.longestBlockWords,
      );
      row.maxMeanSentenceWords = Math.max(
        row.maxMeanSentenceWords,
        cell.copy.meanSentenceWords ?? 0,
      );
    }
    screens.set(s.screen, row);
  }
  const rows = [...screens.values()].sort(
    (a, b) => b.failingCells - a.failingCells,
  );
  return {
    screens: rows,
    cells: cells.length,
    failingCells: rows.reduce((n, r) => n + r.failingCells, 0),
  };
}

// cells: parsed cell JSON. Failing checks grouped by signature, so a failure
// that repeats across cells (a site-wide axe rule) is one group with a count
// and the first cell that showed it, which gets the capture. Signature: the
// check name, plus the rule id for axe and the first offending selector for
// overflow (page and inner are separate). Biggest groups first.
function distinctFailures(cells) {
  const groups = new Map();
  for (const cell of cells) {
    const keys = new Map();
    for (const check of summariseCell(cell).failing) {
      if (check === "axe") {
        for (const v of cell.axe) keys.set("axe\0" + v.rule, [check, v.rule]);
      } else if (check === "overflow") {
        const page = cell.overflow.present
          ? (cell.overflow.elements[0]?.selector ?? "page")
          : null;
        const inner = cell.overflow.inner?.[0]?.selector ?? null;
        for (const key of [page, inner])
          if (key !== null) keys.set("overflow\0" + key, [check, key]);
      } else {
        keys.set(check, [check, check]);
      }
    }
    for (const [id, [check, key]] of keys) {
      const g = groups.get(id) ?? {
        check,
        key,
        cells: 0,
        first: {
          screen: cell.screen,
          state: cell.state,
          width: cell.width,
          theme: cell.theme,
          screenshot: cell.screenshot ?? null,
        },
      };
      g.cells++;
      groups.set(id, g);
    }
  }
  return [...groups.values()].sort((a, b) => b.cells - a.cells);
}

// ---------- page code (runs in the browser; collects raw data only) ----------

function pageCollect() {
  const visible = (el) =>
    el.checkVisibility
      ? el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
      : !!(el.offsetWidth || el.offsetHeight);
  const sel = (el) => {
    const parts = [];
    for (
      let e = el;
      e && e.nodeType === 1 && parts.length < 4;
      e = e.parentElement
    ) {
      let p = e.tagName.toLowerCase();
      if (e.id) {
        parts.unshift(p + "#" + CSS.escape(e.id));
        break;
      }
      const cls = [...e.classList]
        .slice(0, 2)
        .map((c) => "." + CSS.escape(c))
        .join("");
      const same = e.parentElement
        ? [...e.parentElement.children].filter((c) => c.tagName === e.tagName)
        : [];
      p +=
        cls +
        (same.length > 1 ? ":nth-of-type(" + (same.indexOf(e) + 1) + ")" : "");
      parts.unshift(p);
    }
    return parts.join(" > ");
  };
  const all = [...document.querySelectorAll("body *")].filter(
    (e) =>
      !/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|LINK|META)$/.test(e.tagName) &&
      visible(e),
  );
  const vw = document.documentElement.clientWidth;

  // visible text, grouped by nearest block ancestor
  const blocks = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n.nodeValue.replace(/\s+/g, " ").trim();
    const p = n.parentElement;
    if (
      !t ||
      !p ||
      /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(p.tagName) ||
      !visible(p)
    )
      continue;
    let b = p;
    while (
      b !== document.body &&
      /^(inline|contents)$/.test(getComputedStyle(b).display)
    )
      b = b.parentElement;
    blocks.set(b, ((blocks.get(b) ?? "") + " " + t).trim());
  }
  // A block is structured when a heading, list item or disclosure holds it.
  const structuredSel =
    "h1,h2,h3,h4,h5,h6,[role=heading],li,dd,dt,[role=listitem],details,summary";

  const targetSel =
    'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=checkbox],[role=radio],[role=tab],[role=menuitem],[role=switch],[tabindex]:not([tabindex="-1"])';
  const targets = [];
  for (const el of document.querySelectorAll(targetSel)) {
    const r = el.getBoundingClientRect();
    if (!visible(el) || !r.width || !r.height) continue;
    const own = (el.textContent ?? "").trim();
    const parentText = (el.parentElement?.textContent ?? "").trim();
    targets.push({
      selector: sel(el),
      w: Math.round(r.width * 10) / 10,
      h: Math.round(r.height * 10) / 10,
      disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true",
      inline:
        el.tagName === "A" &&
        getComputedStyle(el).display === "inline" &&
        parentText.length > own.length + 10,
    });
  }

  const clipped = (el) => {
    for (
      let a = el.parentElement;
      a && a !== document.body && a !== document.documentElement;
      a = a.parentElement
    ) {
      if (getComputedStyle(a).overflowX !== "visible") return true;
    }
    return false;
  };
  const rects = [];
  for (const el of [document.documentElement, document.body, ...all]) {
    const r = el.getBoundingClientRect();
    if (r.right <= vw + 1 || clipped(el)) continue;
    const pr = el.parentElement?.getBoundingClientRect();
    rects.push({
      selector: sel(el),
      left: r.left,
      right: r.right,
      parentRight: pr ? pr.right : null,
    });
  }

  // Boxes that scroll or clip sideways inside themselves: open dialogs, and
  // visible elements whose overflow-x is auto or scroll. The page itself does
  // not scroll for these, so the page-level check misses them.
  const dialogs = new Set(
    document.querySelectorAll(
      "dialog[open],[role=dialog],[role=alertdialog],[aria-modal=true]",
    ),
  );
  const innerBoxes = [];
  for (const el of new Set([...dialogs, ...all])) {
    const isDialog = dialogs.has(el);
    // Width first: it is cheaper than a computed style on every element.
    if (el.scrollWidth <= el.clientWidth + 1 || !visible(el)) continue;
    if (!isDialog && !/^(auto|scroll)$/.test(getComputedStyle(el).overflowX))
      continue;
    innerBoxes.push({
      selector: sel(el),
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      dialog: isDialog,
      wrapsTable: !!el.querySelector("table,pre"),
    });
  }

  // colours in use, and the colours declared as custom properties
  const colours = [];
  for (const el of all.slice(0, 4000)) {
    const cs = getComputedStyle(el);
    const hasText = [...el.childNodes].some(
      (c) => c.nodeType === 3 && c.nodeValue.trim(),
    );
    if (hasText)
      colours.push({ value: cs.color, selector: sel(el), prop: "color" });
    colours.push({
      value: cs.backgroundColor,
      selector: sel(el),
      prop: "background",
    });
    if (parseFloat(cs.borderTopWidth) > 0 && cs.borderTopStyle !== "none") {
      colours.push({
        value: cs.borderTopColor,
        selector: sel(el),
        prop: "border",
      });
    }
  }
  const names = new Set();
  const raw = [];
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule.style) {
        for (const name of rule.style) {
          if (!name.startsWith("--")) continue;
          names.add(name);
          raw.push(rule.style.getPropertyValue(name).trim());
        }
      }
      if (rule.cssRules) walk(rule.cssRules);
    }
  };
  for (const sheet of document.styleSheets) {
    try {
      walk(sheet.cssRules);
    } catch {
      // cross-origin sheet: its custom properties cannot be read
    }
  }
  const root = getComputedStyle(document.documentElement);
  const probe = document.createElement("span");
  document.body.appendChild(probe);
  const declared = [];
  for (const v of [
    ...[...names].map((n) => root.getPropertyValue(n).trim()),
    ...raw.filter((v) => !v.includes("var(")),
  ]) {
    probe.style.color = "";
    probe.style.color = v;
    if (probe.style.color) declared.push(getComputedStyle(probe).color);
  }
  probe.remove();

  // Tab stops, through open shadow roots (an iframe is opaque and not counted):
  // a radio group is one stop (by name within its form).
  const stopSel =
    'a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])';
  const stops = [];
  const collect = (root) => {
    stops.push(...root.querySelectorAll(stopSel));
    for (const el of root.querySelectorAll("*")) {
      if (el.shadowRoot) collect(el.shadowRoot);
    }
  };
  collect(document);
  const radioGroups = new Set();
  const focusable = stops.filter((el) => {
    if (!visible(el)) return false;
    if (el.type !== "radio" || !el.name) return true;
    const group = (el.form ? sel(el.form) : "") + "|" + el.name;
    if (radioGroups.has(group)) return false;
    radioGroups.add(group);
    return true;
  }).length;

  return {
    blocks: [...blocks].map(([el, text]) => ({
      text,
      structured: !!el.closest(structuredSel),
    })),
    targets,
    rects,
    innerBoxes,
    colours,
    declared,
    focusable,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: vw,
  };
}

function describeFocus() {
  // Follow focus into open shadow roots: activeElement is only the host.
  let el = document.activeElement;
  const hosts = [];
  while (el && el.shadowRoot && el.shadowRoot.activeElement) {
    hosts.push(el);
    el = el.shadowRoot.activeElement;
  }
  window.__probeIds = window.__probeIds || new WeakMap();
  const id = (e) => {
    if (!window.__probeIds.has(e))
      window.__probeIds.set(e, (window.__probeN = (window.__probeN || 0) + 1));
    return "#" + window.__probeIds.get(e);
  };
  if (!el || el === document.body || el === document.documentElement) {
    return {
      key: "body",
      selector: "body",
      tag: "body",
      name: "",
      focusVisible: false,
      container: null,
      x: 0,
      y: 0,
    };
  }
  const key = [...hosts, el].map(id).join("/");
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const boxSel =
    "dialog,[role=dialog],[aria-modal=true],[role=menu],nav,header,main,aside,footer,form";
  const box =
    el.closest(boxSel) ?? hosts.map((h) => h.closest(boxSel)).find(Boolean);
  const name =
    el.getAttribute("aria-label") ||
    (el.getAttribute("aria-labelledby")
      ? document.getElementById(el.getAttribute("aria-labelledby"))?.textContent
      : "") ||
    el.labels?.[0]?.textContent ||
    el.textContent ||
    el.getAttribute("title") ||
    el.getAttribute("alt") ||
    // button-like inputs show their value as the label; typed text is never read
    (/^(submit|button|reset)$/.test(el.type) ? el.value : "") ||
    "";
  const indicator =
    (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) ||
    cs.boxShadow !== "none";
  return {
    key,
    opaque: el.tagName === "IFRAME" || undefined,
    selector:
      el.tagName.toLowerCase() +
      (el.id ? "#" + el.id : "") +
      (el.className && typeof el.className === "string"
        ? "." + el.className.trim().split(/\s+/)[0]
        : ""),
    tag: el.tagName.toLowerCase(),
    role: el.getAttribute("role"),
    name: name.replace(/\s+/g, " ").trim().slice(0, 60),
    focusVisible: el.matches(":focus-visible") && indicator,
    container: box
      ? box.tagName.toLowerCase() + (box.id ? "#" + box.id : "")
      : null,
    x: Math.round(r.x),
    y: Math.round(r.y),
  };
}

// ---------- CLI ----------

const FLAGS = {
  url: "string",
  screen: "string",
  state: "string",
  width: "number",
  theme: "string",
  out: "string",
  screenshot: "string",
  actions: "string",
  modules: "string",
  summarise: "string",
  "delay-match": "string",
  "delay-ms": "number",
  "min-target": "number",
  "min-target-pointer": "string",
  pointer: "string",
  keyboard: "number",
};

// Rejects unknown flags, flags with no value and non-numeric numbers, so a
// typo fails loudly instead of silently probing with a default.
function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    const flag = argv[i];
    if (!flag.startsWith("--") || !(flag.slice(2) in FLAGS))
      throw new Error("unknown argument " + flag);
    const name = flag.slice(2);
    const value = argv[i + 1];
    if (value === undefined || value.startsWith("--"))
      throw new Error(flag + " needs a value");
    if (FLAGS[name] === "number" && !/^\d+(\.\d+)?$/.test(value))
      throw new Error(flag + " is a number");
    out[name] = value;
  }
  return out;
}

function loadTools(modulesDir) {
  const req = createRequire(path.join(path.resolve(modulesDir), "noop.js"));
  const dir = (name) => path.dirname(req.resolve(name + "/package.json"));
  const playwright = req("playwright");
  const axeDir = dir("axe-core");
  return {
    playwright,
    axeSource: fs.readFileSync(path.join(axeDir, "axe.min.js"), "utf8"),
    versions: {
      playwright: req("playwright/package.json").version,
      axe: req(path.join(axeDir, "package.json")).version,
    },
  };
}

async function runCell(args, tools) {
  const width = Number(args.width);
  const theme = args.theme;
  const minTarget = args["min-target"] ? Number(args["min-target"]) : null;
  const delay = args["delay-ms"] ? Number(args["delay-ms"]) : 0;
  const pointer = args.pointer ?? "fine";
  const browser = await tools.playwright.chromium.launch();
  try {
    const context = await browser.newContext({
      colorScheme: theme,
      viewport: { width, height: 800 },
      // A touch device is what makes the product's (pointer: coarse) styles apply.
      hasTouch: pointer === "coarse",
    });
    const page = await context.newPage();
    const consoleErrors = [];
    const failed = [];
    const notes = [];
    page.on(
      "console",
      (m) =>
        m.type() === "error" &&
        consoleErrors.push({
          type: "error",
          text: stripQuery(m.text()).slice(0, 200),
        }),
    );
    page.on("pageerror", (e) =>
      consoleErrors.push({
        type: "pageerror",
        text: stripQuery(e.message).slice(0, 200),
      }),
    );
    page.on("requestfailed", (r) =>
      failed.push({
        url: stripQuery(r.url()),
        status: r.failure()?.errorText ?? "failed",
      }),
    );
    page.on(
      "response",
      (r) =>
        r.status() >= 400 &&
        failed.push({ url: stripQuery(r.url()), status: r.status() }),
    );
    if (delay && args["delay-match"]) {
      await page.route(args["delay-match"], async (route) => {
        await new Promise((resolve) => setTimeout(resolve, delay));
        await route.continue().catch(() => {});
      });
    }
    await page.goto(args.url, {
      waitUntil: delay ? "domcontentloaded" : "load",
      timeout: 30000,
    });
    if (!delay)
      await page
        .waitForLoadState("networkidle", { timeout: 10000 })
        .catch(() => {});
    await page.waitForTimeout(delay ? 200 : 300);
    if (args.actions) {
      const mod = await import(pathToFileURL(path.resolve(args.actions)).href);
      await mod.default(page, {
        state: args.state,
        width,
        theme,
        url: args.url,
        note: (s) => notes.push(String(s)),
        // Where focus is now, in the shape of a keyboard step.
        focus: () => page.evaluate(describeFocus),
      });
      await page.waitForTimeout(200);
    }
    await page.evaluate(tools.axeSource);
    const axeResult = await page.evaluate(() =>
      globalThis.axe.run(document, { resultTypes: ["violations"] }),
    );
    const raw = await page.evaluate(pageCollect);
    const truncated = [];
    if (args.screenshot)
      await page.screenshot({ path: args.screenshot, fullPage: true });
    const keyboard = args.keyboard
      ? await keyboardPass(page, Number(args.keyboard), raw.focusable)
      : undefined;
    const axe = axeResult.violations.map((v) => ({
      rule: v.id,
      impact: v.impact,
      selector: v.nodes[0]?.target.flat().join(" ") ?? "",
      count: v.nodes.length,
    }));
    const overflow = findOverflow(raw.rects, raw.clientWidth, raw.scrollWidth);
    overflow.elements = capList(overflow.elements, truncated, "overflow");
    overflow.inner = capList(
      findInnerOverflow(raw.innerBoxes),
      truncated,
      "overflow.inner",
    );
    const targets = filterTargets(raw.targets, {
      min: 24,
      repoMin: minTarget,
      repoMinPointer: args["min-target-pointer"] ?? "any",
      pointer,
    });
    targets.small = capList(targets.small, truncated, "targets.small");
    targets.belowRepoMin = capList(
      targets.belowRepoMin,
      truncated,
      "targets.belowRepoMin",
    );
    const colours = undeclaredColours(raw.colours, raw.declared);
    colours.unmatched = capList(colours.unmatched, truncated, "colours");
    const cell = {
      schema: 1,
      url: stripQuery(args.url),
      screen: args.screen ?? (new URL(args.url).pathname || "/"),
      state: args.state ?? "default",
      width,
      theme,
      pointer,
      probe: tools.versions,
      axe: capList(axe, truncated, "axe"),
      overflow,
      targets,
      console: capList(consoleErrors, truncated, "console"),
      failedRequests: capList(failed, truncated, "failedRequests"),
      copy: copyFigures(raw.blocks),
      colours,
      screenshot: args.screenshot ?? null,
      truncated,
    };
    if (notes.length) cell.notes = notes;
    if (keyboard) cell.keyboard = keyboard;
    return cell;
  } finally {
    await browser.close();
  }
}

async function keyboardPass(page, n, focusable) {
  const steps = [];
  for (let i = 1; i <= n; i++) {
    await page.keyboard.press("Tab");
    steps.push({ n: i, ...(await page.evaluate(describeFocus)) });
  }
  return {
    focusable,
    steps,
    trap: detectTrap(steps),
    orderJumps: tabOrderJumps(steps),
  };
}

function summariseDir(dir) {
  const cells = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json") && f !== "summary.json")
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
  const failing = cells.map(summariseCell).filter((c) => c.failing.length);
  return {
    schema: 1,
    ...summariseScreens(cells),
    failing,
    distinct: distinctFailures(cells),
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.summarise) {
    const text = JSON.stringify(summariseDir(args.summarise), null, 2);
    if (args.out) fs.writeFileSync(args.out, text + "\n");
    else console.log(text);
    return;
  }
  for (const k of ["url", "width", "theme", "out"])
    if (!args[k]) throw new Error("missing --" + k);
  if (!["light", "dark"].includes(args.theme))
    throw new Error("--theme is light or dark");
  if (args.pointer && !["fine", "coarse"].includes(args.pointer))
    throw new Error("--pointer is fine or coarse");
  if (
    args["min-target-pointer"] &&
    !["any", "coarse"].includes(args["min-target-pointer"])
  )
    throw new Error("--min-target-pointer is any or coarse");
  if (args["min-target-pointer"] && !args["min-target"])
    throw new Error("--min-target-pointer needs --min-target");
  if (!(Number(args.width) > 0))
    throw new Error("--width is a number of CSS px");
  if (
    args.keyboard &&
    !(Number(args.keyboard) > 0 && Number(args.keyboard) <= 200)
  )
    throw new Error("--keyboard is 1 to 200");
  const modules = args.modules ?? process.env.PROBE_MODULES;
  if (!modules)
    throw new Error(
      "set PROBE_MODULES (or --modules) to the scratch install folder",
    );
  if (
    !process.env.PLAYWRIGHT_BROWSERS_PATH &&
    fs.existsSync(path.join(modules, "browsers"))
  ) {
    process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(modules, "browsers");
  }
  const tools = loadTools(modules);
  let cell;
  try {
    cell = await runCell(args, tools);
  } catch (err) {
    if (
      /Executable doesn't exist|browserType\.launch/.test(String(err.message))
    ) {
      throw new Error(
        "Tool unavailable: Playwright Chromium (" +
          String(err.message).split("\n")[0] +
          ")",
        { cause: err },
      );
    }
    throw err;
  }
  fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify(cell, null, 2) + "\n");
}

module.exports = {
  countWords,
  splitSentences,
  copyMetrics,
  isSpaceDelimited,
  blockFlags,
  copyFigures,
  normaliseColour,
  matchesDeclared,
  undeclaredColours,
  filterTargets,
  findOverflow,
  findInnerOverflow,
  detectTrap,
  parseArgs,
  tabOrderJumps,
  stripQuery,
  summariseCell,
  summariseScreens,
  distinctFailures,
};

if (require.main === module) {
  main().catch((err) => {
    console.error("probe failed: " + err.message);
    process.exit(2);
  });
}
