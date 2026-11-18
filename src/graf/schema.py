"""Graf şeması (docs/06-neo4j-graf-semasi.md) için Pydantic modelleri ve doğrulama."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

NodeLabel = Literal["Company", "Person", "Event", "Location", "Metric"]

# ilişki türü -> (izinli kaynak etiketleri, izinli hedef etiketleri)
REL_RULES: dict[str, tuple[set[str], set[str]]] = {
    "BOARD_MEMBER_OF": ({"Person"}, {"Company"}),
    "EXECUTIVE_OF": ({"Person"}, {"Company"}),
    "INVESTED_IN": ({"Company"}, {"Company"}),
    "COMPETITOR_OF": ({"Company"}, {"Company"}),
    "PARTNER_OF": ({"Company"}, {"Company"}),
    "SUBSIDIARY_OF": ({"Company"}, {"Company"}),
    "HEADQUARTERED_IN": ({"Company"}, {"Location"}),
    "PARTICIPATED_IN": ({"Person", "Company"}, {"Event"}),
    "OCCURRED_AT": ({"Event"}, {"Location"}),
    "HAS_METRIC": ({"Company"}, {"Metric"}),
}
RelType = Literal[tuple(REL_RULES)]  # type: ignore[valid-type]

_TR = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})
_SUFFIXES = {"as", "ao", "a", "o", "inc", "ltd", "sti"}


def normalize_name(name: str) -> str:
    """Eşleştirme için ad normalleştirme: küçük harf, aksansız, şirket eki/noktalama yok."""
    s = unicodedata.normalize("NFC", name).replace("İ", "i").replace("I", "ı").lower().translate(_TR)
    s = re.sub(r"(?<=\b\w)\.(?=\w\b)", "", s)  # a.ş. -> aş
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = s.split()
    while len(toks) > 1 and toks[-1] in _SUFFIXES:
        toks.pop()
    return " ".join(toks)


class Entity(BaseModel):
    label: NodeLabel
    name: str = Field(min_length=2)
    ticker: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class Relation(BaseModel):
    type: RelType  # type: ignore[valid-type]
    source: str  # Entity.name
    target: str
    evidence: str = Field(min_length=5)
    confidence: float = Field(ge=0.0, le=1.0)
    props: dict[str, str | float | int | None] = Field(default_factory=dict)


class Extraction(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_refs(self) -> "Extraction":
        by_name = {e.name: e.label for e in self.entities}
        for r in self.relations:
            if r.source not in by_name or r.target not in by_name:
                raise ValueError(f"ilişki tanımsız varlığa bağlı: {r.source} -> {r.target}")
            src_ok, tgt_ok = REL_RULES[r.type]
            if by_name[r.source] not in src_ok or by_name[r.target] not in tgt_ok:
                raise ValueError(f"{r.type} için etiketler uyumsuz: {by_name[r.source]} -> {by_name[r.target]}")
        return self
