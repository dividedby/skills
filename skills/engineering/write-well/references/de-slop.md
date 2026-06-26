# De-Slop

The de-slop layer. Run it during the de-slop step of both entry points. It is
also the single target for downstream skills that need the de-slop pass without
the full write-well flow.

These rules govern prose, not this doc.

## Sentence-load density

Every sentence carries at least one of: a claim, a number, an example, a
constraint, an image, a consequence, an argumentative move.

Test each sentence: does it do work, or only scaffold, transition, or ornament?
Cut the ones that only scaffold. If the argument breaks without a scaffold
sentence, the surrounding sentences are the problem. Clarify them, then cut the
scaffold.

## Burstiness

Vary sentence length. Prose where every sentence runs the same length reads as
machine output; a human mixes a three-word sentence against a thirty-word one.
After the density pass, check the rhythm. If the sentences have flattened to
one length, break and merge until they vary.

## AI-trace passes

Run in order:

1. **Oral test.** Read aloud. A sentence that is rhythmically broken to say,
   not merely formal, is a rewrite candidate.
2. **Density.** Preserve meaning without padding. "In order to" becomes "to";
   "at this point in time" becomes "now"; "it is worth noting that" is cut.
3. **AI-trace audit.** Ask what makes the text read as machine-written, and
   judge in **clusters**, not isolation. A lone em-dash signals nothing. An
   em-dash plus rule-of-three plus "vibrant tapestry" plus a "Conclusion"
   heading plus every paragraph opening with "It is important to" is a
   confession. Name the cluster, then eliminate it.
4. **Anti-style rewrite.** Remove the flagged cluster. Replace each em-dash or
   en-dash with a period, colon, or parentheses, whichever fits the
   relationship.

## Typographic tells

Governing rule: if you would not type the formatting into a message to a
friend, it probably does not belong.

| Tell | Replace with |
|------|--------------|
| Em-dash | Period, colon, or parentheses. |
| En-dash | Split the construction, or normal punctuation. |
| Curly or "smart" quotes | Straight quotes, or cut decorative quoted material. |
| Ellipsis character | `...` if the pause earns its place; otherwise cut. |
| Mid-sentence ornaments (arrows, bullets, middots) | Words. |
| Excessive bold | One term per paragraph at most, or none. |
| Title Case Headings | Sentence case. |
| A heading every 2-3 sentences | Fewer headings. A heading that titles one sentence is a sentence in a vanity hat. |
| Horizontal rules | A blank line, or none. |
| A table for 2-3 items | One sentence. |

## Evidence-bound mode

Never invent:

- product features, capabilities, or limitations
- dates, version numbers, or timelines
- people, roles, or attributed statements
- metrics, benchmarks, or outcome claims
- workflows, processes, or customer scenarios
- examples that require specific knowledge to verify

Empty value-claims ("faster decisions", "better alignment", "improved developer
experience") are proof gaps. When one appears, ask for the supporting evidence
or label it explicitly as unsubstantiated. Do not launder vague into polished.
