---
name: ambitious-founder
description: Juwen's combined /be-ambitious + /founder skill. (A) Ambition pass on any task or prompt - Altitude (goal beyond the goal), Depth (work like the field's best, from raw data, outside judge), Range (borrow other fields' methods) - then a rewritten prompt and the work. (B) Founder pipeline that pressure-tests a business or product idea: board (Offers/Monopoly/Product + Make lens for hardware), competitors, simulated buyer panel, Van Westendorp pricing, offer, CFO unit economics, marketing, brand, ops, launch test, and a plan with a script-computed verdict. Use for /ambitious-founder, /be-ambitious, /founder, /founder-<stage>, "aim higher", "go deeper", "test my business idea", "would people buy this", "unit economics", "is this profitable", "business plan".
---

# Ambitious Founder

Two MIT-licensed Claude skills merged and adapted to Vector:

- **be-ambitious** by RoboNuggets (github.com/robonuggets/be-ambitious), built on
  Felix Rieseberg's article *How to be more ambitious: a tutorial for humans with
  models* (13 Oct 2026). The types, the Depth prompt and the warnings are his.
- **founder-skill** by Jake Schincariol (github.com/Jakeschincariol/founder-skill):
  eleven founder stages and four standard-library Python tools, bundled here in
  `tools/`. Licenses in `licenses/`.

`SKILL_DIR` = the folder that contains this file (Vector: `~/.vector/skills/ambitious-founder`,
Claude Code: `~/.claude/skills/ambitious-founder`). Works in Vector, Claude Code, Codex,
OpenCode and SkillMouse; hosts without tools use **Single-response mode** at the end.

## The rules (both halves, never broken)

1. **Better, not bigger.** Raise the outcome, the standard or the set of
   perspectives. Never just add deliverables, features or side quests.
2. **Do what the expert does, not how they talk.** Use the field's methods and
   instruments. Vocabulary without method is role play.
3. **An outside judge decides.** Never grade your own work. A test, a measurement,
   a script, held-out data, a real buyer. In the founder pipeline the judge is the
   computed verdict (`compile.py`) plus a real-world test (pre-orders, pilots).
4. **Treat the hard target as reasonable, report honestly.** A missed hard target
   with real numbers is a good result; a faked one is not. Never round a failing
   number into a passing one.
5. **No invented facts.** No made-up competitors, prices, reviews, quotes, market
   sizes or budgets. Mark estimates as estimates with reasoning; link sources.
   If data or access is missing, name exactly what and what it would unlock.
6. **Lenses, not people.** The board applies published frameworks. Write "the
   Offers lens", never "Hormozi says". Never quote or speak as them.
7. **Simulated buyers are not customers.** The panel finds objections, segments
   and wording; its buy rate is an upper bound (models lean agreeable). Never use
   panel answers as testimonials.
8. **Ambition raises the standard, not the permissions.** Ask first when a step
   replaces what the user asked for, spends money, contacts people or can't be
   undone. Not financial, legal or tax advice - say so once where it matters.

## Pick the mode

- `/be-ambitious <task>` or "aim higher / go deeper" → **Mode A**.
- `/founder`, `/ambitious-founder <idea>`, "test my business idea" → **Mode B**,
  starting with a short Mode A pass on the idea itself.
- `/founder-<stage>` (board, competitors, consumer, pricing, offer, cfo,
  marketing, brand, ops, launch, plan) → run that stage of Mode B alone; it reads
  whatever already exists in `founder/`.
- `/founder-studio` → open **Founder Studio** (Stage 3 to 11 made visual): run
  `python SKILL_DIR\studio\server.py --root founder` and give the user the URL it prints.
  See "Founder Studio" below.
- Nothing after the command → use the user's most recent request; if none, ask
  for it in one line and stop.

---

# Mode A - Ambition pass

Decide what you were handed: **a task to do** (plan at the ambitious level, then
do it) or **a prompt to improve** (stop after the rewritten prompt). If unclear,
stop after the rewrite.

## Pick the types that fit (usually one or two; Speed is skipped)

| Type | Fits when | Skip when |
|---|---|---|
| Altitude | The task serves an outcome (people hold meetings about it) | Creative work with no outcome beyond itself |
| Depth | The task should be done really well | Throwaway work |
| Range | The result must land with people, or the obvious field ran out of ideas | A narrow fix with one right answer |

**Altitude - aim at the outcome.** What does the user want to happen next? Build a
three-rung ladder: (1) understand, don't just fill in; (2) get to the decisions;
(3) replace the ritual with a durable system that takes the human out of the loop
(name the setup it needs). If a rung has no outside judge, step down one rung.

**Depth - work like the field's best.** Go one level below the task. Answer
Felix's four questions:
1. What would a top professional do here that the user isn't asking for?
2. What is the rawest material they'd start from (not the digested version)?
3. Which specific methods and tools would they use?
4. What, other than you or the user, would show the result is right?
Then set an unreasonable target and treat it as reasonable (asked for 5 s? aim
for 200 ms). Challenge the shared belief against raw data. Look for new knowledge.

**Range - bring in other fields.** Replace the nouns with verbs ("a QBR deck" →
"getting busy people to believe a cause-and-effect story and decide in 30
minutes"); the verbs reveal which fields help. Assemble the crew (quality, delivery,
red team). Borrow their tools, not just ideas. Do, don't play. If the host can
launch sub-agents, give each field its own; otherwise (Vector, SkillMouse, plain
chat) run each field as a separate, explicit pass with its own method and tool,
and keep their findings separate before merging.

## Depth instruments (Vector and other tool-using hosts)

Reach for real instruments, not markdown opinions: the `python` tool (numpy,
scipy, sympy, pandas, pint, CoolProp, shapely, networkx) for models and
statistics; `web_search` for verified references and standards; CAD integrations
for real geometry - mass properties, interference/clearance, rebuild health,
parameter sweeps; slicers for print time and material. For engineering tasks,
typical outside judges are a hand calc that matches FEA/CAD within a stated
tolerance, a measured print or prototype, a tolerance stack-up, or a standard's
test criteria. Follow the Engineering behavior rules (no experiment documents
without approval, never leave a user's model altered).

## Mode A output (size it to the task)

1. **Goal beyond the goal** - one line.
2. **Types that fit** - one line each on why; name the skipped ones.
3. **The plan** - Altitude ladder / Depth's four answers + hard target / Range
   verbs and crew (field → the job they'd actually do → their method or tool).
4. **What it needs** - data, tools, access: marked *have* or *missing*.
5. **Rewritten prompt** - one fenced block the user can copy, written as they'd
   type it, ending with the outside judge and what counts as a pass.
6. **Next** - the highest rung you can finish and check with current access.
   Prompt-to-improve: name it and stop. Task: name it in one line and start.

---

# Mode B - Founder pipeline

Everything lives in a `founder/` folder in the project folder (or the chat's
working folder if no project is set). Each stage reads what the others wrote.

```
ambition -> board -> competitors -> consumer -> pricing -> offer -> cfo -> marketing -> brand -> ops -> launch -> plan
```

Run the whole chain only when asked; otherwise run the next useful stage and
suggest the one after. Tools need Python 3.8+, standard library only, no network:

```powershell
$T = "<SKILL_DIR>\tools"
python "$T\panel.py" --dir founder\panel <init|prompts|check|save|tally|status>
python "$T\unit_economics.py" founder\numbers.json --out founder\cfo.md [--price X] [--volume 0.8]
python "$T\van_westendorp.py" founder\panel\answers --price X --out founder\pricing-curve.md
python "$T\compile.py" --dir founder [--min-buy-rate 0.25] [--check]
```

Examples to copy the shape from: `SKILL_DIR\examples\numbers.example.json`,
`customer.example.json`, `pitch.example.md`. Self-test: `python -m unittest
discover -s tests -v` from `SKILL_DIR`.

## Stage 0 - Ambition pass on the idea (`founder/ambition.md`)

Mode A, aimed at the business: goal beyond the goal (not "open a shop" but e.g.
"own this segment in this city"), the Altitude ladder (sell one unit → a
repeatable channel → a durable system/moat), the Depth hard target (e.g. the real
unit margin at the real volume, from real quotes), and the Range crew = the
stages below. Write the outside judge now: the verdict checks + the success line
for the launch test.

## Stage 1 - Board (`founder/idea.md`, `founder/board/`, `founder/board.md`)

1. `idea.md`: what it is (one sentence), who it is for (specific), what it sells
   at what price, where and how, budget and constraints. If name, customer,
   product or price is missing, ask (max three questions in one message). Never
   invent a budget, market size or competitor.
2. `board/brief.md`: a self-contained brief, no opinion of yours added.
3. Convene: read `SKILL_DIR\lenses.md`. Write one memo per lens - one sub-agent
   per lens if the host has them, otherwise **separate passes** - each applying
   ONLY that lens, to `board/<lens>.md`:
   `Score 1-10 | Vote FUND / FUND IF / PASS`, What is strong, What would kill it
   (top 3), Questions for the founder, Conditions (if FUND IF). Use the Make lens
   only for physical products.
4. Chair's summary `board.md`: the vote and average score, risks raised by more
   than one member first, all conditions merged into a checklist, and one
   paragraph on the strongest version of the business (say plainly if it differs
   from the pitch). Keep disagreements. A PASS is a result.

## Stage 2 - Competitors (`founder/competitors.csv`, `founder/competitors.md`)

Use `web_search`. Public sources only, every fact linked, quotes verbatim and
short. 5-10 direct + indirect competitors plus the main substitutes. CSV columns:
`name,type,url,location_or_channel,price_of_comparable_item,what_it_sells,positioning_line,rating,review_count,source_date`.
For the top 3-5, read 1-3 star reviews then "love it, but" 4-stars; group
complaints into themes with counts and linked quotes; mark thin evidence. End with
the gap: what buyers want that nobody gives them. If a source can't be reached,
say so.

## Stage 3 - Consumer panel (`founder/customer.json`, `founder/pitch.md`, `founder/panel/`)

1. `customer.json` (shape: example): `business`, `target`, 2-4 `segments`
   (share, income range), 4-8 `behaviours` (share, how), 4-8 real `objections`,
   optional `habits`. Ground it in user knowledge and competitor complaints; say
   which parts are guesses. Show it to the user and let them correct it first.
2. `pitch.md`: 3-6 plain lines - product, price, where/how, opening offer. No
   superlatives, nothing undeliverable.
3. Deal and brief: `panel.py init --customer founder\customer.json --pitch
   founder\pitch.md --n 20` (default to 20 for a first look; 100 only if asked),
   then `panel.py prompts`.
4. **Run buyers.** With sub-agents (Claude Code): one sub-agent per brief, in
   waves of 10, each told only "Read <brief path> and follow it exactly."
   Without (Vector, plain chat): answer each brief in its own isolated pass - read ONLY `founder\panel\briefs\<id>.md`, do not look at other
   answers or the tally, answer as that buyer per the brief, and file the JSON
   with `panel.py save <id>` (JSON on stdin; it rejects invalid answers). Process
   buyers in the order `prompts` lists them. Never edit a brief, never
   "correct" an answer afterwards. Tell the user once that one model playing all
   buyers is less independent than separate agents, so the buy rate is an even
   looser upper bound.
5. `panel.py check`, redo only broken ones, then `panel.py tally` →
   `results.md` / `results.json`.
6. Report: "N buy · M pass" and the rate; the segment/behaviour rows that differ
   most; top three pass reasons with one quote each; what would flip a no; one
   sentence on what to change and which stage does it. State the honest limits.

The same `customer.json` also drives /hone's reviewer bots (`~/.vector/skills/hone/bots/README.md`):
the personas review the built app's screenshots and their fix list drives an auto-fix loop.

## Stage 4 - Pricing (`founder/pricing-curve.md`, `founder/pricing.md`)

Run `van_westendorp.py` on the panel answers (or a real survey CSV with
`too_cheap, cheap, expensive, too_expensive` - real beats simulated). Report PMC,
OPP, IPP, PME; PMC→PME is the acceptable range. Compare like-for-like competitor
prices (linked). Run `unit_economics.py --price` at 2-3 candidate prices. Decide:
the price and why, what to test, and the price you won't go below (variable cost
+ margin floor). If the panel hasn't run, say so; don't invent a range.

## Stage 5 - Offer (`founder/offer.md`)

Offers lens as method. List 15-30 obstacles in the buyer's words (before, during,
after buying), mostly from panel objections and competitor complaints. Turn each
into a solution; score value (1-5) and cost to deliver (1-5, from the CFO
numbers); keep high-value low-cost. Stack: core (named by outcome), 2-3 bonuses
each killing one objection, a guarantee (cost it at a realistic claim rate with
the CFO tool), urgency/scarcity only if true, a clear offer name. Score the value
equation before/after, then re-run a quick panel on the new pitch and compare buy
rates.

## Stage 6 - CFO (`founder/numbers.json`, `founder/cfo.md`, `founder/cfo-sources.md`)

`numbers.json` fields: `unit`, `price`, `variable` (cost of ONE unit),
`fixed_monthly`, `startup`, `plan_per_day`, `ramp_per_day` (12 months),
`capacity_per_day`. Free or tips-only product: set `"model": "free"` (or `"tips"`, or `price` 0) with
`fixed_monthly`, `users_per_month`, `supporters_pct`, `avg_tip`; compile then judges tips vs running cost
and the panel, and the best verdict is "Sustainable (free)". Sources in order: user's quotes/invoices → checkable public
prices (log each in `cfo-sources.md`) → marked estimates with reasoning. The ramp
is where plans lie: sanity-check it against the panel's buy rate and first-month
purchases. Run the tool; it flags price below variable cost, break-even above
capacity, losing year 1, payback beyond 12 months. Write the CFO's note at the top
of `cfo.md`: the margin and contribution per unit, the line to watch (with the
what-if that proves it), cash needed, three ways to improve the margin (each with
a run what-if, not a guess), whether the board's money conditions are met.

**Physical products (Make lens):** `variable` = landed unit cost (BOM at planned
volume + assembly + test + packaging + freight + duty + yield loss + warranty
reserve); `startup` includes tooling/moulds, fixtures, certification and the first
MOQ run; `capacity_per_day` = the supplier's or line's real output. If a CAD model
exists, pull mass/volume and part count from it (via the connected CAD app) to
ground material and freight cost, and list the DFM changes that cut the BOM.

## Stage 7 - Marketing (`founder/marketing.md`)

Read the panel, competitors, offer, pricing and numbers; if missing, say so - don't
invent an audience. Positioning: three versions of "For <top-buying segment>, who
<problem in their words>, <business> is the <category> that <gap>, unlike
<nearest alternative>", recommend one with panel evidence. Pick 2-3 channels where
that segment really spends attention (why it fits, rough cost, how you'll know it
worked; say what you're not doing). A dated calendar from launch -14 to +16 days,
ten hooks each answering one objection, and the max affordable cost per customer
from the CFO numbers.

## Stage 8 - Brand (`founder/brand.md`)

Ten name candidates across styles → shortlist three with the checks the user must
finish: trademark search links and classes per market, domain and handle
availability (check, don't assume), no confusion with competitors. Say a
trademark lawyer confirms it. Promise, three taglines, voice in three adjectives
with do/don't and a before/after rewrite of a pitch line. Look brief: 2-3 colours
with hex and WCAG AA contrast, display + text typefaces, logo direction.

## Stage 9 - Ops (`founder/ops.md`)

Daily cycle (mark customer-visible steps); 2-3 real suppliers per input with
public prices or how to quote, MOQs, lead times, terms (linked) - update
`numbers.json` and re-run the CFO if real prices differ; people and rota (wage
source linked, payroll extras flagged for the accountant); one-page SOPs for the
make-or-break moments; the smallest tool stack with published prices; licences,
permits, insurance checklist for the user's location; a risk register with
owner and mitigation. For hardware: supplier qualification, incoming inspection,
first-article and production test plan.

## Stage 10 - Launch (`founder/launch.md`)

Cheapest real test first, with the success line written before it runs (e.g. "50
pre-orders in two weeks at $X"): pop-up/stall/pre-order list for a shop; landing
page with price and pre-order/waitlist for online; three paid pilots for services;
founding-member offer for subscriptions; for hardware, a crowdfunding or
deposit-backed pre-order with a working prototype (a printed/CNC prototype from
the CAD model is the cheapest credible proof). If real buyers fall well short of
the panel, trust the real buyers and go back to offer/pricing. Then the dated
countdown with owners and the critical path, the launch-day run sheet, and the
first 30 days with the numbers to watch weekly.

## Stage 11 - Plan (`founder/summary.md`, `founder/business-plan.md`, `founder/one-pager.md`)

`compile.py --dir founder --check` first to see what's missing; name the stage
that fills each gap - never fill a section from guesses. Write `summary.md` (half a
page: what and for whom, the verdict and its three numbers, where board and panel
agreed/disagreed, the biggest risk and response, cash needed, the one thing to do
this week; if Not yet, lead with what must change). Then `compile.py --dir
founder` → `business-plan.md`. The verdict - Profitable / Not yet / Incomplete -
comes only from the script: every unit earns money, year 1 profits, break-even
fits capacity, enough of the panel buys. Never write Profitable by hand. Then the
`one-pager.md` for a two-minute reader, same numbers word for word.

## Founder Studio (`SKILL_DIR\studio\`, optional)

A local web app on the same files and scripts: 3D buyer bots walk to BUY or PASS, then Results, Pricing,
Numbers, Competitors, A/B offer (same seed) and Verdict tabs. Standalone repo: github.com/juw12/founder-studio.

- Start: `python SKILL_DIR\studio\server.py --root founder` (one project) or `--root <folder of ideas>`.
  Python stdlib only; three.js is bundled. It uses this skill's `tools/`.
- Quick sim is a seeded heuristic (labelled, never counts). AI buyers use the user's own key or Ollama and write
  `panel-ai/`; only the user's explicit "make this the official panel" replaces `panel/`.
- The Verdict tab runs `compile.py`, so the rules above still hold. Use it to show the panel and to try offers;
  never to bypass a stage.
- Review loop tab: the board lenses (Offers, Product, Monopoly) plus a clarity check and the CFO lens act as
  reviewer bots in the arena. They post FIX / OK / YOUR CALL, an editor applies the fixes, the same buyers
  (same seed) judge each version, and only a version that wins more buyers is kept (rule 3: reviewers
  suggest, buyers judge). It never invents facts (slots or "(confirm)"), never changes the price, and only
  replaces the pitch when the user presses *Use as my pitch*. Writes `review-loop.md`; never counts for the verdict.
- Smoke tests: `python SKILL_DIR\studio\test_api.py`.

## Ending every Mode B run

One line with the result (the vote, the buy rate, the margin, or the verdict),
the outside-judge status (what was checked by a script or a real test vs what is
still simulated/estimated), and the single next step. Name every file written
with its full path.

---

# Single-response mode (no tools: SkillMouse, plain chat)

When the host can't run scripts, search the web or launch sub-agents, do it all in
one answer and label what is simulated:

1. **Selected text is a task or prompt** -> Mode A output (goal beyond the goal,
   types, plan, needs, rewritten prompt, next). This is the main use in SkillMouse.
2. **Selected text is a business or product idea** -> a compact founder pass:
   - Ambition line + the outside judge (what real test would prove it).
   - Board: the four lenses from `lenses.md` (Make lens only for physical
     products), each with score, vote, top kill-risk, one condition.
   - Unit economics by hand, showing the formula with the user's numbers:
     contribution = price - variable cost per unit; break-even units per month =
     fixed monthly costs / contribution; months to pay back = startup cost /
     (monthly contribution - fixed). Missing inputs are listed, never invented.
   - Quick panel: 8-10 one-line buyer reactions from distinct segments, honest
     not agreeable, tallied - labelled **simulated, upper bound**.
   - Verdict in words only ("looks viable / not yet / missing data") with the
     failing numbers; say the scripted verdict needs the full skill
     (github.com/juw12/skills, `skills/ambitious-founder`).
   - The cheapest real-world test to run this week, with its success line.
3. Never present estimates as facts, panel answers as customers, or lens votes as
   the named authors' opinions.
