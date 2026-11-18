from __future__ import annotations

import csv
import sys
from pathlib import Path
from contextlib import nullcontext
from itertools import product

from .template import Template


def generate_csv(template: Template, output: str = '') -> None:
    """
    Generates a CSV file containing all combinations of scenes, shots, and tasks
    from the provided template.

    Args:
        template (Template): A Template object
        output (str, optional): The directory path where the 'shots.csv' file
        will be saved. If not provided, the CSV content will be printed to stdout.

    Returns:
        None

    """
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
        target = open(Path(output, 'shots.csv'), 'w', newline='')
    else:
        target = nullcontext(sys.stdout)

    with target as out:
        writer = csv.DictWriter(out, fieldnames=['scene', 'shot', 'task'])
        writer.writeheader()

        scenes = template.get_scenes()
        shots = template.get_shots()
        tasks = template.get_tasks()

        for scene, shot, task in product(scenes, shots, tasks):
            writer.writerow(dict(scene=scene, shot=shot, task=task))
