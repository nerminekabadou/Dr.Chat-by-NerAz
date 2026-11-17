"""Draw the benchmark chart (security/results/attack_llm.png) from attack_llm.json."""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "results", "attack_llm.json"), encoding="utf-8") as f:
        report = json.load(f)
    labels = ["Model refused", "Model wrote\nharmful SQL", "Harm in app\nbefore hardening",
              "Harm in app\nafter hardening"]
    keys = ["refused", "harmful_sql", "harm_before", "harm_after"]
    colors = ["#9aa5b1", "#e8743b", "#c23b3b", "#2e9e5b"]
    fig, axes = plt.subplots(1, len(report), figsize=(5.2 * len(report), 3.8), sharey=True)
    for ax, (model, data) in zip(axes if len(report) > 1 else [axes], report.items()):
        totals = data["summary"]["totals"]
        values = [totals[k] for k in keys]
        bars = ax.bar(labels, values, color=colors)
        ax.bar_label(bars, padding=2, fontsize=9)
        ax.set_title(f"{model} — {data['summary']['attacks']} attack prompts", fontsize=10)
        ax.tick_params(axis="x", labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Attack prompts")
    fig.suptitle("Dr.Chat text-to-SQL attack benchmark", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "results", "attack_llm.png"), dpi=150)


if __name__ == "__main__":
    main()
