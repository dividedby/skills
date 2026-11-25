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

test("isSpaceDelimited", async (t) => {
  const cases = [
    ["English", "Save your changes before you leave.", true],
    ["Korean uses spaces", "변경 사항을 저장하세요", true],
    ["Japanese", "変更を保存してから終了してください。", false],
    ["Chinese", "请在离开之前保存您的更改", false],
    ["Thai", "กรุณาบันทึกการเปลี่ยนแปลงก่อนออก", false],
    ["Latin text with a few CJK labels", `${words(20)} 保存`, true],
    ["no letters", "123 — 45", true],
  ];
  for (const [name, input, want] of cases) {
    await t.test(name, () => assert.equal(probe.isSpaceDelimited(input), want));
  }
});

test("blockFlags counts plain-prose blocks over 60 words, not structured ones", () => {
  const got = probe.blockFlags([
    { text: words(61), structured: false },
    { text: words(60), structured: false },
    { text: words(90), structured: true },
  ]);
  assert.equal(got.longUnstructuredBlocks, 1);
});

test("blockFlags counts a repeated explanation once, ignoring case and spacing", () => {
  const explain = "Archived items stay in the export until you delete them.";
  const got = probe.blockFlags([
    { text: explain, structured: false },
    { text: explain.toUpperCase().replace(/ /g, "  "), structured: true },
    { text: explain, structured: false },
    { text: "Delete", structured: false },
    { text: "Delete", structured: false },
  ]);
  assert.equal(got.repeatedBlocks, 1);
});

test("blockFlags on no text", () => {
  assert.deepEqual(probe.blockFlags([]), {
    longUnstructuredBlocks: 0,
    repeatedBlocks: 0,
    spaceDelimited: true,
  });
});

test("copyFigures measures only space-delimited blocks", async (t) => {
  const long = Array.from({ length: 30 }, (_, i) => `word${i}`).join(" ") + ".";
  const cjk = "这是一个没有空格的很长的中文句子用来测试。".repeat(4);
  const cases = [
    {
      name: "mixed screen: unspaced block left out of the figures",
      blocks: [
        { text: "Save your work.", structured: false },
        { text: long, structured: false },
        { text: cjk, structured: false },
      ],
      want: {
        visibleWords: 33,
        longestBlockWords: 30,
        longSentences: 1,
        meanSentenceWords: 16.5,
        spaceDelimited: true,
      },
    },
    {
      name: "unspaced screen: no figures, flag false",
      blocks: [{ text: cjk, structured: false }],
      want: {
        visibleWords: 0,
        longestBlockWords: 0,
        longSentences: 0,
        spaceDelimited: false,
      },
    },
  ];
  for (const { name, blocks, want } of cases) {
    await t.test(name, () => {
      const got = probe.copyFigures(blocks);
      for (const [k, v] of Object.entries(want)) assert.equal(got[k], v, k);
    });
  }
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
  await t.test("a coarse-only repo minimum", async (t) => {
    const rects = [{ selector: "button", w: 30, h: 30 }];
    const cases = [
      ["coarse rule skipped on a fine cell", "coarse", "fine", 0, false],
      ["coarse rule applied on a coarse cell", "coarse", "coarse", 1, true],
      ["any applies on a fine cell", "any", "fine", 1, true],
      ["any applies on a coarse cell", "any", "coarse", 1, true],
    ];
    for (const [name, repoMinPointer, pointer, count, applies] of cases) {
      await t.test(name, () => {
        const got = probe.filterTargets(rects, {
          repoMin: 44,
          repoMinPointer,
          pointer,
        });
        assert.equal(got.belowRepoMin.length, count);
        assert.equal(got.repoMinApplies, applies);
        assert.equal(got.pointer, pointer);
        assert.equal(got.repoMin, 44);
      });
    }
    await t.test("no repo minimum never applies", () => {
      const got = probe.filterTargets(rects, { pointer: "coarse" });
      assert.equal(got.repoMinApplies, false);
      assert.deepEqual(got.belowRepoMin, []);
    });
  });
});

test("hit area counts a wrapping or for= label", async (t) => {
  const cases = [
    ["a 16x16 box in a 120x32 label is not small", 16, 16, 120, 32, 0],
    ["no label: 16x16 is small", 16, 16, undefined, undefined, 1],
    ["a label only 20 high is still small", 16, 16, 120, 20, 1],
    ["a label widens one side only", 16, 30, 120, 10, 0],
    ["a label null (no label) is small", 16, 16, null, null, 1],
  ];
  for (const [name, w, h, labelW, labelH, small] of cases) {
    await t.test(name, () => {
      const got = probe.filterTargets([
        { selector: "input", w, h, labelW, labelH },
      ]);
      assert.equal(got.small.length, small);
    });
  }
  await t.test("the label counts for the repo minimum too", () => {
    const rect = { selector: "input", w: 16, h: 16, labelW: 120, labelH: 32 };
    assert.equal(
      probe.filterTargets([rect], { repoMin: 44 }).belowRepoMin.length,
      1,
    );
    assert.equal(
      probe.filterTargets([{ ...rect, labelH: 48 }], { repoMin: 44 })
        .belowRepoMin.length,
      0,
    );
  });
  await t.test("disabled and inline stay exempt", () => {
    const got = probe.filterTargets([
      { selector: "a", w: 10, h: 10, labelW: 5, labelH: 5, disabled: true },
      { selector: "p a", w: 10, h: 10, inline: true },
    ]);
    assert.deepEqual(got.small, []);
  });
  await t.test("reported size is the hit area", () => {
    const got = probe.filterTargets([
      { selector: "input", w: 16, h: 16, labelW: 120, labelH: 20 },
    ]);
    assert.deepEqual(got.small, [{ selector: "input", w: 120, h: 20 }]);
  });
});

test("splitInnerOverflow", async (t) => {
  const box = (over) => ({
    selector: "div",
    scrollWidth: 500,
    clientWidth: 300,
    dialog: false,
    wrapsTable: false,
    declared: false,
    ...over,
  });
  const cases = [
    [
      "a declared scroller is allowed, not reported",
      box({ declared: true }),
      0,
      1,
    ],
    ["an undeclared scroller is reported", box(), 1, 0],
    [
      "a declared dialog is still reported",
      box({ dialog: true, declared: true }),
      1,
      0,
    ],
    [
      "a declared box that fits is in neither",
      box({ declared: true, scrollWidth: 301 }),
      0,
      0,
    ],
  ];
  for (const [name, b, inner, allowed] of cases) {
    await t.test(name, () => {
      const got = probe.splitInnerOverflow([b]);
      assert.equal(got.inner.length, inner);
      assert.equal(got.allowed.length, allowed);
    });
  }
  await t.test("findInnerOverflow omits the allowed", () => {
    const got = probe.findInnerOverflow([
      box({ selector: "a", declared: true }),
      box({ selector: "b" }),
    ]);
    assert.deepEqual(
      got.map((b) => b.selector),
      ["b"],
    );
  });
});

test("findInnerOverflow", async (t) => {
  const box = (over) => ({
    selector: "div",
    scrollWidth: 500,
    clientWidth: 300,
    dialog: false,
    wrapsTable: false,
    ...over,
  });
  const cases = [
    ["a dialog wider than itself is reported", [box({ dialog: true })], 1],
    ["a fitting dialog is not", [box({ dialog: true, scrollWidth: 301 })], 0],
    ["a plain scroller is reported", [box()], 1],
    ["a table or code wrapper is not", [box({ wrapsTable: true })], 0],
    [
      "a dialog holding a table is still reported",
      [box({ dialog: true, wrapsTable: true })],
      1,
    ],
  ];
  for (const [name, boxes, want] of cases) {
    await t.test(name, () =>
      assert.equal(probe.findInnerOverflow(boxes).length, want),
    );
  }
  await t.test("widest excess first, with only the reported fields", () => {
    const got = probe.findInnerOverflow([
      box({ selector: "a", scrollWidth: 400 }),
      box({ selector: "b", scrollWidth: 900, dialog: true, wrapsTable: true }),
    ]);
    assert.deepEqual(got, [
      { selector: "b", scrollWidth: 900, clientWidth: 300, dialog: true },
      { selector: "a", scrollWidth: 400, clientWidth: 300, dialog: false },
    ]);
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

test("summariseCell fails a cell whose only overflow is inside a dialog", () => {
  const inner = [
    { selector: "dialog", scrollWidth: 500, clientWidth: 300, dialog: true },
  ];
  const got = probe.summariseCell(
    cell({ overflow: { present: false, elements: [], inner } }),
  );
  assert.deepEqual(got.failing, ["overflow"]);
  assert.equal(got.counts.overflow, 1);
  const both = probe.summariseCell(
    cell({
      overflow: {
        present: true,
        elements: [{ selector: "div", right: 900 }],
        inner,
      },
    }),
  );
  assert.equal(both.counts.overflow, 2);
});

test("summariseCell counts copy flags, and ignores word counts for unspaced text", () => {
  const copy = {
    longSentences: 2,
    longestBlockWords: 90,
    longUnstructuredBlocks: 1,
    repeatedBlocks: 1,
  };
  const spaced = probe.summariseCell(
    cell({ copy: { ...copy, spaceDelimited: true } }),
  );
  assert.deepEqual(spaced.failing, ["longSentences", "repeatedBlocks"]);
  assert.equal(spaced.counts.longUnstructuredBlocks, 1);
  const unspaced = probe.summariseCell(
    cell({ copy: { ...copy, spaceDelimited: false } }),
  );
  assert.deepEqual(unspaced.failing, ["repeatedBlocks"]);
});

test("summariseScreens keeps the highest mean sentence length of spaced cells", () => {
  const copy = (mean, spaceDelimited = true) => ({
    longSentences: 0,
    longestBlockWords: 10,
    meanSentenceWords: mean,
    spaceDelimited,
  });
  const got = probe.summariseScreens([
    cell({ copy: copy(14) }),
    cell({ copy: copy(22), width: 1280 }),
    cell({ copy: copy(80, false), theme: "light" }),
  ]);
  assert.equal(got.screens[0].maxMeanSentenceWords, 22);
});

test("summariseScreens marks a screen unspaced and leaves its word figures out", () => {
  const copy = (spaceDelimited, longestBlockWords) => ({
    longSentences: 0,
    longestBlockWords,
    meanSentenceWords: 5,
    spaceDelimited,
  });
  const got = probe.summariseScreens([
    cell({ copy: copy(true, 12) }),
    cell({ copy: copy(false, 400), width: 1280 }),
  ]);
  assert.equal(got.screens[0].spaceDelimited, false);
  assert.equal(got.screens[0].longestBlockWords, 12);
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

test("distinctFailures groups a repeated failure into one capture", async (t) => {
  const axe = (rule) => [{ rule, impact: "serious", selector: "x", count: 1 }];
  const shot = (name) => ({ screenshot: `shots/${name}.png` });
  await t.test("a site-wide axe rule on 3 cells is one group", () => {
    const got = probe.distinctFailures([
      cell({ screen: "a", axe: axe("color-contrast"), ...shot("a") }),
      cell({ screen: "b", axe: axe("color-contrast"), ...shot("b") }),
      cell({ screen: "c", axe: axe("color-contrast"), ...shot("c") }),
    ]);
    assert.equal(got.length, 1);
    assert.equal(got[0].check, "axe");
    assert.equal(got[0].key, "color-contrast");
    assert.equal(got[0].cells, 3);
    assert.deepEqual(got[0].first, {
      screen: "a",
      state: "default",
      width: 375,
      theme: "dark",
      screenshot: "shots/a.png",
    });
  });
  await t.test("different rules, selectors and checks are separate", () => {
    const got = probe.distinctFailures([
      cell({
        axe: [...axe("image-alt"), ...axe("label")],
        overflow: {
          present: true,
          elements: [{ selector: "div.wide", right: 900 }],
          inner: [
            {
              selector: "dialog",
              scrollWidth: 500,
              clientWidth: 300,
              dialog: true,
            },
          ],
        },
        console: [{ type: "error", text: "x" }],
      }),
      cell({
        screen: "b",
        overflow: {
          present: true,
          elements: [{ selector: "div.wide", right: 900 }],
        },
      }),
    ]);
    assert.deepEqual(
      got.map((g) => [g.check, g.key, g.cells]),
      [
        ["overflow", "div.wide", 2],
        ["axe", "image-alt", 1],
        ["axe", "label", 1],
        ["overflow", "dialog", 1],
        ["console", "console", 1],
      ],
    );
  });
  await t.test("passing cells and a missing screenshot", () => {
    assert.deepEqual(probe.distinctFailures([cell()]), []);
    const got = probe.distinctFailures([
      cell({ console: [{ type: "error", text: "x" }] }),
    ]);
    assert.equal(got[0].first.screenshot, null);
  });
  await t.test("the first captured cell names the image", () => {
    const got = probe.distinctFailures([
      cell({ screen: "a", axe: axe("label") }),
      cell({ screen: "b", axe: axe("label"), ...shot("b") }),
    ]);
    assert.equal(got[0].first.screen, "b");
    assert.equal(got[0].first.screenshot, "shots/b.png");
  });
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
  await t.test("--allow-scroll takes a selector list", () => {
    const got = probe.parseArgs(["--allow-scroll", ".a, #b > .c"]);
    assert.deepEqual(got, { "allow-scroll": ".a, #b > .c" });
    assert.throws(() => probe.parseArgs(["--allow-scroll"]));
  });
  await t.test("valid", () => {
    const got = probe.parseArgs([
      "--url",
      "http://x/",
      "--width",
      "375",
      "--min-target",
      "44",
      "--pointer",
      "coarse",
      "--min-target-pointer",
      "coarse",
    ]);
    assert.deepEqual(got, {
      url: "http://x/",
      width: "375",
      "min-target": "44",
      pointer: "coarse",
      "min-target-pointer": "coarse",
    });
  });
});
