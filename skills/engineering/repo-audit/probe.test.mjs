// Unit tests for the pure helpers in probe.js. No browser: the page-side
// collection is proven by the scratch fixture run in probe.md, not here.
import test from "node:test";
import assert from "node:assert/strict";
import probe from "./probe.js";

const words = (n) => Array.from({ length: n }, (_, i) => "word" + i).join(" ");

test("splitSentences", async (t) => {
  const cases = [
    [
      "two sentences",
      "One two. Three four five!",
      ["One two.", "Three four five!"],
    ],
    ["no terminator", "Just a fragment", ["Just a fragment"]],
    [
      "decimal is not a boundary",
      "Version 3.5 is out. Next.",
      ["Version 3.5 is out.", "Next."],
    ],
    [
      "abbreviation is not a boundary",
      "Use tools, e.g. a hammer. Done.",
      ["Use tools, e.g. a hammer.", "Done."],
    ],
    [
      "question and quote",
      'Why? He said "no." Fine.',
      ["Why?", 'He said "no."', "Fine."],
    ],
    ["empty", "   ", []],
  ];
  for (const [name, input, want] of cases) {
    await t.test(name, () =>
      assert.deepEqual(probe.splitSentences(input), want),
    );
  }
});

test("copyMetrics counts long sentences strictly above 25 words", () => {
  const m = probe.copyMetrics([
    `${words(25)}.`,
    `${words(26)}.`,
    `${words(30)}.`,
  ]);
  assert.equal(m.longSentences, 2);
  assert.equal(m.longestBlockWords, 30);
  assert.equal(m.visibleWords, 81);
  assert.equal(m.meanSentenceWords, 27);
});

test("copyMetrics on no text", () => {
  assert.deepEqual(probe.copyMetrics([]), {
    visibleWords: 0,
    longestBlockWords: 0,
    longSentences: 0,
    meanSentenceWords: 0,
  });
});

test("copyMetrics ignores punctuation-only tokens", () => {
  assert.equal(probe.copyMetrics(["Save — now"]).visibleWords, 2);
});

test("normaliseColour", async (t) => {
  const cases = [
    ["#FFF", "#ffffff"],
    ["rgb(255, 255, 255)", "#ffffff"],
    ["rgb(255 255 255)", "#ffffff"],
    ["hsl(0 0% 100%)", "#ffffff"],
    ["hsl(0, 100%, 50%)", "#ff0000"],
    ["#0b5fff", "#0b5fff"],
    ["rgba(0, 0, 0, 0.5)", "#00000080"],
    ["rgb(0 0 0 / 50%)", "#00000080"],
    ["rgba(0, 0, 0, 1)", "#000000"],
    ["rgba(0, 0, 0, 0)", null],
    ["transparent", null],
    ["oklch(0.5 0.1 20)", null],
    ["not a colour", null],
  ];
  for (const [input, want] of cases) {
    await t.test(input, () => assert.equal(probe.normaliseColour(input), want));
  }
});

test("undeclaredColours reports only colours no custom property declares", () => {
  const entries = [
    { value: "rgb(11, 95, 255)", selector: "a.link", prop: "color" },
    { value: "rgb(18, 52, 86)", selector: "p.note", prop: "color" },
    { value: "rgb(18, 52, 86)", selector: "p.other", prop: "color" },
    { value: "rgba(0, 0, 0, 0)", selector: "div", prop: "background" },
    { value: "oklch(0.5 0.1 20)", selector: "span", prop: "color" },
  ];
  const got = probe.undeclaredColours(entries, [
    "rgb(11, 95, 255)",
    "not a colour",
  ]);
  assert.deepEqual(got.unmatched, [
    { value: "#123456", selector: "p.note", count: 2 },
  ]);
  assert.equal(got.declared, 1);
  assert.equal(got.unparsed, 1);
});

test("matchesDeclared", () => {
  const set = new Set(["#ffffff"]);
  assert.equal(probe.matchesDeclared("rgb(255,255,255)", set), true);
  assert.equal(probe.matchesDeclared("#fefefe", set), false);
  assert.equal(probe.matchesDeclared("transparent", set), false);
});

test("filterTargets uses 24 px as the limit and exempts disabled and inline", async (t) => {
  for (const [size, small] of [
    [16, true],
    [23, true],
    [24, false],
    [25, false],
  ]) {
    await t.test(`${size}x${size}`, () => {
      const got = probe.filterTargets([
        { selector: "button", w: size, h: size },
      ]);
      assert.equal(got.small.length, small ? 1 : 0);
    });
  }
  await t.test("one short side fails", () => {
    assert.equal(
      probe.filterTargets([{ selector: "a", w: 100, h: 16 }]).small.length,
      1,
    );
  });
  await t.test("exemptions", () => {
    const got = probe.filterTargets([
      { selector: "button[disabled]", w: 10, h: 10, disabled: true },
      { selector: "p a", w: 40, h: 14, inline: true },
    ]);
    assert.deepEqual(got.small, []);
  });
  await t.test("repo minimum", () => {
    const rects = [{ selector: "button", w: 30, h: 30 }];
    const got = probe.filterTargets(rects, { repoMin: 44 });
    assert.equal(got.small.length, 0);
    assert.equal(got.belowRepoMin.length, 1);
    assert.equal(got.repoMin, 44);
    assert.equal(probe.filterTargets(rects).repoMin, null);
  });
});

test("findOverflow names the origin, not its children", () => {
  const rects = [
    { selector: "div.wide", left: 0, right: 1400, parentRight: 375 },
    { selector: "div.wide > p", left: 0, right: 1400, parentRight: 1400 },
    { selector: "div.fits", left: 0, right: 375, parentRight: 375 },
  ];
  const got = probe.findOverflow(rects, 375, 1400);
  assert.equal(got.present, true);
  assert.deepEqual(got.elements, [{ selector: "div.wide", right: 1400 }]);
});

test("findOverflow reports nothing when the page does not scroll sideways", () => {
  const rects = [
    { selector: "div.drawer", left: 375, right: 700, parentRight: 375 },
  ];
  const got = probe.findOverflow(rects, 375, 375);
  assert.equal(got.present, false);
  assert.deepEqual(got.elements, []);
});

test("detectTrap", async (t) => {
  const steps = (keys) => keys.map((key, i) => ({ key, n: i + 1 }));
  await t.test("loop inside a subset is a trap", () => {
    const got = probe.detectTrap(steps(["a", "b", "c", "b", "c", "b", "c"]));
    assert.deepEqual(got, {
      trapped: true,
      cycleLength: 2,
      elements: ["b", "c"],
    });
  });
  await t.test("a loop that never reaches the document is a trap", () => {
    // e.g. contenteditable stops the tab-stop count misses: the loop can be
    // as long as that count and still never let focus leave.
    const got = probe.detectTrap(
      steps(["#1", "#2", "#3", "#4", "#2", "#3", "#4"]),
    );
    assert.equal(got.trapped, true);
    assert.equal(got.cycleLength, 3);
  });
  await t.test("a wrap through the document is not a trap", () => {
    const got = probe.detectTrap(
      steps(["#1", "#2", "#3", "body", "#1", "#2", "#3", "body"]),
    );
    assert.equal(got.trapped, false);
    assert.equal(got.cycleLength, 4);
  });
  await t.test("a run inside an iframe is opaque, not a trap", () => {
    const framed = steps(["#1", "#2", "#2", "#2"]).map((s, i) =>
      i ? { ...s, opaque: true } : s,
    );
    const got = probe.detectTrap(framed);
    assert.equal(got.trapped, false);
    assert.equal(got.opaque, true);
  });
  await t.test("distinct inner keys of a shadow host are not a cycle", () => {
    const got = probe.detectTrap(
      steps(["#1", "#2/#3", "#2/#4", "#2/#5", "#6"]),
    );
    assert.equal(got.cycleLength, null);
  });
  await t.test("focus stuck on one real element is a trap", () => {
    const got = probe.detectTrap(steps(["#1", "#2", "#2", "#2"]));
    assert.equal(got.trapped, true);
  });
  await t.test("no cycle yet", () => {
    assert.equal(probe.detectTrap(steps(["a", "b", "c"])).cycleLength, null);
  });
});

test("tabOrderJumps flags focus moving up the page", () => {
  const got = probe.tabOrderJumps([
    { n: 1, y: 10 },
    { n: 2, y: 500 },
    { n: 3, y: 40 },
    { n: 4, y: 90 },
  ]);
  assert.deepEqual(got, [3]);
});

test("stripQuery removes query strings and fragments from URLs in text", () => {
  assert.equal(
    probe.stripQuery(
      "GET http://localhost:8080/api/items?token=abc&x=1 failed",
    ),
    "GET http://localhost:8080/api/items failed",
  );
  assert.equal(probe.stripQuery("no url here?"), "no url here?");
});

const cell = (over = {}) => ({
  screen: "home",
  state: "default",
  width: 375,
  theme: "dark",
  axe: [],
  overflow: { present: false, elements: [] },
  targets: { small: [], belowRepoMin: [] },
  console: [],
  failedRequests: [],
  copy: { longSentences: 0, longestBlockWords: 12 },
  ...over,
});

test("summariseCell lists the failing checks", () => {
  const got = probe.summariseCell(
    cell({
      axe: [
        { rule: "image-alt", impact: "critical", selector: "img", count: 1 },
      ],
      overflow: { present: true, elements: [{ selector: "div", right: 900 }] },
    }),
  );
  assert.deepEqual(got.failing, ["axe", "overflow"]);
  assert.equal(probe.summariseCell(cell()).failing.length, 0);
});

test("summariseScreens puts failing screens first and totals per screen", () => {
  const cells = [
    cell({ screen: "settings" }),
    cell({ screen: "home", console: [{ type: "error", text: "x" }] }),
    cell({ screen: "home", width: 1280 }),
  ];
  const got = probe.summariseScreens(cells);
  assert.deepEqual(
    got.screens.map((s) => s.screen),
    ["home", "settings"],
  );
  assert.equal(got.screens[0].cells, 2);
  assert.equal(got.screens[0].failingCells, 1);
  assert.equal(got.screens[0].totals.console, 1);
  assert.equal(got.failingCells, 1);
});

test("parseArgs", async (t) => {
  const bad = [
    ["unknown flag", ["--widht", "375"]],
    ["positional argument", ["375"]],
    ["flag with no value", ["--url"]],
    ["flag followed by a flag", ["--url", "--width", "375"]],
    ["non-numeric number", ["--min-target", "big"]],
    ["negative number", ["--width", "-1"]],
  ];
  for (const [name, argv] of bad) {
    await t.test(name, () => assert.throws(() => probe.parseArgs(argv)));
  }
  await t.test("valid", () => {
    const got = probe.parseArgs([
      "--url",
      "http://x/",
      "--width",
      "375",
      "--min-target",
      "44",
    ]);
    assert.deepEqual(got, {
      url: "http://x/",
      width: "375",
      "min-target": "44",
    });
  });
});
