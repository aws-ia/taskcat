#!/usr/bin/env python
import argparse
import logging
import re
import tarfile
from functools import cmp_to_key
from pathlib import Path
from typing import Iterable

from copier import Worker
from plumbum.cmd import git

LOG = logging.getLogger(__name__)


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=".")


class HPWorker(Worker):
    def _sort_patterns(self, patterns: Iterable[str]) -> Iterable[str]:
        def _sort(i1, i2):
            if (("!" in i1) and ("!" in i2)) or (("*" in i1) and ("*" in i2)):
                return 0
            if ("!" in i1) or ("*" in i2):
                return 1
            if ("*" in i1) or ("!" in i2):
                return -1
            return 0

        return sorted(patterns, key=cmp_to_key(_sort))


class Update:
    def _untrack_answers_file(self):
        git(
            "-C",
            self.destination,
            "update-index",
            "--assume-unchanged",
            self.temp_answers_file,
        )

    def _track_answers_file(self):
        git(
            "-C",
            self.destination,
            "update-index",
            "--no-assume-unchanged",
            self.temp_answers_file,
        )

    def _modify_git_exclude(self):
        with open(self.local_git_exclude, "r") as f:
            self._local_git_exclude = f.read()
        with open(self.local_git_exclude, "a") as f:
            f.write("\n" + self.temp_answers_file)
        return

    def _restore_git_exclude(self):
        with open(self.local_git_exclude, "w") as f:
            f.write(self._local_git_exclude)
        return

    def _write_modified_answers_file(self):
        with open(
            str(self.destination) + "/" + self._w.template.config_data["answers_file"]
        ) as f:
            ansdata = f.read()

        modified_answer_data = re.sub(
            "_src_path:.*\n", f"_src_path: {self.source}\n", ansdata
        )
        with open(str(self.destination) + "/" + self.temp_answers_file, "w") as f:
            f.write(modified_answer_data)
        return

    @property
    def _curated_excludes(self, fo=True):
        _config = self._w.template.config_data
        excludes = _config.get("exclude", ())
        if fo:
            fo = _config.get("force_overwrite", ())
            return tuple(excludes) + tuple(fo)
        return tuple(excludes)

    @property
    def local_git_exclude(self):
        return Path(str(self.destination) + "/.git/info/exclude")

    @property
    def source(self):
        return Path(self._source)

    @property
    def destination(self):
        return Path(self._destination)

    def __init__(self, source: str = "", dest: str = ""):
        """
        :param source: Source directory
        :param dest: Destination directory
        """
        self._source = source
        self._destination = dest
        self._original_commit = git("-C", dest, "rev-parse", "HEAD").strip()
        self._w = HPWorker(src_path=source)
        self._local_git_exclude = None
        self.temp_answers_file = ".copier-answers.yml"

    def update(self):
        self._untrack_answers_file()
        self._write_modified_answers_file()
        self._w = HPWorker(
            src_path=None,
            dst_path=self.destination,
            answers_file=self.temp_answers_file,
            quiet=False,
            defaults=True,
            overwrite=True,
            exclude=self._curated_excludes,
            skip_if_exists=self._curated_excludes,
        )
        self._w.run_update()
        self._track_answers_file()
        return

        #
        # try:
        #     git('-C', dest, 'add', '.')
        #     git('-C', dest, 'commit', '-m', 'Automatic update from project type')
        # except Exception as e:
        #     print(e)
        #     COMMIT = False
        # if COMMIT:
        #     make_tarfile(optional_archive_file, dest)
        #     git('-C', dest, 'reset', '--hard', original_commit)
        #
        # if force_overwrite:
        #     COMMIT = True
        #
        #     with open(temp_af_full, 'w') as f:
        #         f.write(modified_answer_data)
        #
        #     secondary_excludes = list("*")
        #     for e in force_overwrite:
        #         if '!' in e:
        #             continue
        #         secondary_excludes.append(f"!{e}")
        #
        #     secondary_excludes = list(
        #         w.all_exclusions) + [str(w.answers_relpath)] + secondary_excludes
        #     w = replace(
        #         w,
        #         src_path=None,
        #         overwrite=True,
        #         exclude=set(secondary_excludes),
        #         quiet=True
        #     )
        #     w.run_copy()
        #
        #     os.remove(temp_af_full)
        #     try:
        #         git('-C', dest, 'add', '.')
        #         git('-C', dest, 'commit', '-m',
        #             'Automatic update from project type')
        #     except Exception as e:
        #         print(e)
        #         COMMIT = False
        #
        #     if COMMIT:
        #         make_tarfile(mandatory_archive_file, dest)
        #         git('-C', dest, 'reset', '--hard', original_commit)
        # return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="copier wrapper")
    parser.add_argument("-s", "--source-dir", type=str)
    parser.add_argument("-d", "--dest-dir", type=str)
    args = parser.parse_args()

    s = str(Path(args.source_dir).expanduser().absolute())
    d = str(Path(args.dest_dir).expanduser().absolute())

    u = Update(s, d)
    u.update()
