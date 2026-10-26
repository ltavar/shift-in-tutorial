"""In-memory storage. Not persistent — fine for a workshop starter."""

from dataclasses import dataclass, field


class LinkNotFound(KeyError):
    """No link exists for the requested code."""


@dataclass
class LinkRecord:
    code: str
    url: str
    clicks: int = 0


@dataclass
class Store:
    _links: dict = field(default_factory=dict)

    def put(self, record: LinkRecord) -> None:
        self._links[record.code] = record

    def get(self, code: str) -> LinkRecord:
        try:
            return self._links[code]
        except KeyError:
            raise LinkNotFound(code) from None

    def exists(self, code: str) -> bool:
        return code in self._links

    def all(self) -> list:
        return list(self._links.values())


store = Store()
