from dataclasses import dataclass, field


@dataclass
class ScrapeResult:
    text: str
    meta: dict[str, str] = field(default_factory=dict)
    url: str = ""
