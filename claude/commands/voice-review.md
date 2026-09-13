Edit a document in place against your writing conventions, then report a structured change log so you can absorb the patterns.

> **Placeholder skill.** This was copied from a friend's dotfiles and stripped of his bio, employer paths and personal calibration notes. Everywhere you see `<...>` below, fill in your own facts before relying on this skill. Until then it still runs, but Pass 1 (authority) and the "known locations" list in Pass 4 won't have anything real to check against.

If the user specifies a file, voice-review that. Otherwise, prompt for the file. If the user says "as a learning post" or "--learning", run in learning-post mode (see Mode section).

## This is AI judgement, not a substitution script

The wiki gotchas page contains a table of banned-term → replacement entries. **Do not treat this table as a sed script.** Each occurrence of a flagged term must be read in its sentence context and assessed before any change is made:

- Is the word being used in its **literal technical sense** (the judgement clause applies, keep the word, note in "Banned-but-kept")?
- Is it **filler / marketing colour** (replace, but pick the replacement that fits the sentence's rhythm and register — not always the first column of the table)?
- Does the **sentence as a whole** need rewriting because the banned term is load-bearing? Then rewrite the sentence rather than swap the word.

The table is reference material. The work happens between your eye reading the sentence and your hand making the edit. If the change-log's "Banned-but-kept" section is empty across a long document, that's a red flag: you weren't reading carefully enough. Real prose has technical uses of banned words; the skill should catch and preserve them.

Same principle applies to every other pass — authority calibration, tone, correctness, engagement. Every change is a judgement made in context, never a mechanical find-and-replace.

## Required reading (load before touching the document)

- `~/.wiki/personal/ai-writing-gotchas.md` — banned words, expressions, constructions, em-dashes, judgement clause
- `~/.wiki/personal/uk-tone-writing.md` — steelman framework, hedge non-absolutes, no defensive openers (rename/replace if your tone isn't UK)
- The target document, in full, before editing

No CV/work-experience file is configured. Authority claims (years, roles, tenure) can't be cross-checked against a source file — flag them instead of asserting, unless the claim is the tenure already fixed in this file ("Angular Front-end Developer since July 2017").

If any required file is missing, flag it and proceed with the others. Don't fabricate authority claims from gaps.

## Mode

**Default mode: senior expertise.** Angular Front-end Developer, professionally since July 2017 (9+ years). The voice reads from that seat: observation, teaching, comparison, authority. You share knowledge; you are not the cautionary tale.

**Learning-post mode (opt-in only)**: invoked when you explicitly say "as a learning post", "--learning", or "this is a learning piece". In learning-post mode, the journey from learning to applying is the explicit narrative. Outside this mode, never write yourself learning a thing as an excuse to write about it.

When unclear, default to senior expertise.

## Rules

1. **Edit the document in place** for qualitative passes (voice, AI tells, tone, engagement, spelling convention). These are the passes where the model performs well.
2. **DEFAULT TO FLAGGING, not fixing, for Pass 4 (correctness)**. Numeric claims, identifier names, version numbers, statistics. **Do not auto-correct these.** Open the relevant file, read it, write your finding in the Pass 4 Evidence section of the change log, and let you decide whether to apply the change. This kind of pass has a documented failure mode elsewhere of being wrong on numeric "corrections" most of the time — silent edits to numbers and identifiers are how hallucination ships under your name. Flag-not-fix is the default.
3. **Run all six passes in order.** Each pass has a clear remit; don't skip.
4. **Never fabricate to fix a problem.** If you'd have to invent a fact, flag it instead.
5. **Don't make yourself the cautionary tale** outside learning-post mode.
6. **Tags, publishDate, slug, campaign, series, heroImage, heroAlt, locale, draft, relatedPosts** in frontmatter are hands-off. Title and description are in scope; stay within the original character budget for description.
7. **Em-dashes only where they genuinely fit** (parenthetical aside, appositive, `term — definition` list), never stitching two clauses. Same judgement in every language; don't strip by count.
8. **Every correctness-pass entry in the change log MUST cite the file path you read and an excerpt or paraphrase of what you saw.** If you cannot cite a specific file you opened, the claim is unverified and must be flagged, not fixed. Hand-waving "verified against codebase" is not acceptable. This is the verification gate.

## Passes (run in order, edit in place)

### Pass 1 — Authority calibration

The first and most important pass. Strip framings that undermine your seniority:

- "I made the mistake of..."
- "I tried obvious things and they were all wrong"
- "It cost me a job / a client / every interview"
- "I didn't know X and had to figure it out"
- "I just learned this"
- "I bombed", "I failed", "I didn't pass" italicised confession lines
- Any "I was the candidate who didn't know X" framing for industry-standard libraries or patterns

Replace with senior-practitioner framings:

- **Observation**: "Most apps do X. It works until..."
- **Teaching**: "Your token expires. The app makes a call." (No "Here's".)
- **Comparison**: "The SDK does this in three lines. The custom version takes 600."
- **Authority**: "I've used this pattern across several projects. The reason it works is..."

Exceptions:

- **Learning-post mode**: keep the journey framing. Even here, calibrate so the journey reads as deliberate exploration, not as ignorance.

No CV/work-experience file exists to cross-check against. The one fixed fact is Angular front-end development since July 2017 (this file, Mode section) — any other specific year or role claim must be flagged, not asserted.

**Hard rule**: industry-standard tools are NOT framed as things you just learned. Even if a particular post emerged from a learning moment, the framing is senior comparison, not novice discovery. Strip any line that reads "I didn't know X exists" for any tool that's industry-standard.

### Pass 2 — AI tells

Scan the document against the gotchas wiki page. Strip:

- **Clause-stitching em-dashes** (two independent clauses joined where a full stop or colon belongs); replace those with a period, colon, comma, or parenthesis. Keep em-dashes that genuinely fit (parenthetical, appositive, `term — definition` list). Judge each, never strip by count
- **Banned words** from the canonical list (moreover, furthermore, however, therefore, additionally, leverage, robust, seamless, ensure, delve, foster, and the rest)
- **Banned expressions** ("It's important to note", "That being said", "dive into", "In conclusion", and the rest)
- **Banned constructions** ("It's not X, it's Y" → state the positive)
- **Marketing-adjective compounds** (production-grade, enterprise-grade, mission-critical, future-proof, etc.)
- **Templated openers** ("Let me explain", "Picture this", "Here's the thing", "Imagine this")
- **Templated closers** ("In conclusion", "To summarise", "Hopefully this helped", "Happy coding")
- **Uniform paragraph rhythm**: intro / bold hook / body / blockquote, repeated. Mix short and long. Drop fragments occasionally.
- **Over-bolding**: one bold per paragraph is too many. Keep bolds that act as search anchors in pitfalls / error-message / troubleshooting sections.
- **Recurring 💡 / 🚩 / ⚠️ blockquote rhythm**: fold most into prose. One earned section-closing punchline blockquote at the end of the post is fine if it isn't preceded by 💡 and isn't part of a recurring rhythm.

Apply the judgement clause: keep a banned word only when used in its **literal technical sense** (e.g. "framework" as a software framework, "dynamic" as dynamic dispatch). Note the keep in the change log. Marketing uses of the same word always get replaced.

### Pass 3 — Tone

Apply the framework from your tone wiki page (originally UK-tone; rename or rewrite if yours differs). Known calibration: tends to read as too direct or dismissive of other opinions — the steelman framework below is how that gets corrected, not by inserting self-deprecation.

- **Steelman the opposing view before disagreeing.** Credit what the alternative gets right. Then explain where it stops working for the case at hand. The disagreement still has to land — this isn't about disappearing the opinion.
- **Hedge non-absolute claims.** "X never works" becomes "X's design wasn't shaped around Y". Avoid "never", "always", "impossible" when softer is accurate.
- **Reframe oppositional headers.** "Why X fails" becomes "Where X has limits" or "Where X's design fits a different shape".
- **Frame challenges as questions** where appropriate.
- **No defensive openers.** Drop "To be clear", "Just to clarify", "I want to pre-empt the obvious objection".
- **Bring the reader to your side** rather than dismissing alternatives. The goal of a piece advocating a position is to make the reader want to follow; combative framing makes the reader defensive.

Concrete pattern for any section arguing for a choice: first paragraph credits the alternative; second paragraph names the trade-off that shifts; third paragraph defends the pick on its own terms.

### Pass 4 — Correctness (hallucination prevention)

**Read this first: this pass has a documented history of being wrong on quantitative "corrections" more often than not.** Voice-review has previously shipped hallucinated "corrections" elsewhere (renaming real identifiers, replacing correct counts with arbitrary ones, swapping methodology mid-document). All of those failures had the same root cause: running a grep, not opening the matching files, and substituting a count for the document's own. **This pass defaults to flagging, not fixing.**

**Default behaviour for Pass 4:**

- **Qualitative correctness** (does this sentence make sense, is the argument structurally sound, is the punctuation right): fix in place, normal.
- **Quantitative correctness** (numeric counts, identifier names, version numbers, file paths, percentages, statistics, performance claims): **flag, do not fix**, unless the change log can cite a specific file you opened and read.

The asymmetry is deliberate. A flagged claim is recoverable (you review, decide, apply). A silently-edited wrong claim ships under your name. Fail toward the recoverable outcome.

This pass should read like human review: open the file, scan the surrounding code, confirm or refute the claim, write up what you found. Speed at this pass is not a virtue. Skipping the read step is the failure to guard against.

**Required workflow for every concrete claim** (code identifier, library API, version, file path, statistic, count, performance number):

1. **Find candidate evidence with grep, using multiple patterns.** Identifier-style claims need a *bare-word* search (`grep -rE "\bIdentifier\b"`) AND a declaration search (`class X`, `function X`, `const X =`, `export X`) AND an import-side search (`from '...'`). One pattern returning nothing doesn't mean the thing doesn't exist; it means *that pattern* found nothing.

2. **OPEN the files grep returned and read them.** Not the line grep matched in isolation — the surrounding 20-50 lines. Confirm the match is the thing the document is talking about, not a mock, not a test stub, not a same-named-different-thing, not a comment.

3. **Trace identifiers to their source.** If the document names `Foo`, find where `Foo` is *defined*, not just mentioned. Read the import path. Open the file the import points at. Confirm the actual class/hook/type.

4. **For numeric claims, count via at least two methodologies, then open files to verify.** A directory can hold one, two, or zero wrappers. Grep counts lines, not files, not consumers. Open a sample.

5. **Cross-check against the document's neighbouring numbers.** If the document says "3 Apollo + 18 TanStack + 0 RTK" and your methodology gives 3 for Apollo (matches) but 14 for TanStack (doesn't), the methodology in use is whatever produces 3 for Apollo. Use that same methodology for TanStack — or don't substitute at all.

6. **Decide: leave-as-is, flag, or fix-with-evidence.**
   - **Leave-as-is** is the default for any numeric or identifier claim where you can match the document's methodology and its number stands under it.
   - **Flag** is the next default. Most claims you can't verify confidently belong here. Pass the question to the user with what you checked and what you couldn't.
   - **Fix-with-evidence** is the *last* option, and it requires:
     - You opened a specific file and read it
     - The file's content unambiguously contradicts the document's claim
     - Your fix is consistent with the document's methodology elsewhere
     - The change-log Evidence section cites the file path AND an excerpt/paraphrase of what you saw
   - If any of those conditions isn't met, flag instead of fix. Wrong-correction-shipped is worse than annoying-flag-for-review.

**The failure modes to avoid (generic, not this user's history yet — replace with your own once you have one):**

- *"I greped for `class StateManager` and found nothing, so the identifier doesn't exist."* — Wrong if the class lives in a workspace package imported across many files. The right grep would have been `\bStateManager\b`. The right *next step* after grep would have been to open one of the importing files and follow the import path.
- *"I counted 6 sub-directories + 1 root file = 7 wrappers."* — Wrong if sub-directories can contain multiple wrappers. The right next step is `ls` each sub-directory to verify one-wrapper-per-directory.
- *"I counted 15 matching grep lines from an import."* — Off by one if a file has two import statements. Line count ≠ file count. The right next step is `grep -rl` (files) AND open a few to confirm they're all genuine consumers.

**Known codebase locations to check before flagging anything as "unverified"**:

- `~/Developer/dotfiles/` — this dotfiles repo (RAG, scripts, configs)
- `~/.wiki/` — curated wiki for facts and decisions, once you have one
- No blog/portfolio repo and no employer repo are configured yet. For claims about other projects, check GitHub directly (`gh repo view`, `gh search code`) rather than assuming a local path exists.

For library API claims, check the installed package's `package.json` for the version, then **open the package's `node_modules/<pkg>/dist/*.d.ts` types** and read the actual exported shape. Don't trust your memory of an API; the version installed might pre-date or post-date the API you're thinking of.

For code blocks specifically:
- Verify identifiers (function names, class names, exports) exist in the linked repo *by opening the file they're defined in*, not just by grep
- Verify imports resolve to real packages (open `node_modules/<pkg>/package.json`)
- Verify API shapes match the current installed version (read the `.d.ts`)
- Verify file paths exist (`ls` the path, don't assume)

**Be honest in the change log about what you actually checked.** "Verified against `path/to/file.ts` lines 1-50" beats "verified against codebase" because it tells the user *what file you read* and lets them check your work.

### Pass 5 — Engagement / retention

For blog posts and slide decks especially, but applies to any longer-form artefact. Without changing the core argument:

- **First paragraph hooks with the concrete payoff.** State what the reader gets if they stay. No long preamble. No "let me set the stage".
- **Front-load the most useful idea.** Don't bury under setup. The reader's attention is highest in the first 100 words.
- **Subheadings signal payoff, not topic.** "How the token refresh actually works" beats "Token refresh". "Where one-store hits its limits" beats "Limitations".
- **Cut padding.** If a paragraph repeats the previous one in different words, delete it.
- **Break up walls of text** with short sentences, fragments, or a code block.
- **Tutorials**: signpost the journey. Number the steps. State what the reader has built at each milestone. Readers drop off when they lose the thread.
- **Slide decks**: each slide should earn its place. Bullets should land payoffs, not list topics. Presenter notes are spoken scripts (follow existing convention; not editorial commentary).
- **End on something concrete**: a takeaway, a working result, a question worth thinking about. Not "Hopefully this helped". A single earned punchline blockquote at the close is fine.

If the doc is tagged with retention concerns ("readers aren't reaching the end", "this feels dry"), elevate this pass: be more aggressive on padding, more deliberate on signposting.

### Pass 6 — Spelling consistency (US English)

Behavior, color, organization, optimized, recognize, license, analyze, modeled, prioritize, favorite, defense, program. Match across the document; don't touch quoted code, library names, or upstream identifiers.

## Output — structured change log

After editing, report under 500 words. Be specific so you can absorb the pattern and double-check the correctness work.

```
**Mode**: senior expertise | learning post
**Word-count delta**: +X / -X
**Document type tag**: tutorial / easy-style / essay / deck / artefact

**Authority calibration**:
- Cautionary-tale framings stripped (line N → senior observation)
- Authority claims cross-checked (no CV file configured — flagged instead: ...)

**AI tells removed** (rough count by category):
- Clause-stitching em-dashes fixed: N (legitimate em-dashes kept) · Banned words/expressions: N · Templated openers/closers: N
- Marketing-adjective compounds: N · Decorative blockquotes folded: N · Stylistic bolds stripped: N

**Tone fixes**:
- Steelmans added (which alternatives, which sections)
- Oppositional headers reframed (which → which)
- Defensive openers dropped

**Correctness — fixed** (evidence required for each entry, otherwise demote to "flagged"):
- [Claim that was changed] → [new value]
  - File read: `path/to/file.ts` lines N–M
  - What I saw: [excerpt or one-line paraphrase]
  - Why my fix matches the document's methodology: [...]
- [next entry]

**Correctness — flagged, NOT fixed** (default for most numeric/identifier claims):
- [Claim in the doc] → [my measurement] under [methodology I tried]; under [alternative methodology] I got [different number]. Methodology mismatch means I can't substitute confidently. Recommend you verify under your original methodology.
- [Suspect claim] → opened `path/to/file` but couldn't find the referenced thing. Possibly: [hypothesis]. Flagging for review.

**Engagement restructure**:
- Opening reshaped (was → now)
- Subheadings sharpened
- Padding cut

**Spelling (US English)**: count of inconsistencies fixed

**Banned-but-kept** (judgement clause):
- Banned words kept for literal technical use, with reasoning

**Out of scope / unverifiable**:
- External claims (release dates, vendor policies, CVE scores)
- Bundle-size or perf claims needing instrumentation
- Self-hosted infra config not in this repo
```

**The verification gate**: every entry under "Correctness — fixed" MUST have an Evidence section (file read + what you saw). If you can't produce that, the entry belongs under "Correctness — flagged" instead. No exceptions. A change log with five fixed entries and zero Evidence subsections is a failed run — go back to Pass 4 and either gather the evidence or move them to flagged.

## What NOT to do

- Don't invent or speculate. Flag, never fabricate. This applies especially to dates, statistics, code identifiers, and personal facts.
- Don't add new sections or new examples. Clean, calibrate, correct, tighten. Restructure within the existing scope.
- Don't make yourself the cautionary tale outside learning-post mode, unless that's a deliberate choice.
- Don't add AI / Claude / ChatGPT references in the body of any document, except posts that are literally about those tools.
- Don't touch `tags`, `publishDate`, `slug`, `campaign`, `series`, `heroImage`, `heroAlt`, `locale`, `draft`, `relatedPosts` in frontmatter.
- Don't downgrade the technical claim to make a sentence read more humble. The voice softens; the expertise doesn't.
- Don't summarise back what the user said as if it were a finding. The summary is for new information they can learn from.
