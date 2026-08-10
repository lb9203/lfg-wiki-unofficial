#!/usr/bin/env python3
"""Edit zensical.toml nav by title path, using tomlkit.

Usage: poetry run python scripts/nav.py <cmd> [args...]

Commands:
  show [path...]        print the nav tree (titles + paths) under a path
  move <path...> --to <parent path...> [--before <title>]
                        move a section under another section
  flatten <path...> [--keep-index]
                        promote a section's children into its parent
  rename <path...> --as <new title>
                        change an entry's display title
"""
import sys
from pathlib import Path

import tomlkit

CFG = Path("zensical.toml")


def load():
    doc = tomlkit.parse(CFG.read_text(encoding="utf-8"))
    return doc, doc["project"]["nav"]


def save(doc):
    CFG.write_text(tomlkit.dumps(doc), encoding="utf-8")


def get(nav, path):
    """Return the item at a title path (root list if path empty)."""
    if not path:
        return nav
    item = nav
    for title in path:
        for child in item:
            if isinstance(child, dict) and title in child:
                item = child[title]
                break
        else:
            raise KeyError(f"nav entry not found: {title} (in {path})")
    return item


def entry_of(nav, path):
    """Return (parent_list, index, entry) for the entry at path."""
    if not path:
        raise ValueError("empty path")
    parent = get(nav, path[:-1])
    title = path[-1]
    for i, child in enumerate(parent):
        if isinstance(child, dict) and title in child:
            return parent, i, child
    raise KeyError(f"nav entry not found: {title}")


def flatten(nav, path, keep_index=True):
    """Replace the section at path with its children, spliced at its position.

    With keep_index (default) the section's own index page is kept as the
    first child leaf, with its path rewritten from x/index.md to x.md.
    """
    parent, i, entry = entry_of(nav, path)
    title = path[-1]
    children = entry[title]
    if not isinstance(children, list):
        raise ValueError(f"{path} is not a section")
    flat = list(children)
    if keep_index:
        idx = next((e for e in flat if isinstance(e, dict) and _is_index(e)), None)
        flat = [e for e in flat if not (isinstance(e, dict) and _is_index(e))]
        if idx is not None:
            t, v = next(iter(idx.items()))
            idx[t] = v.rsplit("/", 1)[0] + ".md"  # x/index.md -> x.md
            flat.insert(0, idx)
    parent.pop(i)
    for offset, item in enumerate(flat):
        parent.insert(i + offset, item)
    return parent


def _is_index(item):
    if not isinstance(item, dict):
        return False
    v = next(iter(item.values()))
    return isinstance(v, str) and v.endswith("/index.md")


def show(nav, path):
    root = get(nav, path)

    def rec(items, depth):
        for item in items:
            if not isinstance(item, dict):
                continue
            title, v = next(iter(item.items()))
            if isinstance(v, str):
                print("  " * depth + f"{title}  ->  {v}")
            else:
                print("  " * depth + f"{title}/")
                rec(v, depth + 1)

    rec(root if isinstance(root, list) else [root], 0)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, args = args[0], args[1:]
    doc, nav = load()

    if cmd == "show":
        path = args
        show(nav, path)
        return

    if cmd == "flatten":
        if "--keep-index" in args:
            args.remove("--keep-index")
            keep = True
        else:
            keep = False
        flatten(nav, args)
        save(doc)
        print(f"flattened {args}")
        return

    if cmd == "rename":
        as_i = args.index("--as")
        path, new_title = args[:as_i], args[as_i + 1]
        parent, i, entry = entry_of(nav, path)
        old = next(iter(entry))
        entry[new_title] = entry.pop(old)
        save(doc)
        print(f"renamed {old} -> {new_title}")
        return

    if cmd == "move":
        to_i = args.index("--to")
        path, to = args[:to_i], args[to_i + 1 :]
        parent, i, entry = entry_of(nav, path)
        parent.pop(i)
        target = get(nav, to) if to else nav
        target.append(entry)
        save(doc)
        print(f"moved {path} under {to or 'root'}")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
