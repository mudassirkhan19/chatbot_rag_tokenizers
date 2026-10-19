"""Which Editions are one Work, as far as `eval-check` needs to know (ADR 0041).

An Edition's Work is the manifest's work_id, which `collect`'s Work grouping fills for every included Edition.
Where it is blank, Editions are taken as one Work when the manifest links them by an identifier: an arXiv preprint
records its DOI and ACL Anthology id, so its venue Edition joins it. Editions that share no identifier stay apart,
so that fallback can miss a duplicate; it never joins two Works.
"""

from collections.abc import Iterable, Mapping

from ..collection.works import identifiers


class Works:
    def __init__(self, manifest: Iterable[Mapping[str, str]]) -> None:
        self._parent: dict[str, str] = {}
        for row in manifest:
            names = [f"edition:{row['edition_id']}"]
            names += [f"work:{row['work_id']}"] if row["work_id"] else sorted(identifiers(row))
            for name in names[1:]:
                self._join(names[0], name)

    def of(self, edition_id: str) -> str:
        """The Work an Edition belongs to, named by its work_id or one of its identifiers."""
        return self._root(f"edition:{edition_id}")

    def _root(self, name: str) -> str:
        while (parent := self._parent.get(name, name)) != name:
            self._parent[name] = self._parent.get(parent, parent)
            name = parent
        return name

    def _join(self, first: str, second: str) -> None:
        self._parent[self._root(first)] = self._root(second)
