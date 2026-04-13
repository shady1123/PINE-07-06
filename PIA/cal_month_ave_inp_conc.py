import os
import re
from calendar import month_abbr
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _read_temp_table(temp_file):
    """Read L2 temp spectrum table by locating the header line."""
    with open(temp_file, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Temp_start\t"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find header in {temp_file}")
    df = pd.read_csv(temp_file, sep="\t", skiprows=header_idx, header=0, encoding="latin1")
    required = {"Temp_start", "datetime", "cn_ice"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns {missing} in {temp_file}")
    df["Temp_start"] = pd.to_numeric(df["Temp_start"], errors="coerce")
    df["cn_ice"] = pd.to_numeric(df["cn_ice"], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", format="mixed")
    df = df.dropna(subset=["Temp_start", "cn_ice", "datetime"])
    return df


def cal_month_ave_inp_conc(
    MAIN_DIR,
    PINE_ID,
    CAMPAIGN,
    OP_ID=None,
    target_temps=(-15, -20, -25, -30),
    temp_tolerance=0.5,
    plot_only_existing_months=False,
    figsize=(10, 7.5),
    bar_width=0.38,
    dpi=180,
    show_title=True,
    month_spacing=1.0,
):
    """
    Calculate monthly mean INP concentrations at representative temperatures.

    Parameters
    ----------
    MAIN_DIR : str
        Campaign analysis directory.
    PINE_ID : str
    CAMPAIGN : str
    OP_ID : int or None
        If None, aggregate all *_temp.txt files in campaign.
    target_temps : tuple
        Representative temperatures in degree C.
    temp_tolerance : float
        Use rows where |Temp_start - target_temp| <= temp_tolerance.
    """
    temp_dir = os.path.join(MAIN_DIR, "L2_Data", "Temp_Spec")
    save_dir = os.path.join(MAIN_DIR, "Plots", "monthly")
    os.makedirs(save_dir, exist_ok=True)

    if OP_ID is None:
        pattern = os.path.join(temp_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_*_temp.txt")
        temp_files = sorted(glob(pattern))
    else:
        temp_files = [os.path.join(temp_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp.txt")]

    temp_files = [f for f in temp_files if os.path.exists(f)]
    if not temp_files:
        raise FileNotFoundError(f"No temp files found in {temp_dir}")

    all_df = []
    for fpath in temp_files:
        dfi = _read_temp_table(fpath)
        m = re.search(r"_op_id_(\d+)_temp\.txt$", os.path.basename(fpath))
        dfi["op_id"] = int(m.group(1)) if m else np.nan
        all_df.append(dfi)
    df = pd.concat(all_df, ignore_index=True)
    df = df[df["cn_ice"] > 0].copy()
    df["year_month"] = df["datetime"].dt.to_period("M")

    # Continuous monthly axis from first to last month (across years)
    ym_start = df["year_month"].min()
    ym_end = df["year_month"].max()
    ym_index = pd.period_range(start=ym_start, end=ym_end, freq="M")
    ym_labels = [month_abbr[p.month] for p in ym_index]
    ym_full_labels = [p.strftime("%Y-%m") for p in ym_index]

    # Nature-inspired palette (high contrast, colorblind-friendly)
    palette = ["#E64B35", "#4DBBD5", "#00A087", "#3C5488"]

    monthly_data = {}
    for t in target_temps:
        sel = df[np.abs(df["Temp_start"] - t) <= temp_tolerance]
        g = sel.groupby("year_month")["cn_ice"].mean()
        g = g.reindex(ym_index)
        monthly_data[t] = g

    # Reference-style layout: 4 stacked panels, one temperature per panel.
    fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True)
    if len(target_temps) != 4:
        # keep compatibility for custom temperature count
        fig_h = max(3.2, 1.9 * len(target_temps) + 1)
        fig, axes = plt.subplots(len(target_temps), 1, figsize=(figsize[0], fig_h), sharex=True)
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])

    # Collect CSV-ready monthly values (year-month + one column per target temp)
    monthly_csv_df = pd.DataFrame({"year_month": ym_full_labels})
    monthly_csv_df["month_start"] = [p.to_timestamp(how="start").strftime("%Y-%m-%d") for p in ym_index]
    monthly_csv_df["month_end"] = [p.to_timestamp(how="end").strftime("%Y-%m-%d") for p in ym_index]

    for i, (ax, t) in enumerate(zip(axes, target_temps)):
        series = monthly_data[t].copy()
        labels = ym_labels.copy()
        if plot_only_existing_months:
            mask = series.notna()
            series = series[mask]
            labels = [lbl for lbl, keep in zip(labels, mask) if keep]
        y = series.values
        if month_spacing <= 0:
            month_spacing = 1.0
        x = np.arange(len(series)) * month_spacing
        ax.bar(x, y, width=bar_width, color=palette[i % len(palette)], alpha=0.9)
        ax.text(0.02, 0.82, f"{t}°C", transform=ax.transAxes, fontsize=12, color=palette[i % len(palette)])
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        ax.set_xlim(-0.6 * month_spacing, (len(series) - 0.4) * month_spacing)
        ax.set_xticks(x)
        if i < len(target_temps) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xticklabels(labels, fontsize=10, rotation=0, ha="center")
        ax.tick_params(axis="y", labelsize=10)
        # keep full monthly table (pre-filter) for export
        monthly_csv_df[f"cn_ice_{t}C"] = monthly_data[t].values

    fig.supylabel(r"INP concentration (std L$^{-1}$)", fontsize=12, x=0.04)
    if show_title:
        fig.suptitle(
            f"{PINE_ID} {CAMPAIGN} | Monthly mean INP at representative temperatures",
            fontsize=14,
            y=0.98,
        )
        tight_rect = [0.05, 0.03, 1, 0.96]
    else:
        tight_rect = [0.05, 0.03, 1, 1]
    plt.tight_layout(rect=tight_rect)

    if OP_ID is None:
        out_name = f"{PINE_ID}_{CAMPAIGN}_monthly_mean_inp_by_temp.png"
        out_csv_name = f"{PINE_ID}_{CAMPAIGN}_monthly_mean_inp_by_temp.csv"
    else:
        out_name = f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_monthly_mean_inp_by_temp.png"
        out_csv_name = f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_monthly_mean_inp_by_temp.csv"
    out_path = os.path.join(save_dir, out_name)
    out_csv_path = os.path.join(save_dir, out_csv_name)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    monthly_csv_df.to_csv(out_csv_path, index=False, encoding="utf-8")
    print(f"绘图已保存至: {out_path}")
    print(f"月平均CSV已保存至: {out_csv_path}")

    return monthly_data
