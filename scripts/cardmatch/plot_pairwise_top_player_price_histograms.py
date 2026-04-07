#!/usr/bin/env python3
"""
Build all-in price histograms (SVG in HTML) + summary stats for top pairwise-ranked players.

Compares **overall listing price distributions** (price + shipping) to the pairwise **win_rate**
story: high win_rate does not require the highest **average** price — it reflects same-card-type duels.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import html
import os
import sys
from statistics import median
from typing import Any, Dict, List, Sequence, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cardmatch.bowman_pilot_triples import bowman_all_in_price  # noqa: E402


def _pct(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = k - lo
    return float(sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w)


def _load_prices_by_player(path: str) -> Dict[str, List[float]]:
    by: Dict[str, List[float]] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            player = (row.get("pilot_player_guess") or "").strip()
            if not player:
                continue
            a = bowman_all_in_price(row)
            if a is None:
                continue
            by.setdefault(player, []).append(float(a))
    for p in by:
        by[p].sort()
    return by


def _histogram(
    values: Sequence[float],
    edges: Sequence[float],
) -> List[int]:
    counts = [0] * (len(edges) - 1)
    last = len(counts) - 1
    for v in values:
        i = bisect.bisect_right(edges, v) - 1
        if i < 0:
            i = 0
        if i > last:
            i = last
        counts[i] += 1
    return counts


def _svg_hist(
    title: str,
    values: List[float],
    edges: List[float],
    w: int = 420,
    h: int = 160,
) -> str:
    counts = _histogram(values, edges)
    mx = max(counts) if counts else 1
    pad_l, pad_r, pad_t, pad_b = 36, 12, 22, 28
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    nb = len(counts)
    bw = inner_w / max(nb, 1)
    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafafa" stroke="#ddd"/>',
        f'<text x="{w // 2}" y="16" text-anchor="middle" font-size="11" font-family="system-ui,sans-serif">{html.escape(title)}</text>',
        f'<text x="4" y="{h - 8}" font-size="9" fill="#666" font-family="system-ui,sans-serif">n={len(values)}</text>',
    ]
    med = median(values) if values else 0.0
    # median line in x
    if values:
        x_med = pad_l + (med - edges[0]) / (edges[-1] - edges[0] + 1e-9) * inner_w
        x_med = max(pad_l, min(pad_l + inner_w, x_med))
        parts.append(
            f'<line x1="{x_med:.1f}" y1="{pad_t}" x2="{x_med:.1f}" y2="{pad_t + inner_h}" '
            f'stroke="#c62828" stroke-width="1" stroke-dasharray="3,2" opacity="0.85"/>'
        )
    for i, c in enumerate(counts):
        bh = (c / mx) * inner_h if mx else 0
        x = pad_l + i * bw + 0.5
        y = pad_t + inner_h - bh
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(bw - 1, 0.5):.2f}" height="{max(bh, 0):.2f}" fill="#1565c0" opacity="0.75"/>'
        )
    parts.append(
        f'<text x="{pad_l + inner_w // 2}" y="{h - 10}" text-anchor="middle" font-size="9" fill="#444" font-family="system-ui,sans-serif">'
        f'all-in $ (0–{edges[-1]:.0f}); red dashed = median'
        f"</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="pilot_scored_full.csv")
    ap.add_argument("--out-html", required=True, help="Output HTML path")
    ap.add_argument("--out-csv", default="", help="Optional summary CSV path")
    ap.add_argument(
        "--pairwise-csv",
        default="",
        help="Optional bowman_pairwise_player_rankings_with_listings.csv to merge rank/win_rate",
    )
    ap.add_argument(
        "--players",
        default=(
            "Malachi Witherspoon/Kyson Witherspoon,"
            "Seth Hernandez,Michael Oliveto,Dax Kilby,Steele Hall,Gage Wood,Liam Doyle,Eli Willits"
        ),
        help="Comma-separated player names (order preserved)",
    )
    ap.add_argument("--max-bin", type=float, default=800.0, help="Histogram right edge ($)")
    ap.add_argument("--bins", type=int, default=40, help="Number of bins")
    args = ap.parse_args()

    by_player = _load_prices_by_player(args.input)
    players = [p.strip() for p in (args.players or "").split(",") if p.strip()]

    edges = [i * (args.max_bin / args.bins) for i in range(int(args.bins) + 1)]

    rows_summary: List[Dict[str, Any]] = []
    svgs: List[str] = []
    for pl in players:
        vals = by_player.get(pl, [])
        svgs.append(_svg_hist(pl[:48] + ("…" if len(pl) > 48 else ""), vals, edges))
        svals = sorted(vals)
        rows_summary.append(
            {
                "player": pl,
                "n_listings": len(vals),
                "mean_all_in": round(sum(vals) / len(vals), 4) if vals else 0.0,
                "median_all_in": round(median(vals), 4) if vals else 0.0,
                "p90_all_in": round(_pct(svals, 90), 4) if vals else 0.0,
                "max_all_in": round(max(vals), 4) if vals else 0.0,
            }
        )

    out_csv = (args.out_csv or "").strip()
    pairwise_path = (args.pairwise_csv or "").strip()
    pairwise_map: Dict[str, Tuple[int, float, int]] = {}
    if pairwise_path and os.path.isfile(pairwise_path):
        with open(pairwise_path, "r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                pairwise_map[(r.get("player") or "").strip()] = (
                    int(r["rank"]),
                    float(r["win_rate"]),
                    int(r["listing_count"]),
                )

    if out_csv:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        base_fields = [
            "player",
            "n_listings",
            "mean_all_in",
            "median_all_in",
            "p90_all_in",
            "max_all_in",
        ]
        if pairwise_map:
            fieldnames = [
                "pairwise_rank",
                "player",
                "win_rate",
                "n_listings",
                "mean_all_in",
                "median_all_in",
                "p90_all_in",
                "max_all_in",
                "pairwise_listing_count",
            ]
        else:
            fieldnames = base_fields
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows_summary:
                pl = row["player"]
                if pairwise_map and pl in pairwise_map:
                    rk, wr, plc = pairwise_map[pl]
                    w.writerow(
                        {
                            "pairwise_rank": rk,
                            "player": pl,
                            "win_rate": wr,
                            "n_listings": row["n_listings"],
                            "mean_all_in": row["mean_all_in"],
                            "median_all_in": row["median_all_in"],
                            "p90_all_in": row["p90_all_in"],
                            "max_all_in": row["max_all_in"],
                            "pairwise_listing_count": plc,
                        }
                    )
                else:
                    w.writerow(row)

    body = """
<h1 style="font-family:system-ui,sans-serif;font-size:18px">All-in price distributions (top pairwise names)</h1>
<p style="font-family:system-ui,sans-serif;max-width:900px;font-size:14px;color:#333">
Each chart is the distribution of <strong>price + shipping</strong> for that player’s listings in this pilot.
<strong>Pairwise rank</strong> uses same–card-type Monte Carlo duels, not this overall histogram — so a player can have a high
<code>win_rate</code> without the highest <code>mean_all_in</code> (e.g. many wins on mid-tier parallels vs cheaper peers for the same label).
Red dashed line = median all-in.
</p>
<p style="font-family:system-ui,sans-serif;font-size:13px;color:#555">
Bin range: $0–{max_bin:.0f} ({bins} bins). Mass above the cap is folded into the last bin.
</p>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:16px">
{grid}
</div>
""".format(
        max_bin=args.max_bin,
        bins=int(args.bins),
        grid="\n".join(svgs),
    )

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Pairwise top player price histograms</title></head>
<body style="margin:16px;background:#fff">
{body}
</body></html>
"""

    out_html = (args.out_html or "").strip()
    os.makedirs(os.path.dirname(out_html) or ".", exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Wrote {out_html}")
    if out_csv:
        print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
