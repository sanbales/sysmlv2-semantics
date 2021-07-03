import json

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Union


class Naming(Enum):
    """An enumeration for how to repr SysML elements"""

    identifier = "IDENTIFIER"
    long = "LONG"
    qualified = "QUALIFIED"
    short = "SHORT"

    def get_name(self, data: dict) -> str:
        naming = self._value_

        if naming == Naming.qualified:
            return f"""<{data["qualifiedName"]}>"""

        if naming == Naming.identifier:
            return f"""<{data["@id"]}>"""

        name = data.get("name") or data["@id"]
        if naming == Naming.short:
            return f"<{name}>"
        else:
            return f"""<{name} «{data["@type"]}»>"""


@dataclass(repr=False)
class Model:
    """A SysML v2 Model"""

    elements: dict
    naming: Naming = Naming.long
    source: str = ""

    @staticmethod
    def load_from_file(filepath: Union[Path, str]) -> "Model":
        if isinstance(filepath, str):
            filepath = Path(filepath)
        return Model(
            elements={
                element["@id"]: element
                for element in json.loads(filepath.read_text())
            },
            source=str(filepath.resolve()),
        )

    @staticmethod
    def load_from_api() -> "Model":
        raise NotImplementedError("""Need to implement this""")

    def __post_init__(self):
        self.elements = {
            id_: Element(data=data, model=self)
            for id_, data in self.elements.items()
        }
        for element in self.elements.values():
            if not element.is_relationship:
                continue
            metatype = element.metatype
            source, target = element.source, element.target
            assert len(source) == 1 and len(target) == 1
            source, target = source[0], target[0]
            through = f"through{metatype}"
            reverse = f"reverse{metatype}"
            if through not in source.data:
                source.data[through] = []
            if reverse not in target.data:
                target.data[reverse] = []

            source.data[through] += [{"@id": target._id}]
            target.data[reverse] += [{"@id": source._id}]

    def __repr__(self) -> str:
        data = self.source or f"len(self.elements) elements"
        return f"<SysML v2 Model ({data})>"


@dataclass(repr=False)
class Element:
    """A SysML v2 Element"""

    data: dict
    model: Model
    is_relationship: bool = False

    def __post_init__(self):
        self.is_relationship = "relatedElement" in self.data

    @property
    def metatype(self):
        return self.data["@type"]

    def __dir__(self):
        return sorted(
            list(self.data.keys()) +
            list(super().__dir__())
        )

    def __getattr__(self, key):
        if key.startswith("_") and f"@{key[1:]}" in self.data:
            key = f"@{key[1:]}"
        if key in self.data:
            return self[key]
        return self.__getattribute__(self, key)

    @lru_cache
    def __getitem__(self, key):
        item = self.data[key]

        if isinstance(item, dict) and "@id" in item:
            return self.model.elements[item["@id"]]

        if isinstance(item, (list, tuple, set)) and all("@id" in _ for _ in item):
            return type(item)([
                    self.model.elements[subitem["@id"]]
                    for subitem in item
                ])

        return item

    def __hash__(self):
        return hash(id(self))

    def __repr__(self):
        return self.model.naming.get_name(self.data)