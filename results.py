from __future__ import annotations
import textwrap
from pathlib import Path

from lazyportfolio import lazyports
from idealportfolio import idealport
from performance import Performance, SPYport
from treasuryyields import rf

lazyresults: dict[float, Performance] = dict()

for delta in lazyports:
    lazy, history = lazyports[delta]
    lazyresults[delta] = Performance(lazy, rf)

spyresult = Performance(SPYport[0], rf)
idealresult = Performance(idealport[0], rf)



import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

out_dir = Path("figures")
dpi = 200
show = False            # change to True to show figures interactively

surface = "#fcfcfb"
ink = "#0b0b0b"        # titles
ink2 = "#52514e"       # labels, legend text, SPY
muted = "#898781"      # tick labels, notes
grid = "#e1e0d9"
axis = "#c3c2b7"
blue = "#2a78d6"       # lazy portfolios
orange = "#eb6834"     # ideal portfolio
spy_colour = ink2
path_blue = "#9ec5f4"  # thin connecting line behind the lazy dots
ramp = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
        "#256abf", "#1c5cab", "#184f95", "#104281"]


lazy_deltas = sorted(lazyresults, key = float)
delta_pct = np.array([float(d) * 100 for d in lazy_deltas])
norm = Normalize(vmin=delta_pct.min(), vmax=delta_pct.max())
cmap = LinearSegmentedColormap.from_list("delta_blue", ramp)
assets = list(idealresult.weights_history.columns)

_days = idealresult.values.index
period = f"{_days[1]:%b %Y} – {_days[-1]:%b %Y}"        # first return day to last day
period_note = (f"Test period {period}. Weights are re-solved every quarter on a rolling 10-year window.")

lazy_tbl = pd.DataFrame([lazyresults[d].summary() for d in lazy_deltas],
                        index=pd.Index(delta_pct, name="delta (%)"))
ideal_row = idealresult.summary()
spy_row = spyresult.summary()


# Styling helpers

def apply_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": surface, "axes.facecolor": surface, "savefig.facecolor": surface,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "text.color": ink,
        "axes.labelcolor": ink2, "axes.edgecolor": axis, "axes.linewidth": 1.0,
        "xtick.color": muted, "ytick.color": muted,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "axes.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
        "grid.color": grid, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left",
        "axes.titlepad": 8,
        "legend.frameon": False, "legend.fontsize": 9,
        "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    })
 
 
def suptitle(fig, text: str) -> None:
    fig.suptitle(text, x=0.01, ha="left", fontsize=14, fontweight="semibold", color=ink)
 
 
def draw_key(ax, handles, colourbar: bool, note: str = period_note) -> None:
    """Turns a spare grid cell into the legend panel (identity key, optional delta scale, note)."""
    ax.set_axis_off()
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.02, 0.98),
              borderaxespad=0, labelcolor=ink2, handlelength=2.6, labelspacing=0.9)
    if colourbar:
        cax = ax.inset_axes([0.04, 0.42, 0.88, 0.07])
        cb = ax.figure.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                                orientation="horizontal", ticks=[0.25, 1, 2, 3, 4, 5])
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=0, labelsize=8.5, colors=muted)
        cb.set_label("Lazy portfolios: return tolerance δ (%)", color=ink2, fontsize=9)
    ax.text(0.04, 0.20, textwrap.fill(note, 44), transform=ax.transAxes,
            color=muted, fontsize=8.5, va="top")
 
 
def lazy_handle(label="Lazy (min variance)") -> Line2D:
    return Line2D([0], [0], color=blue, lw=2, marker="o", ms=6, mec=surface, mew=1.2, label=label)
 
 
def style_dates(ax) -> None:
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
 
 
def save(fig, name: str) -> None:
    out_dir.mkdir(exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=dpi)
    print(f"saved {path}")
    if not show:
        plt.close(fig)
 


# Figure 1a: weights over time

def fig_weights_over_time() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.2), constrained_layout=True)
    flat = axes.ravel()
    ideal_w = idealresult.step_frame()
    lazy_w = {d: lazyresults[d].step_frame() for d in lazy_deltas}
 
    for ax, asset in zip(flat, assets):
        for d in lazy_deltas:                                       # light -> dark = small -> large delta
            ax.plot(lazy_w[d].index, lazy_w[d][asset], drawstyle="steps-post",
                    color=cmap(norm(float(d) * 100)), lw=1.5)
        ax.plot(ideal_w.index, ideal_w[asset], drawstyle="steps-post", color=orange, lw=2.4,
                path_effects=[pe.Stroke(linewidth=4.6, foreground=surface), pe.Normal()])
        ax.set_title(asset)
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        style_dates(ax)
 
    handles = [Line2D([0], [0], color=orange, lw=2.4, label="Ideal (max Sharpe)")]
    draw_key(flat[5], handles, colourbar=True)
    suptitle(fig, "Portfolio weights through time: ideal against every lazy portfolio")
    save(fig, "fig1a_weights_over_time.png")


# Figure 1b: time-averaged weights against delta 

def fig_average_weights() -> pd.DataFrame:
    avg_lazy = pd.DataFrame([lazyresults[d].average_weights() for d in lazy_deltas],
                            index=pd.Index(delta_pct, name="delta (%)")) * 100
    avg_ideal = idealresult.average_weights() * 100
 
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.2), constrained_layout=True)
    flat = axes.ravel()
    for ax, asset in zip(flat, assets):
        ax.plot(delta_pct, avg_lazy[asset], color=blue, lw=2, marker="o", ms=6,
                mec=surface, mew=1.2, zorder=3)
        ax.hlines(avg_ideal[asset], 0, 5.25, color=orange, lw=2.2, linestyles=(0, (4, 2)), zorder=2)
        ax.set_title(asset)
        ax.set_xlim(0, 5.25)
        ax.set_xticks(range(0, 6))
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.set_xlabel("Return tolerance δ (%)")
 
    handles = [lazy_handle("Lazy portfolios (one point per δ)"),
               Line2D([0], [0], color=orange, lw=2.2, ls=(0, (4, 2)), label="Ideal (max Sharpe)")]
    draw_key(flat[5], handles, colourbar=False,
             note=period_note + " Each value is the time-weighted average of the target weights.")
    suptitle(fig, "Time-weighted average weight of each asset (against δ for lazy portfolios)")
    save(fig, "fig1b_average_weights.png")
 
    return pd.concat([avg_lazy, avg_ideal.to_frame("Ideal").T.rename_axis("delta (%)")])


# Figure 2: return against risk

def fig_risk_return() -> None:
    risks = [("Annualised volatility (%)", "Annualised volatility (%)"),
             ("Max drawdown (%)", "Maximum drawdown (%)"),
             ("CVaR 95% daily (%)", "CVaR 95% daily (%)")]
    y = "CAGR (%)"
 
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.2), sharey=True, constrained_layout=True)
    for ax, (col, label) in zip(axes, risks):
        ax.grid(axis="both")
        ax.plot(lazy_tbl[col], lazy_tbl[y], color=path_blue, lw=1.2, zorder=1)
        ax.scatter(lazy_tbl[col], lazy_tbl[y], c=delta_pct, cmap=cmap, norm=norm, s=75,
                   edgecolors=surface, linewidths=1.5, zorder=3)
        ax.scatter(ideal_row[col], ideal_row[y], marker="D", s=95, color=orange,
                   edgecolors=surface, linewidths=1.5, zorder=4)
        ax.scatter(spy_row[col], spy_row[y], marker="s", s=85, color=spy_colour,
                   edgecolors=surface, linewidths=1.5, zorder=4)
 
        for text, (xv, yv) in [("Ideal", (ideal_row[col], ideal_row[y])),
                               ("SPY", (spy_row[col], spy_row[y]))]:
            ax.annotate(text, (xv, yv), xytext=(8, 6), textcoords="offset points",
                        fontsize=9, color=ink2)
        for text, i in [("δ 0.25%", 0), ("δ 5%", -1)]:               # ends of the lazy path
            ax.annotate(text, (lazy_tbl[col].iloc[i], lazy_tbl[y].iloc[i]),
                        xytext=(8, -12), textcoords="offset points", fontsize=8.5, color=muted)
 
        ax.margins(0.14)
        ax.set_xlabel(label)
    axes[0].set_ylabel("CAGR (%)")
 
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=axes, shrink=0.75, pad=0.015,
                      aspect=28, ticks=[0.25, 1, 2, 3, 4, 5])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=8.5, colors=muted)
    cb.set_label("Lazy portfolios: return tolerance δ (%)", color=ink2, fontsize=9)
 
    handles = [Line2D([0], [0], marker="D", ls="", color=orange, ms=8, mec=surface, label="Ideal (max Sharpe)"),
               Line2D([0], [0], marker="s", ls="", color=spy_colour, ms=8, mec=surface, label="SPY, buy and hold")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, labelcolor=ink2)
    suptitle(fig, f"Return against risk, {period}")
    save(fig, "fig2_risk_return_scatter.png")


# Figure 3: summary of all metrics against delta

metric_panels = [
    ("CAGR (%)", "CAGR (%)"),
    ("Annualised volatility (%)", "Annualised volatility (%)"),
    ("Sharpe ratio", "Sharpe ratio"),
    ("Beta (vs market index)", "Beta vs SPY"),
    ("CVaR 95% daily (%)", "CVaR 95%, daily (%)"),
    ("Max drawdown (%)", "Maximum drawdown (%)"),
    ("Avg turnover per rebalance (%)", "Average turnover per quarter (%)"),
]
 
 
def fig_metrics_vs_delta() -> None:
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.2), constrained_layout=True)
    flat = axes.ravel()
 
    for ax, (col, title) in zip(flat, metric_panels):
        ax.hlines(spy_row[col], 0, 5.25, color=spy_colour, lw=1.8, linestyles=(0, (1, 2)), zorder=1)
        ax.hlines(ideal_row[col], 0, 5.25, color=orange, lw=2.2, linestyles=(0, (4, 2)), zorder=2)
        ax.plot(delta_pct, lazy_tbl[col], color=blue, lw=2, marker="o", ms=6,
                mec=surface, mew=1.2, zorder=3)
        ax.set_title(title)
        ax.set_xlim(0, 5.25)
        ax.set_xticks(range(0, 6))
        ax.set_xlabel("Return tolerance δ (%)")
        ax.margins(y=0.12)
 
    handles = [lazy_handle("Lazy portfolios (one point per δ)"),
               Line2D([0], [0], color=orange, lw=2.2, ls=(0, (4, 2)), label="Ideal (max Sharpe)"),
               Line2D([0], [0], color=spy_colour, lw=1.8, ls=(0, (1, 2)), label="SPY, buy and hold")]
    draw_key(flat[7], handles, colourbar=False)
    suptitle(fig, f"Performance metrics against return tolerance δ, {period}")
    save(fig, "fig3_metrics_vs_delta.png")


# Saving the tables

def save_tables(avg_weights_table: pd.DataFrame) -> None:
    out_dir.mkdir(exist_ok=True)
    metrics = pd.concat([
        lazy_tbl.rename(index=lambda v: f"lazy, delta={v:g}%"),
        ideal_row.to_frame("ideal").T,
        spy_row.to_frame("SPY").T,
    ])
    metrics.index.name = "portfolio"
    metrics.to_csv(out_dir / "metrics_by_portfolio.csv", float_format="%.6g")
    avg_weights_table.to_csv(out_dir / "average_weights.csv", float_format="%.4f")
    print(f"saved {out_dir / 'metrics_by_portfolio.csv'} and {out_dir / 'average_weights.csv'}")
 
 
def main() -> None:
    apply_style()
    fig_weights_over_time()
    avg_table = fig_average_weights()
    fig_risk_return()
    fig_metrics_vs_delta()
    save_tables(avg_table)
    if show:
        plt.show()
 
 
if __name__ == "__main__":
    main()
