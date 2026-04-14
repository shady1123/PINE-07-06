import argparse
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


def read_cn_file(cn_path: str) -> pd.DataFrame:
    # 自动找到表头行（以 t_rel 开头）
    with open(cn_path, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("t_rel\t"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find data header line in {cn_path}")

    df = pd.read_csv(cn_path, sep="\t", skiprows=header_idx, header=0, encoding="latin1")
    # 确保关键列为数值
    for col in ["t_rel", "flow", "n_ice", "cn_ice", "opc_n", "run_modus"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def conc(flow_stdL_min: float, count: float, duration_s: float) -> float:
    # 项目公式: count / (flow * time/60)
    if flow_stdL_min <= 0 or duration_s <= 0 or np.isnan(count):
        return np.nan
    return count / (flow_stdL_min * duration_s / 60.0)


def recompute_inp_from_cn(df_cn: pd.DataFrame) -> dict:
    # flush: run_modus == 1
    # expansion: run_modus == 2
    flush = df_cn[df_cn["run_modus"] == 1].copy()
    exp = df_cn[df_cn["run_modus"] == 2].copy()

    if len(flush) == 0 or len(exp) == 0:
        raise ValueError("Missing flush or expansion segment in cn file.")

    # 与项目一致：持续时间 = 最后t_rel - 最初t_rel + dt
    # dt可由相邻t_rel估计（通常1s或3s）
    t_rel_sorted = df_cn["t_rel"].dropna().sort_values().unique()
    if len(t_rel_sorted) < 2:
        raise ValueError("Cannot infer dt from t_rel.")
    dt = np.median(np.diff(t_rel_sorted))

    t_flush = float(flush["t_rel"].iloc[-1] - flush["t_rel"].iloc[0] + dt)
    t_exp = float(exp["t_rel"].iloc[-1] - exp["t_rel"].iloc[0] + dt)

    n_ice_flush = float(flush["n_ice"].sum())
    n_ice_0 = float(exp["n_ice"].sum())

    flow_flush = float(flush["flow"].mean())
    flow_exp = float(exp["flow"].mean())

    inp_cn_flush = conc(flow_flush, n_ice_flush, t_flush)
    inp_cn_0 = conc(flow_exp, n_ice_0, t_exp)

    return {
        "INP_count": n_ice_0,
        "INP_cn_0": inp_cn_0,
        "INP_cn_flush": inp_cn_flush,
        "dt_inferred_s": dt,
        "t_flush_s": t_flush,
        "t_exp_s": t_exp,
        "flow_flush_mean": flow_flush,
        "flow_exp_mean": flow_exp,
    }


def compare_with_ice_file(ice_path: str, run_id: int, recomputed: dict) -> pd.DataFrame:
    # 自动找 ice 数据表头
    with open(ice_path, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("run_id\t"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find data header line in {ice_path}")

    df_ice = pd.read_csv(ice_path, sep="\t", skiprows=header_idx, header=0, encoding="latin1")
    df_ice["run_id"] = pd.to_numeric(df_ice["run_id"], errors="coerce")
    row = df_ice[df_ice["run_id"] == run_id]
    if len(row) == 0:
        raise ValueError(f"run_id={run_id} not found in {ice_path}")
    row = row.iloc[0]

    report = pd.DataFrame(
        {
            "metric": ["INP_count", "INP_cn_0", "INP_cn_flush"],
            "recomputed": [
                recomputed["INP_count"],
                recomputed["INP_cn_0"],
                recomputed["INP_cn_flush"],
            ],
            "ice_file": [
                pd.to_numeric(row.get("INP_count"), errors="coerce"),
                pd.to_numeric(row.get("INP_cn_0"), errors="coerce"),
                pd.to_numeric(row.get("INP_cn_flush"), errors="coerce"),
            ],
        }
    )
    report["abs_diff"] = (report["recomputed"] - report["ice_file"]).abs()
    rel = report["abs_diff"] / report["ice_file"].replace(0, np.nan) * 100
    report["rel_diff_%"] = rel
    report["rel_diff_display"] = report["rel_diff_%"].map(
        lambda x: "NA(denominator=0)" if pd.isna(x) else f"{x:.6f}"
    )
    return report


def parse_run_id_from_cn_filename(cn_path: Path) -> int:
    match = re.search(r"run_id_(\d+)_cn", cn_path.name)
    if not match:
        raise ValueError(f"Cannot parse run_id from filename: {cn_path.name}")
    return int(match.group(1))


def find_ice_file_from_op_dir(op_dir: Path) -> Path:
    candidate_dirs = [
        op_dir.parent / "exportdata_ice",
        op_dir.parent.parent / "exportdata_ice",
        op_dir / "exportdata_ice",
    ]
    for ice_dir in candidate_dirs:
        ice_files = sorted(ice_dir.glob("*_ice.txt"))
        if ice_files:
            if len(ice_files) > 1:
                print(f"Warning: multiple ice files found in {ice_dir}, using {ice_files[0].name}")
            return ice_files[0]
    searched = ", ".join(str(p) for p in candidate_dirs)
    raise FileNotFoundError(f"No *_ice.txt found. Searched: {searched}")


def build_run_summary(cmp_df: pd.DataFrame, run_id: int, cn_file: Path, recomputed: dict) -> dict:
    row_count = cmp_df.loc[cmp_df["metric"] == "INP_count"].iloc[0]
    row_cn0 = cmp_df.loc[cmp_df["metric"] == "INP_cn_0"].iloc[0]
    row_flush = cmp_df.loc[cmp_df["metric"] == "INP_cn_flush"].iloc[0]
    return {
        "run_id": run_id,
        "cn_file": str(cn_file),
        "INP_count_recomputed": row_count["recomputed"],
        "INP_count_ice": row_count["ice_file"],
        "INP_count_abs_diff": row_count["abs_diff"],
        "INP_count_rel_diff_display": row_count["rel_diff_display"],
        "INP_cn_0_recomputed": row_cn0["recomputed"],
        "INP_cn_0_ice": row_cn0["ice_file"],
        "INP_cn_0_abs_diff": row_cn0["abs_diff"],
        "INP_cn_0_rel_diff_display": row_cn0["rel_diff_display"],
        "INP_cn_flush_recomputed": row_flush["recomputed"],
        "INP_cn_flush_ice": row_flush["ice_file"],
        "INP_cn_flush_abs_diff": row_flush["abs_diff"],
        "INP_cn_flush_rel_diff_display": row_flush["rel_diff_display"],
        "dt_inferred_s": recomputed["dt_inferred_s"],
        "t_flush_s": recomputed["t_flush_s"],
        "t_exp_s": recomputed["t_exp_s"],
        "flow_flush_mean": recomputed["flow_flush_mean"],
        "flow_exp_mean": recomputed["flow_exp_mean"],
    }


def run_single(cn_file: Path, ice_file: Path, run_id: int) -> None:
    df_cn = read_cn_file(str(cn_file))
    recomputed = recompute_inp_from_cn(df_cn)
    print("Recomputed:", recomputed)
    cmp_df = compare_with_ice_file(str(ice_file), run_id, recomputed)
    print("\nComparison:")
    print(cmp_df[["metric", "recomputed", "ice_file", "abs_diff", "rel_diff_display"]].to_string(index=False))


def run_batch(
    op_dir: Path, output_csv: Path, only_dt: Optional[int] = None, ice_file: Optional[Path] = None
) -> None:
    cn_files = sorted(op_dir.glob("*_cn*.txt"))
    if not cn_files:
        raise FileNotFoundError(f"No cn files found in {op_dir}")
    if only_dt in (1, 3):
        if only_dt == 1:
            cn_files = [p for p in cn_files if "_cn_1sec" in p.name]
        else:
            cn_files = [p for p in cn_files if "_cn_1sec" not in p.name]
        if not cn_files:
            raise FileNotFoundError(
                f"No cn files found in {op_dir} after applying only_dt={only_dt} filter"
            )

    if ice_file is None:
        ice_file = find_ice_file_from_op_dir(op_dir)
    elif not ice_file.exists():
        raise FileNotFoundError(f"Provided --ice-file does not exist: {ice_file}")
    print(f"Using ice file: {ice_file}")
    if only_dt in (1, 3):
        print(f"Found {len(cn_files)} cn files in: {op_dir} (filtered by only_dt={only_dt})")
    else:
        print(f"Found {len(cn_files)} cn files in: {op_dir}")

    summary_rows = []
    for cn_file in cn_files:
        try:
            run_id = parse_run_id_from_cn_filename(cn_file)
            df_cn = read_cn_file(str(cn_file))
            recomputed = recompute_inp_from_cn(df_cn)
            cmp_df = compare_with_ice_file(str(ice_file), run_id, recomputed)
            summary_rows.append(build_run_summary(cmp_df, run_id, cn_file, recomputed))
            print(f"[OK] run_id={run_id} -> compared")
        except Exception as exc:
            summary_rows.append(
                {
                    "run_id": np.nan,
                    "cn_file": str(cn_file),
                    "error": str(exc),
                }
            )
            print(f"[ERR] {cn_file.name}: {exc}")

    summary_df = pd.DataFrame(summary_rows)
    summary_df.sort_values(by=["run_id", "cn_file"], inplace=True, na_position="last")
    summary_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\nBatch comparison saved: {output_csv}")
    print(summary_df.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute and compare INP metrics with *_ice.txt")
    parser.add_argument("--mode", choices=["single", "batch"], default="single")
    parser.add_argument("--cn-file", type=Path, help="Path to a single *_cn.txt file")
    parser.add_argument("--ice-file", type=Path, help="Path to *_ice.txt file")
    parser.add_argument("--run-id", type=int, help="run_id for single mode")
    parser.add_argument(
        "--op-dir",
        type=Path,
        help="Directory containing run-wise cn files, e.g. .../exportdata_cn/OP1",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("inp_comparison_summary.csv"),
        help="Output CSV path for batch mode",
    )
    parser.add_argument(
        "--only-dt",
        type=int,
        choices=[1, 3],
        default=None,
        help="Batch mode only: compare only 1s files (_cn_1sec) or only 3s files (_cn)",
    )
    args = parser.parse_args()

    if args.mode == "single":
        if not args.cn_file or not args.ice_file or args.run_id is None:
            raise ValueError("Single mode requires --cn-file, --ice-file, and --run-id")
        run_single(args.cn_file, args.ice_file, args.run_id)
        return

    if not args.op_dir:
        raise ValueError("Batch mode requires --op-dir")
    run_batch(args.op_dir, args.output_csv, args.only_dt, args.ice_file)


if __name__ == "__main__":
    main()

    # python .\check.py --mode batch --op-dir "D:\Download\PINE-07-06\20260410_test\L1_Data\exportdata\exportdata_cn\OP1" --output-csv ".\inp_comparison_summary.csv"
    # python .\check.py --mode batch --op-dir "D:\Download\PINE-07-06\20260410_test\L1_Data\exportdata\exportdata_cn\OP1" --only-dt 3 --output-csv ".\inp_comparison_summary_3sec.csv"
    # python .\check.py --mode batch --op-dir "D:\Download\PINE-07-06\20260410_test\L1_Data\exportdata\exportdata_cn\OP1" --only-dt 1 --output-csv ".\inp_comparison_summary_1sec.csv"