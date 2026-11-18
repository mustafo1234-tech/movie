import json
from pathlib import Path


class Translator:
    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        self.catalogs: dict[str, dict[str, str]] = {}
        self.reload()

    def reload(self) -> None:
        self.catalogs.clear()
        for path in self.folder.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            self.catalogs[path.stem] = {str(key): str(value) for key, value in data.items()}

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(sorted(self.catalogs))

    def t(self, language: str, key: str, **kwargs: object) -> str:
        catalog = self.catalogs.get(language) or self.catalogs.get("uz") or {}
        text = catalog.get(key, self.catalogs.get("uz", {}).get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text


_folder = Path(__file__).resolve().parent.parent / "translations"
translator = Translator(_folder)


def t(language: str, key: str, **kwargs: object) -> str:
    return translator.t(language, key, **kwargs)


def __(language: str, key: str, **kwargs: object) -> str:
    return t(language, key, **kwargs)


def labels(*keys: str) -> set[str]:
    return {t(language, key) for language in translator.languages for key in keys}
