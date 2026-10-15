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

    def remove(self, positions):
        """Remove only in-memory snapshots; retain current or nearest predecessor."""
        removed = set(positions)
        if any(i < 0 or i >= len(self.variants) for i in removed):
            raise IndexError("Invalid history position.")
        if not removed:
            return self.current
        old_position = self.position
        survivors = [(i, variant) for i, variant in enumerate(self.variants) if i not in removed]
        self.variants = [variant for _, variant in survivors]
        if not survivors:
            self.position = -1
        elif old_position not in removed:
            self.position = next(i for i, (old, _) in enumerate(survivors) if old == old_position)
        else:
            predecessors = [i for i, (old, _) in enumerate(survivors) if old < old_position]
            self.position = predecessors[-1] if predecessors else 0
        return self.current
