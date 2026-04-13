import os
import re
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _read_temp_table(temp_file):
    """Read L2 temp spectrum file by locating the table header."""
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
        raise ValueError(f"Missing columns {missing} in {temp_file}")
    df["Temp_start"] = pd.to_numeric(df["Temp_start"], errors="coerce")
    df["cn_ice"] = pd.to_numeric(df["cn_ice"], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", format="mixed")
    df = df.dropna(subset=["Temp_start", "cn_ice", "datetime"])
    return df


def _tag_day_night(series_dt):
    """
    Day:   08:00 <= hour < 18:00
    Night: otherwise (18:00-24:00 and 00:00-08:00)
    """
    hours = series_dt.dt.hour
    return np.where((hours >= 8) & (hours < 18), "Day (08-18)", "Night (18-08)")


def cal_day_night_ave_inp_conc(
    MAIN_DIR,
    PINE_ID,
    CAMPAIGN,
    OP_ID=None,
    target_temps=(-15, -20, -25, -30),
    temp_tolerance=0.5,
    show_title=True,
):
    """
    Calculate and plot day/night mean INP concentration at representative temperatures.
    """
    temp_dir = os.path.join(MAIN_DIR, "L2_Data", "Temp_Spec")
    save_dir = os.path.join(MAIN_DIR, "Plots", "day_night")
    os.makedirs(save_dir, exist_ok=True)

    if OP_ID is None:
        pattern = os.path.join(temp_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_*_temp.txt")
        temp_files = sorted(glob(pattern))
    else:
        temp_files = [os.path.join(temp_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp.txt")]

    temp_files = [f for f in temp_files if os.path.exists(f)]
    if not temp_files:
        raise FileNotFoundError(f"No temp files found in {temp_dir}")

    frames = []
    for fpath in temp_files:
        dfi = _read_temp_table(fpath)
        m = re.search(r"_op_id_(\d+)_temp\.txt$", os.path.basename(fpath))
        dfi["op_id"] = int(m.group(1)) if m else np.nan
        frames.append(dfi)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["cn_ice"] > 0].copy()
    df["period"] = _tag_day_night(df["datetime"])

    # Aggregate day/night means for each target temperature
    rows = []
    for t in target_temps:
        sel = df[np.abs(df["Temp_start"] - t) <= temp_tolerance]
        group = sel.groupby("period")["cn_ice"].mean()
        rows.append(
            {
                "target_temp": t,
                "day_mean": float(group.get("Day (08-18)", np.nan)),
                "night_mean": float(group.get("Night (18-08)", np.nan)),
            }
        )
    result_df = pd.DataFrame(rows)

    # Nature-like color style
    day_color = "#4DBBD5"    # cyan
    night_color = "#E64B35"  # orange-red

    x = np.arange(len(target_temps))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.8), dpi=170)
    ax.bar(x - width / 2, result_df["day_mean"], width=width, color=day_color, alpha=0.92, label="Day (08-18)")
    ax.bar(
        x + width / 2,
        result_df["night_mean"],
        width=width,
        color=night_color,
        alpha=0.92,
        label="Night (18-08)",
    )

    ax.set_xticks(x)
    ax.set_xticklabels([f"{t}°C" for t in target_temps], fontsize=11)
    ax.set_ylabel(r"INP concentration (std L$^{-1}$)", fontsize=12)
    if show_title:
        ax.set_title(f"{PINE_ID} {CAMPAIGN} | Day/Night mean INP", fontsize=13)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.legend(frameon=False, fontsize=10)
    ax.set_yscale("log")
    plt.tight_layout()

    if OP_ID is None:
        fig_name = f"{PINE_ID}_{CAMPAIGN}_day_night_mean_inp.png"
        csv_name = f"{PINE_ID}_{CAMPAIGN}_day_night_mean_inp.csv"
    else:
        fig_name = f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_day_night_mean_inp.png"
        csv_name = f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_day_night_mean_inp.csv"
    fig_path = os.path.join(save_dir, fig_name)
    csv_path = os.path.join(save_dir, csv_name)
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)
    result_df.to_csv(csv_path, index=False, encoding="utf-8")

    print(f"绘图已保存至: {fig_path}")
    print(f"统计结果CSV已保存至: {csv_path}")
    return result_df
