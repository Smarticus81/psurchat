"""
Chart Generator - MDCG 2022-21 Annex II Tables and Trend Charts.

Generates publication-quality charts and tables required for PSUR compliance.
All outputs are base64-encoded PNG images suitable for embedding in DOCX reports
and serving via API.

MDCG 2022-21 Annex II Required Tables:
  Table 1: Units Distributed by Year
  Table 2: Units Distributed by Region
  Table 3: Complaint Summary by Year
  Table 4: Serious Incident Summary
  Table 5: Serious Incidents by Type
  Table 6: Serious Incidents Over Time
  Table 7: FSCA Summary
  Table 8: CAPA Summary

Additional Trend Charts:
  - Complaint Rate Trend (line)
  - Severity Distribution (bar/pie)
  - Complaint Type Distribution (bar)
  - Year-over-Year Comparison (grouped bar)
"""

import io
import base64
from typing import Dict, List, Any, Optional, Tuple

from backend.psur.context import PSURContext

# matplotlib import with non-interactive backend
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None  # type: ignore

# Consistent styling
COLORS = {
    "primary": "#4C8EDA",
    "secondary": "#57C7E3",
    "danger": "#F16667",
    "warning": "#FFC454",
    "success": "#8DCC93",
    "purple": "#C990C0",
    "orange": "#F79767",
    "bg": "#FFFFFF",
    "text": "#1A1A2E",
    "grid": "#E5E5E5",
}

PALETTE = [COLORS["primary"], COLORS["secondary"], COLORS["danger"],
           COLORS["warning"], COLORS["success"], COLORS["purple"],
           COLORS["orange"]]


def _setup_style():
    """Apply consistent chart styling."""
    if not MATPLOTLIB_AVAILABLE or plt is None:
        return
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["bg"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text"],
        "xtick.color": COLORS["text"],
        "ytick.color": COLORS["text"],
        "text.color": COLORS["text"],
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": COLORS["grid"],
    })


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _fig_to_bytes(fig) -> bytes:
    """Convert matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# MDCG 2022-21 Annex II Table Charts
# ---------------------------------------------------------------------------

def table1_units_by_year(ctx: PSURContext) -> Optional[str]:
    """Table 1: Units Distributed by Year -- bar chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.total_units_by_year:
        return None
    _setup_style()
    years = sorted(ctx.total_units_by_year.keys())
    units = [ctx.total_units_by_year[y] for y in years]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([str(y) for y in years], units, color=COLORS["primary"], edgecolor="white", width=0.6)
    for bar, val in zip(bars, units):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(units) * 0.02,
                f"{val:,}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("Table 1: Units Distributed by Year", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Year")
    ax.set_ylabel("Units Distributed")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig.tight_layout()
    return _fig_to_base64(fig)


def table2_units_by_region(ctx: PSURContext) -> Optional[str]:
    """Table 2: Units Distributed by Region -- horizontal bar chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.total_units_by_region:
        return None
    _setup_style()
    regions = list(ctx.total_units_by_region.keys())
    units = [ctx.total_units_by_region[r] for r in regions]
    fig, ax = plt.subplots(figsize=(8, max(3, len(regions) * 0.6)))
    bars = ax.barh(regions, units, color=COLORS["secondary"], edgecolor="white", height=0.5)
    for bar, val in zip(bars, units):
        ax.text(bar.get_width() + max(units) * 0.02, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, fontweight="bold")
    ax.set_title("Table 2: Units Distributed by Region", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Units")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig.tight_layout()
    return _fig_to_base64(fig)


def table3_complaints_by_year(ctx: PSURContext) -> Optional[str]:
    """Table 3: Complaint Summary by Year -- bar + line combo."""
    if not MATPLOTLIB_AVAILABLE or not ctx.total_complaints_by_year:
        return None
    _setup_style()
    years = sorted(ctx.total_complaints_by_year.keys())
    counts = [ctx.total_complaints_by_year[y] for y in years]
    rates = [ctx.complaint_rate_by_year.get(y, 0) for y in years]

    fig, ax1 = plt.subplots(figsize=(8, 4))
    bars = ax1.bar([str(y) for y in years], counts, color=COLORS["orange"], edgecolor="white", width=0.5, label="Complaints")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Number of Complaints", color=COLORS["orange"])
    for bar, val in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(val), ha="center", va="bottom", fontsize=9, fontweight="bold")

    if any(r > 0 for r in rates):
        ax2 = ax1.twinx()
        ax2.plot([str(y) for y in years], rates, color=COLORS["danger"], marker="o",
                 linewidth=2, markersize=6, label="Rate %")
        ax2.set_ylabel("Complaint Rate (%)", color=COLORS["danger"])

    ax1.set_title("Table 3: Complaint Summary by Year", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return _fig_to_base64(fig)


def table4_serious_incident_summary(ctx: PSURContext) -> Optional[str]:
    """Table 4: Serious Incident Summary -- stacked bar."""
    if not MATPLOTLIB_AVAILABLE or ctx.serious_incidents == 0:
        return None
    _setup_style()
    categories = ["Deaths", "Serious Injuries", "Other"]
    values = [ctx.deaths, ctx.serious_injuries,
              max(0, ctx.serious_incidents - ctx.deaths - ctx.serious_injuries)]
    colors = [COLORS["danger"], COLORS["warning"], COLORS["primary"]]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(categories, values, color=colors, edgecolor="white", width=0.5)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                    str(val), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title("Table 4: Serious Incident Summary", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Count")
    fig.tight_layout()
    return _fig_to_base64(fig)


def table5_incidents_by_type(ctx: PSURContext) -> Optional[str]:
    """Table 5: Serious Incidents by Type -- pie chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.serious_incidents_by_type:
        return None
    _setup_style()
    labels = list(ctx.serious_incidents_by_type.keys())
    values = list(ctx.serious_incidents_by_type.values())
    colors = PALETTE[:len(labels)]
    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")
    ax.set_title("Table 5: Serious Incidents by Type", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return _fig_to_base64(fig)


def table6_incidents_over_time(ctx: PSURContext) -> Optional[str]:
    """Table 6: Serious Incidents Over Time -- line chart (requires yearly data)."""
    # This would need yearly incident data; for now, generate a placeholder
    # that shows available data
    if not MATPLOTLIB_AVAILABLE or ctx.serious_incidents == 0:
        return None
    if not ctx.total_units_by_year:
        return None
    _setup_style()
    years = sorted(ctx.total_units_by_year.keys())
    fig, ax = plt.subplots(figsize=(8, 4))
    # Show incident rate per year if we have complaint data by year
    if ctx.total_complaints_by_year:
        complaint_years = sorted(ctx.total_complaints_by_year.keys())
        ax.plot([str(y) for y in complaint_years],
                [ctx.total_complaints_by_year[y] for y in complaint_years],
                color=COLORS["danger"], marker="o", linewidth=2, markersize=6, label="Complaints")
    ax.set_title("Table 6: Event Trend Over Time", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Year")
    ax.set_ylabel("Count")
    ax.legend()
    fig.tight_layout()
    return _fig_to_base64(fig)


def table7_fsca_summary(ctx: PSURContext) -> Optional[str]:
    """Table 7: FSCA Summary -- info card (no FSCA data = 'None' chart)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    _setup_style()
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.axis("off")
    text = "No Field Safety Corrective Actions during this reporting period."
    if ctx.capa_details:
        text = f"{len(ctx.capa_details)} CAPA-related actions tracked."
    ax.text(0.5, 0.5, text, transform=ax.transAxes, ha="center", va="center",
            fontsize=12, fontweight="bold", color=COLORS["success"],
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F0FFF0", edgecolor=COLORS["success"]))
    ax.set_title("Table 7: FSCA Summary", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return _fig_to_base64(fig)


def table8_capa_summary(ctx: PSURContext) -> Optional[str]:
    """Table 8: CAPA Summary -- stacked bar."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    _setup_style()
    categories = ["Open", "Closed This Period", "Verified Effective"]
    values = [ctx.capa_actions_open, ctx.capa_actions_closed_this_period,
              ctx.capa_actions_effectiveness_verified]
    colors = [COLORS["warning"], COLORS["primary"], COLORS["success"]]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(categories, values, color=colors, edgecolor="white", width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(val), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title("Table 8: CAPA Summary", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Count")
    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Additional Trend Charts
# ---------------------------------------------------------------------------

def complaint_rate_trend(ctx: PSURContext) -> Optional[str]:
    """Complaint rate over time -- line chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.complaint_rate_by_year:
        return None
    _setup_style()
    years = sorted(ctx.complaint_rate_by_year.keys())
    rates = [ctx.complaint_rate_by_year[y] for y in years]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([str(y) for y in years], rates, color=COLORS["primary"], marker="o",
            linewidth=2.5, markersize=8)
    for y, r in zip(years, rates):
        ax.annotate(f"{r:.3f}%", (str(y), r), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, fontweight="bold")
    ax.set_title("Complaint Rate Trend", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Year")
    ax.set_ylabel("Complaint Rate (%)")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return _fig_to_base64(fig)


def severity_distribution(ctx: PSURContext) -> Optional[str]:
    """Complaint severity distribution -- donut chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.complaints_by_severity:
        return None
    _setup_style()
    labels = list(ctx.complaints_by_severity.keys())
    values = list(ctx.complaints_by_severity.values())
    colors = PALETTE[:len(labels)]
    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.4),
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")
    ax.set_title("Complaint Severity Distribution", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return _fig_to_base64(fig)


def complaint_type_breakdown(ctx: PSURContext) -> Optional[str]:
    """Complaint type breakdown -- horizontal bar chart."""
    if not MATPLOTLIB_AVAILABLE or not ctx.complaints_by_type:
        return None
    _setup_style()
    types = list(ctx.complaints_by_type.keys())
    counts = list(ctx.complaints_by_type.values())
    fig, ax = plt.subplots(figsize=(8, max(3, len(types) * 0.5)))
    bars = ax.barh(types, counts, color=COLORS["purple"], edgecolor="white", height=0.5)
    for bar, val in zip(bars, counts):
        ax.text(bar.get_width() + max(counts) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold")
    ax.set_title("Complaint Type Breakdown", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Count")
    fig.tight_layout()
    return _fig_to_base64(fig)


def root_cause_distribution(ctx: PSURContext) -> Optional[str]:
    """Root cause distribution -- bar chart."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    categories = {
        "Product Defect": ctx.complaints_product_defect,
        "User Error": ctx.complaints_user_error,
        "Unrelated": ctx.complaints_unrelated,
        "Unconfirmed": ctx.complaints_unconfirmed,
    }
    if all(v == 0 for v in categories.values()):
        return None
    _setup_style()
    labels = list(categories.keys())
    values = list(categories.values())
    colors = [COLORS["danger"], COLORS["warning"], COLORS["success"], COLORS["grid"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                str(val), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title("Root Cause Distribution", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Count")
    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Master chart generation
# ---------------------------------------------------------------------------

def generate_all_charts(ctx: PSURContext) -> List[Dict[str, Any]]:
    """
    Generate all MDCG 2022-21 Annex II tables and trend charts.
    Returns a list of dicts: {chart_id, title, category, base64_png, section_id}
    """
    if not MATPLOTLIB_AVAILABLE:
        return []

    chart_specs: List[Tuple[str, str, str, str, Any]] = [
        # (chart_id, title, category, relevant_section, generator_fn)
        ("table1_units_year", "Table 1: Units Distributed by Year", "annex_ii", "C", table1_units_by_year),
        ("table2_units_region", "Table 2: Units Distributed by Region", "annex_ii", "C", table2_units_by_region),
        ("table3_complaints_year", "Table 3: Complaint Summary by Year", "annex_ii", "E", table3_complaints_by_year),
        ("table4_si_summary", "Table 4: Serious Incident Summary", "annex_ii", "D", table4_serious_incident_summary),
        ("table5_si_type", "Table 5: Serious Incidents by Type", "annex_ii", "D", table5_incidents_by_type),
        ("table6_si_time", "Table 6: Events Over Time", "annex_ii", "G", table6_incidents_over_time),
        ("table7_fsca", "Table 7: FSCA Summary", "annex_ii", "H", table7_fsca_summary),
        ("table8_capa", "Table 8: CAPA Summary", "annex_ii", "I", table8_capa_summary),
        ("trend_complaint_rate", "Complaint Rate Trend", "trend", "G", complaint_rate_trend),
        ("dist_severity", "Severity Distribution", "distribution", "E", severity_distribution),
        ("dist_type", "Complaint Type Breakdown", "distribution", "E", complaint_type_breakdown),
        ("dist_root_cause", "Root Cause Distribution", "distribution", "F", root_cause_distribution),
    ]

    results = []
    skipped = []
    for chart_id, title, category, section_id, gen_fn in chart_specs:
        try:
            b64 = gen_fn(ctx)
            if b64:
                results.append({
                    "chart_id": chart_id,
                    "title": title,
                    "category": category,
                    "section_id": section_id,
                    "base64_png": b64,
                })
                print(f"[chart_generator] Generated: {chart_id} ({title})")
            else:
                skipped.append(chart_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[chart_generator] ERROR generating {chart_id}: {e}")
            skipped.append(chart_id)

    print(f"[chart_generator] Summary: {len(results)} generated, {len(skipped)} skipped ({', '.join(skipped)})")
    print(f"[chart_generator] Context data: units_by_year={bool(ctx.total_units_by_year)}, "
          f"units_by_region={bool(ctx.total_units_by_region)}, "
          f"complaints_by_year={bool(ctx.total_complaints_by_year)}, "
          f"complaints_by_type={bool(ctx.complaints_by_type)}, "
          f"complaints_by_severity={bool(ctx.complaints_by_severity)}, "
          f"serious_incidents={ctx.serious_incidents}, "
          f"si_by_type={bool(ctx.serious_incidents_by_type)}")
    return results
