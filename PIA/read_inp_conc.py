import os
import matplotlib.pyplot as plt
from datetime import datetime

import numpy as np
import pandas as pd


def _read_table_with_header(file_path, header_prefix):
    """Read tabular section by locating header line prefix."""
    with open(file_path, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith(header_prefix):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find header '{header_prefix}' in {file_path}")
    return pd.read_csv(file_path, sep="\t", skiprows=header_idx, header=0, encoding="latin1")


def _to_datetime(values):
    out = []
    for dt in values:
        if isinstance(dt, datetime):
            out.append(dt)
            continue
        try:
            out.append(datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S.%f"))
        except ValueError:
            out.append(datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S"))
    return out


def _extract_start_time(file_path):
    """Extract run start time from metadata line: 'start: YYYY-MM-DD HH:MM:SS'."""
    with open(file_path, "r", encoding="latin1") as f:
        for line in f:
            text = line.strip()
            if text.startswith("start:"):
                value = text.split("start:", 1)[1].strip()
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    return None


def read_input_conc(
    OP_ID,
    MAIN_DIR,
    PINE_ID,
    CAMPAIGN,
    series_source="ice_run",
    cn_dt=3,
    downsample_n=1,
    min_cn_ice=None,
    resample_minutes=None,
    show_title=True,
):
    """
    Plot INP time series from PIA outputs.

    Parameters
    ----------
    OP_ID : int
    MAIN_DIR : str
        Campaign analysis directory.
    PINE_ID : str
    CAMPAIGN : str
    series_source : str
        "ice_run" -> run-wise series from *_ice.txt using INP_cn_0
        "cn_bin"  -> time-bin series from *_cn*.txt using cn_ice
    cn_dt : int
        Used when series_source="cn_bin". 3 reads *_cn.txt, 1 reads *_cn_1sec.txt.
    downsample_n : int
        Used when series_source="cn_bin". Keep every Nth point for plotting.
        1 means no downsampling.
    min_cn_ice : float or None
        Used when series_source="cn_bin". Filter out points with cn_ice <= min_cn_ice.
    resample_minutes : int or None
        Used when series_source="cn_bin". If set, aggregate cn_ice by time bins of N minutes
        using median to improve readability.
    """
    SAVEPATH = os.path.join(MAIN_DIR, 'Plots')
    os.makedirs(SAVEPATH, exist_ok=True)

    if series_source == "ice_run":
        ice_dir = os.path.join(MAIN_DIR, "L1_Data", "exportdata", "exportdata_ice")
        ice_file = os.path.join(ice_dir, f"{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_ice.txt")
        if not os.path.exists(ice_file):
            raise FileNotFoundError(f"File not found: {ice_file}")
        df = _read_table_with_header(ice_file, "run_id\t")
        for c in ["INP_cn_0", "INP_count", "INP_cn_flush"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["datetime"] = _to_datetime(df["datetime"].tolist())
        if min_cn_ice is not None:
            df = df[df["INP_cn_0"] > float(min_cn_ice)]
        if resample_minutes is not None:
            if int(resample_minutes) < 1:
                raise ValueError("resample_minutes must be >= 1")
            df = (
                df.set_index("datetime")[["INP_cn_0"]]
                .resample(f"{int(resample_minutes)}min")
                .median()
                .dropna()
                .reset_index()
            )
        if downsample_n is None or downsample_n < 1:
            downsample_n = 1
        if downsample_n > 1:
            df = df.iloc[::downsample_n, :].reset_index(drop=True)
        x = df["datetime"].tolist()
        y = df["INP_cn_0"].to_numpy()
        y_label = "INP_cn_0 (stdL-1)"
        file_tag = "runwise_ice"
        print(
            f"Using run-wise data from: {ice_file}, "
            + f"downsample_n={downsample_n}, min_cn_ice={min_cn_ice}, "
            + f"resample_minutes={resample_minutes}"
        )
    elif series_source == "cn_bin":
        cn_dir = os.path.join(MAIN_DIR, "L1_Data", "exportdata", "exportdata_cn", f"OP{OP_ID}")
        if not os.path.isdir(cn_dir):
            raise FileNotFoundError(f"Directory not found: {cn_dir}")
        suffix = "_cn_1sec.txt" if cn_dt == 1 else "_cn.txt"
        cn_files = sorted(
            [os.path.join(cn_dir, f) for f in os.listdir(cn_dir) if f.endswith(suffix)]
        )
        if not cn_files:
            raise FileNotFoundError(f"No cn files ending with '{suffix}' in {cn_dir}")

        df_list = []
        for fpath in cn_files:
            dfi = _read_table_with_header(fpath, "t_rel\t")
            if "cn_ice" not in dfi.columns:
                continue
            # Preferred: use explicit date column if available.
            if "date" in dfi.columns:
                dfi["date"] = pd.to_datetime(dfi["date"], errors="coerce", format="mixed")
            # Fallback: construct datetime from metadata start + t_rel.
            elif "t_rel" in dfi.columns:
                dfi["t_rel"] = pd.to_numeric(dfi["t_rel"], errors="coerce")
                run_start = _extract_start_time(fpath)
                if run_start is None:
                    continue
                dfi["date"] = run_start + pd.to_timedelta(dfi["t_rel"], unit="s")
            else:
                continue
            dfi["cn_ice"] = pd.to_numeric(dfi["cn_ice"], errors="coerce")
            df_list.append(dfi[["date", "cn_ice"]])
        if not df_list:
            raise ValueError("No valid cn data found for plotting.")
        df_all = pd.concat(df_list, ignore_index=True).dropna(subset=["date"]).sort_values("date")
        if min_cn_ice is not None:
            df_all = df_all[pd.to_numeric(df_all["cn_ice"], errors="coerce") > float(min_cn_ice)]
        if resample_minutes is not None:
            if int(resample_minutes) < 1:
                raise ValueError("resample_minutes must be >= 1")
            df_all = (
                df_all.set_index("date")[["cn_ice"]]
                .resample(f"{int(resample_minutes)}min")
                .median()
                .dropna()
                .reset_index()
            )
        if downsample_n is None or downsample_n < 1:
            downsample_n = 1
        if downsample_n > 1:
            df_all = df_all.iloc[::downsample_n, :].reset_index(drop=True)
        x = df_all["date"].tolist()
        y = df_all["cn_ice"].to_numpy()
        y_label = "cn_ice (stdL-1)"
        file_tag = f"timebin_cn_{cn_dt}sec"
        print(
            f"Using time-bin data from: {cn_dir} ({len(cn_files)} files), "
            + f"downsample_n={downsample_n}, min_cn_ice={min_cn_ice}, "
            + f"resample_minutes={resample_minutes}"
        )
    else:
        raise ValueError("series_source must be 'ice_run' or 'cn_bin'")

    if len(x) == 0:
        raise ValueError("No time points available for plotting.")

    plt.figure(figsize=(12, 6))
    plt.scatter(x, y, color="#1f77b4", alpha=0.6, s=20)
    plt.xlabel("Datetime")
    plt.ylabel(y_label)
    title = f"INP Time Series ({series_source}, OP_ID: {OP_ID})"
    if series_source in ("cn_bin", "ice_run"):
        extras = []
        if downsample_n > 1:
            extras.append(f"1/{downsample_n} points")
        if min_cn_ice is not None:
            extras.append(f"cn_ice>{min_cn_ice}")
        if resample_minutes is not None:
            extras.append(f"{resample_minutes}min median")
        if extras:
            title = f"{title[:-1]}, " + ", ".join(extras) + ")"
    if show_title:
        plt.title(title)
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.xlim(x[0], x[-1])
    if np.nanmax(y) > 0:
        plt.yscale("log")

    out_png = (
        f"{SAVEPATH}/{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_INP_concentration_{file_tag}.png"
    )
    plt.savefig(out_png)
    print(f"图表已保存到: {out_png}")
    plt.close()

    return {"time": x, "inp": y, "source": series_source}
