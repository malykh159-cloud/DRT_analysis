from dataclasses import dataclass, field


@dataclass
class History:
    variants: list = field(default_factory=list)
    position: int = -1

    @property
    def current(self):
        return self.variants[self.position] if self.position >= 0 else None

    def push(self, variant):
        # A fresh branch drops only redo references, never original measurements.
        self.variants[self.position+1:] = [variant]
        self.position = len(self.variants)-1

    def undo(self):
        if self.position > 0:
            self.position -= 1
        return self.current

    def redo(self):
        if self.position < len(self.variants)-1:
            self.position += 1
        return self.current

    def select(self, position):
        if not 0 <= position < len(self.variants):
            raise IndexError("Invalid history position.")
        self.position = position
        return self.current
