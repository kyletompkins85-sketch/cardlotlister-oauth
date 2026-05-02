# 2025 Bowman Classifier Notes

Working document for raw thoughts, hypotheses, edge cases, and classification decisions.

Goal: capture nuance first, structure later.

## Context

- Dataset snapshot: `data/cardmatch_pilot/2025_bowman/20260501_full/term_search_items_export.csv`
- Checklists: full normalized rows in `data/checklists/normalized/2025_Bowman_Normalized.csv`; compact number → player → `card_type` line in `data/checklists/normalized/2025_Bowman_card_number_lookup.csv` (same idea as `bowman_cards.csv`, kept for classifier alignment).
- Steps 1–2 (exclude + checklist code match): `scripts/cardmatch/run_2025_bowman_retail_steps12.py` → writes full `listings_steps12.csv` next to the input export, then one **review** CSV per `match_status` under `step2_by_match_status/` with columns only `card_number`, `player_name`, `card_type`, `listing` (logic in `cardmatch/bowman_2025_retail_steps.py`). Re-split only: `scripts/cardmatch/split_listings_steps12_by_match_status.py`.
- This file is intentionally lightweight and iterative.
- Prefer recording reasoning over rushing implementation.

## Current Focus

- Build a robust way to classify 2025 Bowman listing titles.
- Avoid premature rule coding until the logic feels stable.

## Notes (chronological)

### 2026-05-01

- Initial notes file created.
- Plan is to capture thought process first, then convert into implementation guidance later.
- Ad-hoc normalization hypothesis: team names containing color words can create false color signals.
  - Examples: `Blue Jays`, `Red Sox`, `White Sox`.
  - Potential approach: strip or mask these phrases early in normalization so they do not influence color/parallel inference.
  - Rationale: likely low signal for card-type classification, high risk of introducing noise.

## Open Questions

- What is the exact target taxonomy for 2025 Bowman (labels and precedence)?
- How should we handle ambiguous listings that match multiple possible classes?
- What should be excluded from classification scope? (See **Excluded listings** below.)

## Candidate Ideas

- (Add ideas here as they come up)

## Mental model: card vs modifiers

Helpful framing for classification (and for rules later):

- **Card** — the stable identity: stock line + checklist code + player (when known). Example: `BP-1` Walker Jenkins is one *card* in the sense of “which slot on the checklist / which product line.”
- **Modifiers** — everything layered on top of that card: parallels (colors), patterns, serials, print types, grade, lot language, etc. Examples for the same card slot: sky blue, neon green, black, orange, pattern, refractor, `/99`, printing plate, etc.

Splitting the problem this way keeps “which card line / code” separate from “which parallel or variant,” and makes it easier to reason about conflicts (e.g. team color words vs parallel colors) and precedence.

## Prediction pipeline (hypothesis)

Four **sequential** steps (each step can pass forward structured state, e.g. normalized title, spans, confidence):

1. **Exclude** — drop or tag listings per **Excluded listings** below (lots, pick-your-card, etc.). Cheap gate before any player/card work.
2. **Player** — predict player from **title text / description plus card number** (checklist codes like `#`, `BP-`, `BCP-`, auto suffix patterns, etc. help anchor which roster slot).
3. **Card** — predict **which card** (set line + checklist identity: base vs prospect vs chrome line, auto vs non-auto, insert family, etc.) using **player + card number** (and remaining title context as tie-breaker).
4. **Card version** — predict **parallel / pattern / print / serial** (“modifiers”) using **keywords** (and `/N`, `x/N`, etc.) once the card slot is fixed — reduces color/pattern noise affecting earlier steps.

Notes:

- Order matches the mental model: exclusions → identity → slot → modifiers.
- If a step is low-confidence, we can still defer to later steps or a second pass (e.g. rare cases where insert wording helps disambiguate card line).

## Excluded listings (out of scope)

Listings we likely want to **exclude** from single-card classification, training slices, and “card + modifiers” labeling — or to bucket separately so they do not pollute stats.

Working list (add more as we discover them):

- **Lots** — multi-card, “lot of N,” bulk, etc.
- **Pick your card / U-pick** — seller inventory, choose one, pick one, “you pick,” etc.
- **Set builder / complete your set** — not a single defined card.
- **Complete sets** — full or partial set listings, not one card slot.
- **Presale / pre-order** — if we want comps only from in-hand listings.
- **Graded / slab** — PSA, BGS, SGC, CGC, “graded,” “gem mint,” etc., if the goal is raw title semantics for parallels (optional policy).
- **Multi-SKU / volume headers** — inserts volume discounts, “singles - volume,” minimum N cards, etc.

Policy notes (TBD):

- Decide per use case: hard exclude vs tag-but-keep for analytics.
- Align phrasing with whatever we already use elsewhere (e.g. Bowman Draft pilot “listing counts” exclusions) when we wire rules.

## Set Distinction Sections (working catalog)

Use this section to track the distinct 2025 Bowman set lines and insert/auto families.

- Base (`#`)
- Base Prospects (`BP`)
- Chrome Prospects (`BCP`)
- Base Prospect Autos (`BPA`)
- Base Rookies and Veterans Autos (`PRV`)
- Chrome Prospect Autos (`CPA`)
- Chrome Rookie Autos (`CRA`)
- Hobby Stars Autos (`HSA`)
- Retrofactor Autos (`CPR`)
- Rockstar Rookie Autos (`RRA`)
- Rookie of the Year Favorites (`ROY`)
- Very Important Prospects (`VIP`)
- Anime (`BA`)
- Anime Kanji (`BA`) (Japanese players subset)
- Scouts Top 100 (`BTP`)
- Spotlights (`BS`)
- Crystalized (`BWC`)
- Etched in Glass Variations (follow underlying card line, either `#` or `BCP`)
- Greatness Loading (`GL`)
- Hobby Stars (`HS`)
- Rockstar Rookies (`RR`)

Auto vs non-auto card-code distinction (important):

- Auto cards: code after dash is player initials (2-3 letters).
  - Example: `CPA-JW` -> JJ Wetherholt auto.
- Non-auto cards: code after dash is numeric.
  - Example: `BCP-22` -> JJ Wetherholt non-auto.

Base card parallel/print details:

- Base cards have 13 colors:
  - sky blue
  - neon green
  - fuchsia
  - purple
  - pink
  - blue
  - green
  - yellow
  - gold
  - orange
  - black
  - red
  - platinum

- Base cards have 1 color modifier:
  - `pattern`
  - Can combine with: purple, blue, green, yellow, black.

- Base cards have 2 unique prints:
  - retro logo foil
  - printing plates

Scope clarification:

- The distinctions above apply to both:
  - Base veterans/rookies (`#1`, `#2`, `#3`, ...)
  - Paper prospects (`BP1`, `BP2`, ...)

- Paper autos (`BPA`) use different color options from non-auto paper/base cards.

Paper/base auto color set (applies to both prospects and rookies/veterans autos):

- purple
- blue
- green
- gold
- orange
- red
- platinum

Chrome variation details (working list):

- Chrome has broader variation options than paper/base.

- Colors:
  - purple
  - fuchsia
  - blue
  - aqua
  - green
  - yellow
  - gold
  - orange
  - rose gold
  - black
  - red

- Patterns:
  - geometric (possible for: purple, yellow, blue, gold, green, orange, black, red)
  - lava (possible for: no color, red)
  - reptilian (possible for: no color, fuchsia, blue, green, gold, orange, red)
  - shimmer (possible for: blue, aqua, green, gold, orange)
  - grass (possible for: green)
  - raywave (possible for: purple, blue)
  - wave (possible for: no color, fuchsia, yellow)
  - mini diamond (possible for: no color, rose gold)

- Unique prints / special variants:
  - xfractor
  - speckle
  - refractor
  - steel metal
  - pearl
  - snackpack (gumball, peanuts, popcorn, sunflower seed)
  - firefractors
  - superfractors
  - printing plates

## Paper vs Chrome Clues (working list)

Critical distinction for 2025 Bowman classification:

- `Base/Paper` vs `Chrome` should be treated as a first-order decision.
- There are likely many subtle textual clues that indicate one vs the other.
- We want all such clues documented in this single section before rule implementation.

Known clue categories to capture:

- explicit product words (e.g., "chrome", "paper", "base")
- card-number patterns and set-line indicators
- insert/parallel terms that strongly imply chrome stock
- misleading/ambiguous terms that often cause false signals
- exceptions and conflict-resolution heuristics

Working note:

- This section is intended to become the central reference for stock-type inference logic.

Current explicit heuristics (from working notes):

- If title includes `Chrome`, classify as `Chrome` (not Base/Paper).
- If title includes `Paper`, classify as `Base/Paper` (not Chrome).
- If title includes `true blue`, `true red`, etc., classify as `Base/Paper` (not Chrome).

Card-number and prefix clues (high-signal):

- Plain numbered pattern like `1`, `2`, `3` (contextual card-number usage) -> `Base/Paper`.
- `BP 1`, `BP 2`, `BP 3` -> `Base/Paper`.
- `BCP 1`, `BCP 2`, `BCP 3` -> `Chrome`.
- `BPA 1`, `BPA 2`, `BPA 3` -> `Base/Paper`.
- `CPA 1`, `CPA 2`, `CPA 3` -> `Chrome`.
- `CRA 1`, `CRA 2`, `CRA 3` -> `Chrome`.

## Edge Cases

- (Add concrete title examples and why they are tricky)

## Decisions

- (Record final decisions here once agreed)

## Deferred / Parking Lot

- (Capture good ideas that are not for now)
