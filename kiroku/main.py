from __future__ import annotations

import argparse
import glob
import io
import os
import pathlib
from datetime import date as dtdate
from typing import Optional

import yaml

categories = {
    "added": "Added",
    "changed": "Changed",
    "deprecated": "Deprecated",
    "removed": "Removed",
    "fixed": "Fixed",
    "security": "Security",
}


class Release:
    def __init__(
        self, version: Optional[str], date: Optional[date] = None, is_released=True
    ):
        self._version = version
        self._date = date
        self._is_released = is_released
        if not is_released:
            self._date = dtdate(9999, 1, 1)
        self._categories: dict[str, list[str]] = {}
        for k in categories.keys():
            self._categories[k] = []

    def add_entry(self, category_str: str, body: str) -> None:
        if category_str not in self._categories:
            raise ValueError(f"Unknown category: {category_str}.")
        self._categories[category_str].append(body)

    @property
    def version(self) -> Optional[str]:
        return self._version

    @property
    def date(self) -> Optional[date]:
        return self._date

    @property
    def categories(self) -> dict[str, list[str]]:
        return self._categories

    @property
    def is_released(self) -> bool:
        return self._is_released

    @property
    def item_count(self):
        return sum(len(l) for l in self._categories.values())


RST_RELEASE_SEP = "-" * 27
RST_CATEGORY_SEP = "^" * 27


def to_rst(rel: Release) -> None:
    ss = []
    if not rel.is_released:
        ss += ["Unreleased"]
        ss += [RST_RELEASE_SEP]
    else:
        ss += [f"{rel.version} ({rel.date.strftime('%Y-%m-%d')})"]
        ss += [RST_RELEASE_SEP]
    for c, header in categories.items():
        if len(rel.categories[c]) > 0:
            ss += [f"{header}"]
            ss += [RST_CATEGORY_SEP]
            for body in rel.categories[c]:
                ss += [f"* {body}"]
            ss += [""]
    ss += [""]
    return "\n".join(ss)


def read_text(dirpath, filename) -> str:
    p = pathlib.Path(dirpath).resolve()
    filename = os.path.join(str(p), filename)
    if not os.path.isfile(filename):
        return ""
    with open(filename) as fp:
        return fp.read()


def read_releaselog_dir(dirpath) -> list[Release]:
    p = pathlib.Path(dirpath).resolve()
    release_dirs = filter(os.path.isdir, glob.glob(os.path.join(str(p), "*")))
    releases = []
    for d in release_dirs:
        try:
            is_released = True
            year, month, day, version_str = os.path.basename(d).split("-")
            date = dtdate(int(year), int(month), int(day))
        except ValueError:
            version_str = os.path.basename(d)
            date = None
            is_released = False
        rel = Release(version=version_str, date=date, is_released=is_released)
        for entry_yaml in glob.glob(os.path.join(str(p), d, "*")):
            with open(entry_yaml) as fp:
                entry = yaml.safe_load(fp)
                rel.add_entry(entry["category"], entry["body"])
        releases += [rel]
    return releases


def write_changelog(
    releases: list[Release], header: str, footer: str, text_io, hide_unreleased
):
    text_io.write(header)
    releases.sort(key=lambda x: x.date, reverse=True)
    for rel in releases:
        if hide_unreleased and not rel.is_released:
            continue
        if rel.item_count > 0:
            text_io.write(to_rst(rel))
    text_io.write(footer)


def main():
    parser = argparse.ArgumentParser(description="Generate changelog file")
    parser.add_argument("--hide-unreleased", action="store_true")
    parser.add_argument("input_dir")
    args = parser.parse_args()

    releases = read_releaselog_dir(args.input_dir)
    header = read_text(args.input_dir, "header")
    footer = read_text(args.input_dir, "footer")
    sio = io.StringIO()
    write_changelog(releases, header, footer, sio, args.hide_unreleased)
    print(sio.getvalue())


if __name__ == "__main__":
    main()
