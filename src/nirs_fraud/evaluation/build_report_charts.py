from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MPLCONFIGDIR = ROOT / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


OUTPUT_DIR = ROOT / "outputs" / "report_charts"
EXP3_DIR = ROOT / "outputs" / "experiment_03"
VARIANT_ORDER = ["original", "paraphrase", "subtle", "asr_noise", "all_augmented"]
ARCHITECTURE_ORDER = ["single_llm", "llm_checklist", "llm_self_check", "llm_ensemble"]
ARCHITECTURE_LABELS = {
    "single_llm": "Qwen single",
    "llm_checklist": "Qwen checklist",
    "llm_self_check": "Qwen self-check",
    "llm_ensemble": "Qwen ensemble",
}
EXPERIMENT_LABELS = {
    "Experiment 1": "Эксперимент 1\n(базовый набор)",
    "Experiment 2 all_augmented": "Эксперимент 2\n(аугментации)",
    "Experiment 3": "Эксперимент 3\n(внешний бенчмарк)",
}
DISPLAY_NAME_RU = {
    "Rules baseline": "Правила",
    "Qwen single": "LLM: single",
    "Qwen checklist": "LLM: checklist",
    "Qwen self-check": "LLM: self-check",
    "Qwen ensemble": "LLM: ensemble",
}
ARCHITECTURE_CONFIG_LABELS_RU = {
    "single_llm": "single_llm",
    "llm_checklist": "llm_checklist",
    "llm_self_check": "llm_self_check",
    "llm_ensemble": "llm_ensemble",
}
VARIANT_LABELS_RU = {
    "original": "оригинал",
    "paraphrase": "парафраз",
    "subtle": "тонкие\nпризнаки",
    "asr_noise": "ASR-шум",
    "all_augmented": "все\nаугментации",
}
METRIC_LABELS_RU = {
    "f1_fraud": "F1 по классу fraud",
    "recall_fraud": "Recall по классу fraud",
}


def resolve_experiment_01_dir() -> Path:
    preferred = ROOT / "outputs" / "experiment_01_2"
    fallback = ROOT / "outputs" / "experiment_01"
    return preferred if preferred.exists() else fallback


def resolve_experiment_02_dir() -> Path:
    preferred = ROOT / "outputs" / "experiment_02_2"
    fallback = ROOT / "outputs" / "experiment_02"
    return preferred if preferred.exists() else fallback


def latest_metrics_file(directory: Path, pattern: str) -> Path:
    candidates = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return candidates[0]


def latest_aggregate_metrics_file(directory: Path, prefix: str) -> Path:
    candidates = sorted(directory.glob(f"{prefix}*_metrics.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates:
        if not any(path.stem.endswith(f"_{architecture}_metrics") for architecture in ARCHITECTURE_ORDER):
            return path
    raise FileNotFoundError(f"No aggregate metrics file matching {prefix}*_metrics.csv in {directory}")


def load_experiment_01_metrics() -> pd.DataFrame:
    exp1_dir = resolve_experiment_01_dir()
    baseline = pd.read_csv(exp1_dir / "metrics.csv")
    baseline["architecture"] = "rules_baseline"
    baseline["display_name"] = "Rules baseline"
    baseline["group"] = "baseline"

    llm_path = latest_metrics_file(exp1_dir, "local_llm_experiment_01_*_metrics.csv")
    llm = pd.read_csv(llm_path)
    llm["display_name"] = llm["architecture"].map(ARCHITECTURE_LABELS)
    llm["group"] = "qwen"
    return pd.concat([baseline, llm], ignore_index=True, sort=False)


def load_experiment_02_metrics() -> tuple[pd.DataFrame, pd.DataFrame]:
    exp2_dir = resolve_experiment_02_dir()
    baseline = pd.read_csv(exp2_dir / "experiment_02_metrics.csv")
    baseline["architecture"] = "rules_baseline"
    baseline["display_name"] = "Rules baseline"

    llm_path = latest_aggregate_metrics_file(exp2_dir, "local_llm_experiment_02_")
    llm = pd.read_csv(llm_path)
    llm["display_name"] = llm["architecture"].map(ARCHITECTURE_LABELS)
    return baseline, llm


def load_experiment_03_metrics() -> pd.DataFrame:
    baseline = pd.read_csv(EXP3_DIR / "experiment_03_metrics.csv")
    baseline["architecture"] = "rules_baseline"
    baseline["display_name"] = "Rules baseline"
    baseline["group"] = "baseline"

    llm_path = latest_metrics_file(EXP3_DIR, "local_llm_experiment_03_*_metrics.csv")
    llm = pd.read_csv(llm_path)
    llm["display_name"] = llm["architecture"].map(ARCHITECTURE_LABELS)
    llm["group"] = "qwen"
    return pd.concat([baseline, llm], ignore_index=True, sort=False)


def setup_theme() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["figure.dpi"] = 160
    plt.rcParams["savefig.dpi"] = 200
    plt.rcParams["axes.titlesize"] = 16
    plt.rcParams["axes.labelsize"] = 12


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def annotate_heatmap(ax, data: pd.DataFrame) -> None:
    for row_index, row_name in enumerate(data.index):
        for col_index, col_name in enumerate(data.columns):
            value = data.loc[row_name, col_name]
            if pd.isna(value):
                label = "n/a"
                color = "#666666"
            else:
                label = f"{value:.3f}"
                color = "white" if value >= 0.5 else "#222222"
            ax.text(col_index + 0.5, row_index + 0.5, label, ha="center", va="center", color=color, fontsize=11)


def format_best_configuration_label(rows: pd.DataFrame) -> str:
    max_score = rows["f1_fraud"].max()
    winners = rows[rows["f1_fraud"] == max_score].copy()
    winners["sort_order"] = winners["architecture"].map({name: index for index, name in enumerate(ARCHITECTURE_ORDER)})
    winners = winners.sort_values(["sort_order", "architecture"])
    labels = [ARCHITECTURE_CONFIG_LABELS_RU[architecture] for architecture in winners["architecture"]]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return " / ".join(labels)
    return ",\n".join(labels)


def plot_horizontal_metric(df: pd.DataFrame, metric: str, title: str, path: Path) -> None:
    ordered = df.sort_values(metric, ascending=True).copy()
    ordered["display_name_ru"] = ordered["display_name"].map(DISPLAY_NAME_RU)
    palette = ["#c44e52" if name == "Rules baseline" else "#4c72b0" for name in ordered["display_name"]]
    plt.figure(figsize=(10, 5.5))
    ax = sns.barplot(data=ordered, x=metric, y="display_name_ru", palette=palette)
    ax.set_title(title)
    ax.set_xlabel(METRIC_LABELS_RU.get(metric, metric))
    ax.set_ylabel("")
    for patch, value in zip(ax.patches, ordered[metric]):
        ax.text(value + 0.01, patch.get_y() + patch.get_height() / 2, f"{value:.3f}", va="center", fontsize=10)
    ax.set_xlim(0, 1.08)
    save_figure(path)


def plot_exp2_heatmap(baseline: pd.DataFrame, llm: pd.DataFrame, path: Path) -> None:
    combined = pd.concat([baseline, llm], ignore_index=True, sort=False)
    filtered = combined[combined["variant"].isin(VARIANT_ORDER)].copy()
    filtered["row_name"] = filtered.apply(
        lambda row: "Правила" if row["architecture"] == "rules_baseline" else DISPLAY_NAME_RU[ARCHITECTURE_LABELS[row["architecture"]]],
        axis=1,
    )
    exp2_row_order = ["Правила"] + [
        DISPLAY_NAME_RU[ARCHITECTURE_LABELS[architecture]]
        for architecture in ARCHITECTURE_ORDER
        if architecture in set(llm["architecture"])
    ]
    heatmap_df = (
        filtered.pivot(index="row_name", columns="variant", values="f1_fraud")
        .reindex(index=exp2_row_order)
        .reindex(columns=VARIANT_ORDER)
    )
    plt.figure(figsize=(11.2, 5.2))
    ax = sns.heatmap(
        heatmap_df,
        annot=False,
        cmap="YlGnBu",
        vmin=0.0,
        vmax=1.0,
        cbar_kws={"label": "F1 по классу fraud"},
        linewidths=0.5,
        linecolor="white",
    )
    annotate_heatmap(ax, heatmap_df)
    ax.set_title("Эксперимент 2: F1 по архитектурам и типам аугментаций")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(VARIANT_ORDER, rotation=0)
    save_figure(path)


def plot_exp2_robustness_lines(baseline: pd.DataFrame, llm: pd.DataFrame, path: Path) -> None:
    combined = pd.concat([baseline, llm], ignore_index=True, sort=False)
    filtered = combined[combined["variant"].isin(VARIANT_ORDER)].copy()
    filtered["display_name"] = filtered.apply(
        lambda row: "Rules baseline" if row["architecture"] == "rules_baseline" else ARCHITECTURE_LABELS[row["architecture"]],
        axis=1,
    )
    filtered["display_name_ru"] = filtered["display_name"].map(DISPLAY_NAME_RU)
    filtered["variant_ru"] = filtered["variant"].map(VARIANT_LABELS_RU)
    filtered["variant"] = pd.Categorical(filtered["variant"], categories=VARIANT_ORDER, ordered=True)
    variant_order_ru = [VARIANT_LABELS_RU[variant] for variant in VARIANT_ORDER]
    filtered["variant_ru"] = pd.Categorical(filtered["variant_ru"], categories=variant_order_ru, ordered=True)
    palette_map = {
        "Правила": "#4f78b7",
        "LLM: single": "#6f63c2",
        "LLM: checklist": "#dd8452",
        "LLM: self-check": "#55a868",
        "LLM: ensemble": "#c44e52",
    }
    plot_order = ["Правила"] + [DISPLAY_NAME_RU[ARCHITECTURE_LABELS[architecture]] for architecture in ARCHITECTURE_ORDER if architecture in set(llm["architecture"])]
    plt.figure(figsize=(11.4, 5.4))
    ax = plt.gca()
    x_positions = list(range(len(variant_order_ru)))
    last_point_labels: list[tuple[float, str, str]] = []
    for label in plot_order:
        subset = filtered[filtered["display_name_ru"] == label].sort_values("variant")
        values = subset["f1_fraud"].tolist()
        if not values:
            continue
        ax.plot(
            x_positions,
            values,
            marker="o",
            markersize=7,
            linewidth=2.8,
            color=palette_map.get(label, "#4c72b0"),
        )
        last_point_labels.append((values[-1], label, palette_map.get(label, "#4c72b0")))
    sorted_labels = sorted(last_point_labels, key=lambda item: item[0], reverse=True)
    used_y_positions: list[float] = []
    min_gap = 0.035
    for value, label, color in sorted_labels:
        adjusted_y = value
        while any(abs(adjusted_y - used_y) < min_gap for used_y in used_y_positions):
            adjusted_y -= min_gap
        used_y_positions.append(adjusted_y)
        ax.text(
            x_positions[-1] + 0.12,
            adjusted_y,
            label,
            color=color,
            va="center",
            fontsize=10,
        )
    ax.set_title("Эксперимент 2: устойчивость к аугментациям")
    ax.set_xlabel("")
    ax.set_ylabel("F1 по классу fraud")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(-0.25, len(variant_order_ru) - 0.1)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(variant_order_ru)
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", color="#d7dbe2", linewidth=0.8)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    save_figure(path)


def plot_overall_heatmap(exp1: pd.DataFrame, exp2_baseline: pd.DataFrame, exp2_llm: pd.DataFrame, exp3: pd.DataFrame, path: Path) -> None:
    exp1_rows = exp1.copy()
    exp1_rows["scenario_bucket"] = "Experiment 1"

    exp2_base = exp2_baseline[exp2_baseline["variant"] == "all_augmented"].copy()
    exp2_base["display_name"] = "Rules baseline"
    exp2_base["scenario_bucket"] = "Experiment 2 all_augmented"

    exp2_qwen = exp2_llm[exp2_llm["variant"] == "all_augmented"].copy()
    exp2_qwen["display_name"] = exp2_qwen["architecture"].map(ARCHITECTURE_LABELS)
    exp2_qwen["scenario_bucket"] = "Experiment 2 all_augmented"

    exp3_rows = exp3.copy()
    exp3_rows["scenario_bucket"] = "Experiment 3"

    combined = pd.concat(
        [
            exp1_rows[["display_name", "scenario_bucket", "f1_fraud"]],
            exp2_base[["display_name", "scenario_bucket", "f1_fraud"]],
            exp2_qwen[["display_name", "scenario_bucket", "f1_fraud"]],
            exp3_rows[["display_name", "scenario_bucket", "f1_fraud"]],
        ],
        ignore_index=True,
    )

    heatmap_df = (
        combined.pivot(index="display_name", columns="scenario_bucket", values="f1_fraud")
        .reindex(
            index=[
                "Rules baseline",
                "Qwen single",
                "Qwen checklist",
                "Qwen self-check",
                "Qwen ensemble",
            ],
            columns=["Experiment 1", "Experiment 2 all_augmented", "Experiment 3"],
        )
    )
    heatmap_df = heatmap_df.rename(index=DISPLAY_NAME_RU, columns=EXPERIMENT_LABELS)
    plt.figure(figsize=(10.6, 5.0))
    ax = sns.heatmap(
        heatmap_df,
        annot=False,
        cmap="YlOrRd",
        vmin=0.0,
        vmax=1.0,
        cbar_kws={"label": "F1 по классу fraud"},
        linewidths=0.5,
        linecolor="white",
    )
    annotate_heatmap(ax, heatmap_df)
    ax.set_title("Сравнение результатов по всем экспериментам")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(list(heatmap_df.columns), rotation=0)
    save_figure(path)


def plot_best_models_overview(exp1: pd.DataFrame, exp2_baseline: pd.DataFrame, exp2_llm: pd.DataFrame, exp3: pd.DataFrame, path: Path) -> None:
    exp1_best_qwen = exp1[exp1["group"] == "qwen"].sort_values("f1_fraud", ascending=False).iloc[0]
    exp1_base = exp1[exp1["group"] == "baseline"].iloc[0]

    exp2_best_qwen = exp2_llm[exp2_llm["variant"] == "all_augmented"].sort_values("f1_fraud", ascending=False).iloc[0]
    exp2_base = exp2_baseline[exp2_baseline["variant"] == "all_augmented"].iloc[0]

    exp3_best_qwen = exp3[exp3["group"] == "qwen"].sort_values("f1_fraud", ascending=False).iloc[0]
    exp3_base = exp3[exp3["group"] == "baseline"].iloc[0]

    plot_df = pd.DataFrame(
        [
            {
                "experiment": "Эксперимент 1\n(базовый набор)",
                "baseline_f1": exp1_base["f1_fraud"],
                "llm_f1": exp1_best_qwen["f1_fraud"],
                "llm_label": format_best_configuration_label(exp1[exp1["group"] == "qwen"]),
            },
            {
                "experiment": "Эксперимент 2\n(аугментации)",
                "baseline_f1": exp2_base["f1_fraud"],
                "llm_f1": exp2_best_qwen["f1_fraud"],
                "llm_label": format_best_configuration_label(exp2_llm[exp2_llm["variant"] == "all_augmented"]),
            },
            {
                "experiment": "Эксперимент 3\n(внешний бенчмарк)",
                "baseline_f1": exp3_base["f1_fraud"],
                "llm_f1": exp3_best_qwen["f1_fraud"],
                "llm_label": format_best_configuration_label(exp3[exp3["group"] == "qwen"]),
            },
        ]
    )
    experiment_order = [
        "Эксперимент 1\n(базовый набор)",
        "Эксперимент 2\n(аугментации)",
        "Эксперимент 3\n(внешний бенчмарк)",
    ]
    y_positions = list(range(len(experiment_order)))[::-1]
    position_map = dict(zip(experiment_order, y_positions))

    plt.figure(figsize=(11.3, 5.8))
    ax = plt.gca()
    ax.set_facecolor("#fbfbfc")

    for experiment in experiment_order:
        row = plot_df[plot_df["experiment"] == experiment].iloc[0]
        baseline_value = row["baseline_f1"]
        qwen_value = row["llm_f1"]
        llm_label = row["llm_label"]
        y = position_map[experiment]
        midpoint = (baseline_value + qwen_value) / 2

        ax.hlines(y, xmin=baseline_value, xmax=qwen_value, color="#b8c0cc", linewidth=3.0, zorder=1)
        ax.scatter(baseline_value, y, color="#d05a5a", s=220, edgecolors="white", linewidth=1.4, zorder=3)
        ax.scatter(qwen_value, y, color="#4f78b7", s=260, marker="s", edgecolors="white", linewidth=1.4, zorder=3)

        delta = qwen_value - baseline_value
        ax.text(
            baseline_value - 0.03,
            y,
            f"Правила\n{baseline_value:.3f}",
            ha="right",
            va="center",
            fontsize=10,
            color="#8a4343",
        )
        ax.text(
            qwen_value + 0.025,
            y,
            f"{llm_label}\n{qwen_value:.3f}",
            ha="left",
            va="center",
            fontsize=10,
            color="#355b95",
        )
        ax.text(
            midpoint,
            y + 0.18,
            f"+{delta:.3f}",
            ha="center",
            va="center",
            fontsize=10,
            color="#333333",
            bbox={
                "boxstyle": "round,pad=0.28,rounding_size=0.18",
                "fc": "#eef2f7",
                "ec": "none",
            },
        )

    ax.set_title("Лучшая LLM-конфигурация против правил", pad=14)
    ax.set_xlabel("F1 по классу fraud")
    ax.set_ylabel("")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(experiment_order)
    ax.set_xlim(0, 1.12)
    ax.set_ylim(-0.15, max(y_positions) + 0.15)
    ax.grid(axis="x", color="#d7dbe2", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d7dbe2")
    ax.tick_params(axis="y", length=0, pad=16)
    save_figure(path)


def write_chart_index(path: Path) -> None:
    lines = [
        "# Графики для отчета",
        "",
        "- `exp1_f1_comparison.png`: сравнение F1 по классу fraud для эксперимента 1 (базовый набор).",
        "- `exp1_recall_comparison.png`: сравнение полноты по классу fraud для эксперимента 1 (базовый набор).",
        "- `exp2_f1_heatmap.png`: тепловая карта F1 по вариантам аугментаций в эксперименте 2.",
        "- `exp2_robustness_lines.png`: график устойчивости к аугментациям в эксперименте 2.",
        "- `exp3_f1_comparison.png`: сравнение F1 по классу fraud для эксперимента 3 (внешний бенчмарк).",
        "- `exp3_recall_comparison.png`: сравнение полноты по классу fraud для эксперимента 3 (внешний бенчмарк).",
        "- `overall_f1_heatmap.png`: сводная тепловая карта по всем экспериментам.",
        "- `overall_best_models.png`: сравнение правил и лучшего Qwen по всем экспериментам.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    setup_theme()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exp1 = load_experiment_01_metrics()
    exp2_baseline, exp2_llm = load_experiment_02_metrics()
    exp3 = load_experiment_03_metrics()

    plot_horizontal_metric(
        exp1[["display_name", "f1_fraud"]].copy(),
        metric="f1_fraud",
        title="Эксперимент 1: F1 по моделям и архитектурам\n(базовый набор)",
        path=OUTPUT_DIR / "exp1_f1_comparison.png",
    )
    plot_horizontal_metric(
        exp1[["display_name", "recall_fraud"]].copy(),
        metric="recall_fraud",
        title="Эксперимент 1: полнота по моделям и архитектурам\n(базовый набор)",
        path=OUTPUT_DIR / "exp1_recall_comparison.png",
    )
    plot_exp2_heatmap(exp2_baseline, exp2_llm, OUTPUT_DIR / "exp2_f1_heatmap.png")
    plot_exp2_robustness_lines(exp2_baseline, exp2_llm, OUTPUT_DIR / "exp2_robustness_lines.png")
    plot_horizontal_metric(
        exp3[["display_name", "f1_fraud"]].copy(),
        metric="f1_fraud",
        title="Эксперимент 3: F1 по моделям и архитектурам\n(внешний бенчмарк)",
        path=OUTPUT_DIR / "exp3_f1_comparison.png",
    )
    plot_horizontal_metric(
        exp3[["display_name", "recall_fraud"]].copy(),
        metric="recall_fraud",
        title="Эксперимент 3: полнота по моделям и архитектурам\n(внешний бенчмарк)",
        path=OUTPUT_DIR / "exp3_recall_comparison.png",
    )
    plot_overall_heatmap(exp1, exp2_baseline, exp2_llm, exp3, OUTPUT_DIR / "overall_f1_heatmap.png")
    plot_best_models_overview(exp1, exp2_baseline, exp2_llm, exp3, OUTPUT_DIR / "overall_best_models.png")
    write_chart_index(OUTPUT_DIR / "chart_index.md")
    print(f"Wrote report charts to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
