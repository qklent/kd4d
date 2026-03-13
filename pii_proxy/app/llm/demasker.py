from __future__ import annotations

import re


class StreamingDemasker:
    PLACEHOLDER_RE = re.compile(r"\[([A-Z_]+_\d+)\]")
    PARTIAL_OPEN = re.compile(r"\[[A-Z_0-9]*$")
    MAX_BUFFER = 50

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping
        self.buffer = ""

    def feed(self, chunk: str) -> str:
        self.buffer += chunk
        return self._flush()

    def finalize(self) -> str:
        result = self.buffer
        self.buffer = ""
        return result

    def _flush(self) -> str:
        self.buffer = self.PLACEHOLDER_RE.sub(self._replace, self.buffer)

        match = self.PARTIAL_OPEN.search(self.buffer)
        if match:
            safe = self.buffer[: match.start()]
            self.buffer = self.buffer[match.start() :]

            if len(self.buffer) > self.MAX_BUFFER:
                safe += self.buffer
                self.buffer = ""

            return safe

        result = self.buffer
        self.buffer = ""
        return result

    def _replace(self, match: re.Match) -> str:
        placeholder = match.group(0)
        return self.mapping.get(placeholder, placeholder)


def demask_text(text: str, mapping: dict[str, str]) -> str:
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text
