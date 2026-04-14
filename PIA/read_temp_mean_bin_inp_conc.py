import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator, LogFormatterMathtext


def _read_temp_mean_table(txt_path):
    """Locate the table header and read temp spectrum mean data."""
    with open(txt_path, "r", encoding="latin1") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Temp_start\t"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Cannot find table header in {txt_path}")

    # Use numpy for lightweight tab-separated loading
    data = np.genfromtxt(
        txt_path,
        delimiter="\t",
        names=True,
        dtype=None,
        encoding="utf-8",
        skip_header=header_idx,
    )
    if data.size == 0:
        raise ValueError("No valid temp spectrum data found.")
    return data


def read_temp_mean_bin_inp_conc(
    OP_ID,
    MAIN_DIR,
    PINE_ID,
    CAMPAIGN,
    smooth_window=3,
    show_std_band=True,
    show_smooth_curve=True,
    show_title=True,
):
    # 拼接文件路径
    SAVEPATH = os.path.join(MAIN_DIR, 'Plots')
    PINE_DIR = os.path.join(MAIN_DIR, 'L2_Data', 'Temp_Spec')
    txt_filename = f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_temp_mean.txt'
    txt_path = os.path.join(PINE_DIR, txt_filename)
    
    # 校验文件是否存在
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f'文件不存在: {txt_path}')

    # 自动创建保存目录
    os.makedirs(SAVEPATH, exist_ok=True)

    arr = _read_temp_mean_table(txt_path)
    temp_start = np.asarray(arr["Temp_start"], dtype=float)
    cn_ice = np.asarray(arr["cn_ice"], dtype=float)
    cn_ice_std = np.asarray(arr["cn_ice_std"], dtype=float)

    # 略去0值及无效值，避免对数坐标下拥挤/失真
    valid = np.isfinite(temp_start) & np.isfinite(cn_ice) & np.isfinite(cn_ice_std) & (cn_ice > 0)
    temp_start = temp_start[valid]
    cn_ice = cn_ice[valid]
    cn_ice_std = cn_ice_std[valid]
    if temp_start.size == 0:
        raise ValueError("No positive cn_ice values available after filtering.")

    # 按温度排序，保证曲线连续
    order = np.argsort(temp_start)
    temp_start = temp_start[order]
    cn_ice = cn_ice[order]
    cn_ice_std = cn_ice_std[order]

    # 平滑曲线（可配置窗口，窗口会被校正为>=1且不大于数据长度）
    try:
        smooth_window = int(smooth_window)
    except (TypeError, ValueError):
        smooth_window = 3
    smooth_window = max(1, min(smooth_window, cn_ice.size))
    # 优先使用奇数窗口，便于居中
    if smooth_window > 1 and smooth_window % 2 == 0:
        smooth_window -= 1
    kernel = np.ones(smooth_window) / smooth_window
    cn_ice_smooth = np.convolve(cn_ice, kernel, mode="same")

    plt.figure(figsize=(9, 5.5), dpi=160)
    plt.plot(
        temp_start,
        cn_ice,
        marker="o",
        markersize=3.5,
        linestyle="-",
        color="#1f77b4",
        linewidth=1.4,
        alpha=0.9,
        label="INP mean",
    )
    if show_smooth_curve and smooth_window > 1:
        plt.plot(
            temp_start,
            cn_ice_smooth,
            linestyle="-",
            color="#d62728",
            linewidth=1.6,
            alpha=0.9,
            label=f"{smooth_window}-point smoothed",
        )
    if show_std_band:
        # 在log图中，std大于均值会导致下界接近0并“铺满整图”。
        # 仅在相对不确定度合理（std <= 0.8*mean）的位置画误差带。
        rel_ok = cn_ice_std <= (0.8 * cn_ice)
        if np.any(rel_ok):
            lower = np.maximum(cn_ice[rel_ok] - cn_ice_std[rel_ok], 1e-6)
            upper = cn_ice[rel_ok] + cn_ice_std[rel_ok]
            plt.fill_between(
                temp_start[rel_ok],
                lower,
                upper,
                color="#1f77b4",
                alpha=0.15,
                label=r"$\pm1\sigma$ (filtered)",
            )
        else:
            print("Warning: std band skipped because std is too large relative to mean.")

    plt.xlabel("Temperature (°C)", fontsize=11)
    plt.ylabel(r"INP concentration (std L$^{-1}$)", fontsize=11)
    if show_title:
        plt.title(f"{PINE_ID} {CAMPAIGN} | OP {OP_ID} | INP temperature spectrum", fontsize=12)
    plt.yscale("log")
    plt.grid(True, which="major", alpha=0.30, linestyle="-")
    plt.grid(True, which="minor", alpha=0.15, linestyle=":")
    plt.legend(frameon=False, fontsize=9, loc="best")
    plt.tight_layout()

    # x轴不留白：显式设置范围 + 去除自动margin
    x_min = float(np.min(temp_start))
    x_max = float(np.max(temp_start))
    plt.xlim(x_min, x_max)
    plt.margins(x=0)
    # 确保最左侧和最右侧都有主刻度标签
    step = 2.5
    start_tick = np.ceil(x_min / step) * step
    end_tick = np.floor(x_max / step) * step
    x_ticks = np.arange(start_tick, end_tick + 0.5 * step, step)
    # 强制包含左右边界；最后一个刻度默认用最大温度
    x_ticks = np.unique(np.concatenate(([x_min], x_ticks, [x_max])))
    x_ticks = np.round(x_ticks, 2)
    plt.xticks(x_ticks)

    # y轴范围按主数据自适应，避免误差带把跨度拉得过大
    y_pos = cn_ice[np.isfinite(cn_ice) & (cn_ice > 0)]
    if y_pos.size > 0:
        y_low = np.nanmin(y_pos) * 0.7
        y_high = np.nanmax(y_pos) * 1.3
        if y_low <= 0:
            y_low = np.nanmin(y_pos)
        plt.ylim(y_low, y_high)
    # 对数坐标使用标准log刻度，避免y轴刻度消失
    ax = plt.gca()
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=8))
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1, numticks=12))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10.0))

    fig_path = os.path.join(SAVEPATH, f'{PINE_ID}_{CAMPAIGN}_op_id_{OP_ID}_inp_conc_vs_temp.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'绘图已保存至: {fig_path}')

    return np.column_stack([temp_start, cn_ice, cn_ice_std]).tolist()
