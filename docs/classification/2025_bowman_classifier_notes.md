# 2025 Bowman Classifier Notes

Working document for raw thoughts, hypotheses, edge cases, and classification decisions.

Goal: capture nuance first, structure later.

## Context

- Dataset snapshot: `data/cardmatch_pilot/2025_bowman/20260501_full/term_search_items_export.csv`
- Checklists: full normalized rows in `data/checklists/normalized/2025_Bowman_Normalized.csv`; compact number → player → `card_type` + **`card_type_display`** (short label, e.g. BCP) in `data/checklists/normalized/2025_Bowman_card_number_lookup.csv` (same idea as `bowman_cards.csv`, kept for classifier alignment). Matched review CSVs show **`card_type_display`** in the `card_type` column and abbreviated **`player_name`** (first name → two letters).
- Steps 1–2 (exclude + checklist code match): `scripts/cardmatch/run_2025_bowman_retail_steps12.py` → writes full `listings_steps12.csv` next to the input export (includes `step2_pass`: **1** only when `match_status` is `matched`, i.e. title↔checklist player score ≥ 80). Then one **review** CSV per `match_status` under `step2_by_match_status/` with columns `card_number`, `player_name`, `card_type`, **`listing_display`**, `listing` (logic in `cardmatch/bowman_2025_retail_steps.py`). ``listing_display`` uses the same title cleanup and **code + /serial prefix** rules as step 3 whenever ``card_number`` is present on the row. Re-split only: `scripts/cardmatch/split_listings_steps12_by_match_status.py`.
- **Matched + serial (review):** `step3_by_match_status/listings_step3_matched.csv` — only rows with `match_status_after_step3` = **matched** (step-2 checklist match), columns `card_number`, `serial`, `player_name`, `card_type`, **`listing_display`**, `listing`. ``listing_display`` strips team/city phrasing, ``RC`` / ``Rookie Card`` / ``1st Bowman``, drops whole words ``2025``, ``Bowman`` / ``Bowman's``, ``Prospects`` / ``Prospect``, standalone ``1st``, ``baseball``, ``shipping``, ``edition``, ``Topps``, removes ``!`` and spaced-hyphen glue (`` - ``), keeps ``Chrome``, then when the row has a checklist ``card_number`` prefixes **that code**, then a **Chrome** cue (``Chrome`` plus optional **product** follow-ons Mega/Mojo/Anime only — not parallel modifiers like Sapphire), then **``/serial``** parsed from the raw title (same slot-aware rules as the ``serial`` column), then the cleaned remainder without duplicating code, Chrome span, or serial (see ``cardmatch/bowman_2025_listing_display.py``). `serial` is recomputed from the title with the matched card slot so lone `/N` does not echo the checklist number (e.g. `/15` vs `BP-15`); use **`/499`**, **`#/99`**, or **`a/b`** fractions for print runs. Missing serial → **`-1`**. Sort: `card_number`, then `serial` with **`-1` first**, then denominators **descending**. Written by the same runner (or `scripts/cardmatch/split_listings_step3_matched_serial.py` on an existing `listings_steps12.csv`).
- **Word flags / groups**: `cardmatch/bowman_2025_retail_flags.py` — `WF_*` flags are grounded in **this notes doc** (exclusions, paper/chrome clues, card-vs-modifier keywords, insert **phrases** from the set-distinction list). **`grp_*`** are reserved placeholders (all false) until retail-specific combination rules are defined; they are **not** copied from Bowman Draft. Step-1 exclusions use the same `WF_*` definitions.
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

For a **fixed stacking order** of modifiers on top of the checklist slot, see **Hierarchical listing identity** below (serial → color → pattern).

## Hierarchical listing identity (four levels)

Use this when you need a **single ladder** from checklist row to full variant wording. Each step **extends** the previous (nested / finer granularity); later steps assume earlier ones are resolved.

### Step 1 — Card (checklist `card_number`)

- **Anchors to:** the checklist key (`card_number` in `2025_Bowman_card_number_lookup.csv` and the full normalized checklist).
- **Captures:** product line + slot + player identity for that row (no serial, no parallel color, no pattern).
- **Example:** `BCP-149`

### Step 2 — Card + serial number

- **Adds:** the finite print run from the title (e.g. `/50`, `/499`, `#/50`, `x/50` — normalize conventions in implementation).
- **Example:** `BCP-149` + `/50`

### Step 3 — Card + serial number + color

- **Adds:** parallel / ink **color** (gold, purple, neon green, etc. — use the set-line color lists later in this doc for Base vs Chrome).
- **Example:** `BCP-149` + `/50` + gold

### Step 4 — Card + serial number + color + pattern

- **Adds:** **pattern** / texture (shimmer, reptilian, geometric, etc. — Chrome pattern list lives under **Chrome variation details** below).
- **Example:** `BCP-149` + `/50` + gold + shimmer

**Notes**

- This hierarchy is **orthogonal** to the **Prediction pipeline (hypothesis)** section: that section is about *processing order* (exclude → player → card slot → modifiers). Here, “Step 1–4” is about *how much of the variant stack* you record on a listing once the card line is known.
- Steps 2–4 are all **modifiers** in the mental model above; Step 1 is the **card** slot only.

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

Implementation note (``WF_chrome`` / ``WF_paper`` in ``cardmatch/bowman_2025_retail_flags.py``): ``WF_chrome`` is also set by chrome-line checklist codes **BCP**, **CPA**, **CRA** (strict hyphen or glued digits); ``WF_paper`` is also set by **BP**, **BPA**, **PRV** the same way.

Word flags for matching help: ``WF_rookie_of_the_year`` (phrase *rookie of the year* or strict ``ROY-`` / ``#ROY-`` codes), ``WF_auto`` (auto / autograph / a/u / on-card / signed / signature), plus ``WF_insert_roy_favorites`` for the insert line name *Rookie of the Year Favorites* only.

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
