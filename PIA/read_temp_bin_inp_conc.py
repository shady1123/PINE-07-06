import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _read_temp_table(txt_path):
    with open(txt_path, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Temp_start\t"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find table header in {txt_path}")
    df = pd.read_csv(txt_path, sep="\t", skiprows=header_idx, header=0, encoding="latin1")
    required = {"Temp_start", "run_id", "datetime", "cn_ice"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in temp file: {missing}")
    df["Temp_start"] = pd.to_numeric(df["Temp_start"], errors="coerce")
    df["cn_ice"] = pd.to_numeric(df["cn_ice"], errors="coerce")
    df["run_id"] = pd.to_numeric(df["run_id"], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", format="mixed")
    df = df.dropna(subset=["Temp_start", "cn_ice", "run_id", "datetime"])
    return df


def _plot_big_run_spectrum(df_big, save_path, title, x_limits=None, show_title=True):
    # remove non-positive values for log scale
    d = df_big[df_big["cn_ice"] > 0].copy()
    if len(d) == 0:
        return
    spec = (
        d.groupby("Temp_start", as_index=False)["cn_ice"]
        .agg(["median", "std", "count"])
        .reset_index()
        .rename(columns={"median": "cn_med", "std": "cn_std"})
    )
    spec["cn_std"] = spec["cn_std"].fillna(0.0)
    spec = spec.sort_values("Temp_start")

    x = spec["Temp_start"].to_numpy()
    y = spec["cn_med"].to_numpy()
    y_std = spec["cn_std"].to_numpy()

    plt.figure(figsize=(8.8, 5.6), dpi=170)
    plt.plot(x, y, marker="o", markersize=3.8, linewidth=1.5, color="#1f77b4", label="median")

    rel_ok = y_std <= (0.8 * y)
    if np.any(rel_ok):
        lower = np.maximum(y[rel_ok] - y_std[rel_ok], 1e-6)
        upper = y[rel_ok] + y_std[rel_ok]
        plt.fill_between(x[rel_ok], lower, upper, color="#1f77b4", alpha=0.15, label=r"$\pm1\sigma$")

    plt.yscale("log")
    plt.xlabel("Temperature (°C)", fontsize=11)
    plt.ylabel(r"INP concentration (std L$^{-1}$)", fontsize=11)
    if show_title:
        plt.title(title, fontsize=12)
    plt.grid(True, which="major", alpha=0.3)
    plt.grid(True, which="minor", alpha=0.15, linestyle=":")
    if x_limits is None:
        x_min = float(np.min(x))
        x_max = float(np.max(x))
    else:
        x_min, x_max = x_limits
    plt.xlim(x_min, x_max)
    plt.margins(x=0)

    # 2 degree ticks and always include rightmost boundary
    step = 2.0
    start_tick = np.ceil(x_min / step) * step
    end_tick = np.floor(x_max / step) * step
    ticks = np.arange(start_tick, end_tick + 0.5 * step, step)
    ticks = np.unique(np.concatenate(([x_min], ticks, [x_max])))
    ticks = np.round(ticks, 2)
    # 防止标签过密重叠：过多时隔一个显示
    if len(ticks) > 12:
        ticks = ticks[::2]
        if ticks[-1] != round(x_max, 2):
            ticks = np.append(ticks, round(x_max, 2))
    plt.xticks(ticks, rotation=0, ha="center")
    plt.legend(frameon=False, fontsize=9, loc="best")
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()


def read_temp_bin_inp_conc(
    OP_ID,
    MAIN_DIR,
    PINE_ID,
    CAMPAIGN,
    runs_per_big_run=10,
    unify_temp_range=True,
    start_run_id=None,
    end_run_id=None,
    export_group_csv=True,
    group_csv_path=None,
    show_title=True,
):
    save_dir = os.path.join(MAIN_DIR, "Plots", "bin_temp")
    os.makedirs(save_dir, exist_ok=True)
    temp_dir = os.path.join(MAIN_DIR, "L2_Data", "Temp_Spec")
    txt_file = os.path.join(temp_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp.txt")
    if not os.path.exists(txt_file):
        raise FileNotFoundError(f"文件不存在: {txt_file}")

    df = _read_temp_table(txt_file)
    # run-level index by time
    run_df = (
        df.groupby("run_id", as_index=False)
        .agg(
            datetime_start=("datetime", "min"),
            datetime_end=("datetime", "max"),
            temp_min=("Temp_start", "min"),
            temp_max=("Temp_start", "max"),
        )
        .sort_values("run_id")
        .reset_index(drop=True)
    )
    if len(run_df) == 0:
        return []
    if runs_per_big_run < 1:
        runs_per_big_run = 10
    if start_run_id is not None:
        start_run_id = int(start_run_id)
    if end_run_id is not None:
        end_run_id = int(end_run_id)
    if (start_run_id is not None) and (end_run_id is not None) and (start_run_id > end_run_id):
        raise ValueError("start_run_id cannot be greater than end_run_id")

    if start_run_id is not None:
        run_df = run_df[run_df["run_id"] >= start_run_id]
    if end_run_id is not None:
        run_df = run_df[run_df["run_id"] <= end_run_id]
    run_df = run_df.reset_index(drop=True)
    if (start_run_id is not None) or (end_run_id is not None):
        if len(run_df) == 0:
            print(
                f"No runs left after applying run_id range "
                + f"[{start_run_id if start_run_id is not None else '-inf'}, "
                + f"{end_run_id if end_run_id is not None else '+inf'}]."
            )
            return []

    # Optional shared x-range for cross-big-run comparison
    shared_xlim = None
    if unify_temp_range:
        global_min = float(df["Temp_start"].min())
        global_max = float(df["Temp_start"].max())
        shared_xlim = (global_min, global_max)

    outputs = []
    big_run_id = 0
    for start in range(0, len(run_df), runs_per_big_run):
        chunk = run_df.iloc[start : start + runs_per_big_run, :]
        if len(chunk) == 0:
            continue
        big_run_id += 1
        run_ids = chunk["run_id"].to_numpy()
        df_big = df[df["run_id"].isin(run_ids)].copy()
        t0 = chunk["datetime_start"].min()
        t1 = chunk["datetime_end"].max()
        t0_str = pd.to_datetime(t0).strftime("%Y%m%d_%H%M")
        t1_str = pd.to_datetime(t1).strftime("%Y%m%d_%H%M")

        fig_name = (
            f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_bigrun_{big_run_id}_"
            f"run_{int(run_ids.min())}-{int(run_ids.max())}_{t0_str}-{t1_str}.png"
        )
        fig_path = os.path.join(save_dir, fig_name)
        title = (
            f"{PINE_ID} {CAMPAIGN} | OP {OP_ID} | Big run {big_run_id}\n"
            f"run_id {int(run_ids.min())}-{int(run_ids.max())} | "
            f"{pd.to_datetime(t0).strftime('%Y-%m-%d %H:%M')} to "
            f"{pd.to_datetime(t1).strftime('%Y-%m-%d %H:%M')}"
        )
        _plot_big_run_spectrum(df_big, fig_path, title, x_limits=shared_xlim, show_title=show_title)
        print(f"绘图已保存至: {fig_path}")
        outputs.append(
            {
                "big_run": big_run_id,
                "run_id_start": int(run_ids.min()),
                "run_id_end": int(run_ids.max()),
                "start_time": t0,
                "end_time": t1,
                "num_runs": len(run_ids),
                "temp_range_used": shared_xlim
                if shared_xlim is not None
                else (float(df_big["Temp_start"].min()), float(df_big["Temp_start"].max())),
                "figure_path": fig_path,
            }
        )

    print(
        f"Generated {len(outputs)} big-run figure(s) in {save_dir}. "
        + f"unify_temp_range={unify_temp_range}, runs_per_big_run={runs_per_big_run}, "
        + f"start_run_id={start_run_id}, end_run_id={end_run_id}"
    )
    if export_group_csv:
        if group_csv_path is None:
            csv_name = f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_big_run_groups.csv"
            group_csv_path = os.path.join(save_dir, csv_name)
        df_out = pd.DataFrame(outputs).copy()
        if len(df_out) > 0:
            # Add explicit run_id list column for traceability.
            # The range columns already exist, list helps exact membership checks.
            # build from recorded range for compact output
            df_out["run_id_list"] = df_out.apply(
                lambda r: "|".join(
                    str(i) for i in range(int(r["run_id_start"]), int(r["run_id_end"]) + 1)
                ),
                axis=1,
            )
            # Force text for spreadsheet tools to avoid scientific notation.
            df_out["run_id_list"] = df_out["run_id_list"].map(lambda s: f"'{s}")
        df_out.to_csv(group_csv_path, index=False, encoding="utf-8")
        print(f"分组信息CSV已保存至: {group_csv_path}")
    return outputs
