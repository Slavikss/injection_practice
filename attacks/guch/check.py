"""Прогоны четырёх комбинаций и сохранение доказательств."""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = {
    "basic": ("attack.md", "", "AB"),
    "prompt": ("attack_prompt.md", "spotlighting,repeat_task", "AB"),
    "action": ("attack_action.md", "sanitizer,action_check", "AC"),
    "star": ("attack_star.md", "detector,action_check,dual_llm", "ABC"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["all", *CASES], default="all")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs должен быть положительным")
    names = list(CASES) if args.case == "all" else [args.case]
    for name in names:
        path = HERE / CASES[name][0]
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            parser.error(f"нужен непустой файл {path.relative_to(ROOT)}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for name in names:
        filename, defenses, goals = CASES[name]
        attack = (HERE / filename).relative_to(ROOT)
        label = f"guch_{name}_{stamp}"
        command = [sys.executable, "-u", "run.py", "--attack", str(attack),
                   "--defense", defenses, "--goal", ",".join(goals),
                   "--runs", str(args.runs), "--name", label]
        subprocess.run(command, cwd=ROOT, check=True)
        folder = ROOT / "runs" / f"{attack.stem}__{label}"
        records = [folder / f"run_{i}" / "trace.json" for i in range(1, args.runs + 1)]
        outcomes = [json.loads(p.read_text(encoding="utf-8")) for p in records]
        hits = [p for p, record in zip(records, outcomes)
                if all(record["outcome"][g] for g in goals)]
        evidence = (hits[0] if hits else records[0]).with_suffix(".md")
        destination = HERE / f"trace_{name}_{stamp}.md"
        shutil.copyfile(evidence, destination)
        result = HERE / f"result_{name}.md"
        result.write_text(
            f"# {'+'.join(goals)}: {defenses or 'без защит'}\n\n"
            f"Комбо: {len(hits)}/{args.runs}. Модель: "
            f"{outcomes[0]['model']}.\n\n"
            f"[{'Успешный прогон' if hits else 'Неуспешный прогон'}]({destination.name}).\n\n"
            f"Все прогоны: `{folder.relative_to(ROOT)}`.\n",
            encoding="utf-8",
        )
        print(f"{name}: {len(hits)}/{args.runs}; {result.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
