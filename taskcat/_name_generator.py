from pathlib import Path
from random import choice

from taskcat.exceptions import TaskCatException


def generate_name():
    path: Path = (Path(__file__).parent / "./cfg/").resolve()
    if not (path / "animals.txt").is_file() or not (path / "descriptors.txt").is_file():
        raise TaskCatException("cannot find dictionary files")
    with open(str(path / "animals.txt"), "r", encoding="utf-8") as _f:
        animals = _f.read().split("\n")
    with open(str(path / "descriptors.txt"), "r", encoding="utf-8") as _f:
        descriptors = _f.read().split("\n")
    return choice(descriptors) + "-" + choice(animals)  # nosec: B311
