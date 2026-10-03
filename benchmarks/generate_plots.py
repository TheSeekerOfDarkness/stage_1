#!/usr/bin/env python3
"""Generate publication-ready comparison plots from benchmark results.json."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_JSON = BASE_DIR / "benchmarks" / "results.json"
FIGURES_DIR = BASE_DIR / "reports" / "figures"


def setup_style():
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "bold",
        "figure.titlesize": 14,
        "figure.titleweight": "bold",
        "figure.dpi": 300,
    })


def plot_datalake_write_speed(data):
    layouts = [d["layout"].replace("_", " ").title() for d in data]
    x = np.arange(len(layouts))
    width = 0.25

    py_means = [d["python"]["mean_ms"] for d in data]
    py_stds = [d["python"]["stddev_ms"] for d in data]

    java_means = [d["java"]["mean_ms"] for d in data]
    java_stds = [d["java"]["stddev_ms"] for d in data]

    rust_means = [d["rust"]["mean_ms"] for d in data]
    rust_stds = [d["rust"]["stddev_ms"] for d in data]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    rects1 = ax.bar(x - width, py_means, width, yerr=py_stds, label="Python", color="#3572A5", capsize=4, alpha=0.9)
    rects2 = ax.bar(x, java_means, width, yerr=java_stds, label="Java", color="#E76F00", capsize=4, alpha=0.9)
    rects3 = ax.bar(x + width, rust_means, width, yerr=rust_stds, label="Rust", color="#C84B31", capsize=4, alpha=0.9)

    ax.set_ylabel("Execution Time (ms)")
    ax.set_title("Datalake Ingestion Speed Across Layouts (106 Books)")
    ax.set_xticks(x)
    ax.set_xticklabels(layouts)
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Add data labels
    for rects in (rects1, rects2, rects3):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.1f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    out_path = FIGURES_DIR / "datalake_write_speed.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_index_build_speed(data):
    structures = ["Monolithic JSON\n(106 Books)", "Hierarchical Folders\n(Sample Subset)"]
    x = np.arange(len(structures))
    width = 0.25

    py_means = [d["python"]["mean_ms"] for d in data]
    py_stds = [d["python"]["stddev_ms"] for d in data]

    java_means = [d["java"]["mean_ms"] for d in data]
    java_stds = [d["java"]["stddev_ms"] for d in data]

    rust_means = [d["rust"]["mean_ms"] for d in data]
    rust_stds = [d["rust"]["stddev_ms"] for d in data]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    rects1 = ax.bar(x - width, py_means, width, yerr=py_stds, label="Python", color="#3572A5", capsize=4, alpha=0.9)
    rects2 = ax.bar(x, java_means, width, yerr=java_stds, label="Java", color="#E76F00", capsize=4, alpha=0.9)
    rects3 = ax.bar(x + width, rust_means, width, yerr=rust_stds, label="Rust", color="#C84B31", capsize=4, alpha=0.9)

    ax.set_ylabel("Execution Time (ms, Log Scale)")
    ax.set_yscale("log")
    ax.set_title("Inverted Index Construction Latency: Monolithic vs Hierarchical")
    ax.set_xticks(x)
    ax.set_xticklabels(structures)
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for rects in (rects1, rects2, rects3):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.0f} ms",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    out_path = FIGURES_DIR / "inverted_index_build_speed.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_query_latency(data):
    labels = []
    for d in data:
        labels.append(f"{d['structure'].split('_')[0]}\n'{d['term']}'")
    x = np.arange(len(labels))
    width = 0.25

    py_means = [d["python"]["mean_us"] for d in data]
    py_stds = [d["python"]["stddev_us"] for d in data]

    java_means = [d["java"]["mean_us"] for d in data]
    java_stds = [d["java"]["stddev_us"] for d in data]

    rust_means = [d["rust"]["mean_us"] for d in data]
    rust_stds = [d["rust"]["stddev_us"] for d in data]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    rects1 = ax.bar(x - width, py_means, width, yerr=py_stds, label="Python", color="#3572A5", capsize=4, alpha=0.9)
    rects2 = ax.bar(x, java_means, width, yerr=java_stds, label="Java", color="#E76F00", capsize=4, alpha=0.9)
    rects3 = ax.bar(x + width, rust_means, width, yerr=rust_stds, label="Rust", color="#C84B31", capsize=4, alpha=0.9)

    ax.set_ylabel("Lookup Latency (µs, Log Scale)")
    ax.set_yscale("log")
    ax.set_title("Query Lookup Latency Across Languages (without process startup)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for rects in (rects1, rects2, rects3):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.1f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_path = FIGURES_DIR / "query_latency.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved: {out_path}")


def main():
    if not RESULTS_JSON.exists():
        print(f"Error: {RESULTS_JSON} not found. Run run_benchmarks.py first.")
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    setup_style()

    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        results = json.load(f)

    if "datalake_benchmarks" in results:
        plot_datalake_write_speed(results["datalake_benchmarks"])

    if "inverted_index_benchmarks" in results:
        plot_index_build_speed(results["inverted_index_benchmarks"])

    if "query_benchmarks" in results:
        plot_query_latency(results["query_benchmarks"])

    print("All plots successfully generated!")


if __name__ == "__main__":
    main()
