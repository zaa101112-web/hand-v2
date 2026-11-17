from dataclasses import dataclass


@dataclass(frozen=True)
class ImageAsset:
    key: str
    width: int
    height: int
    rgba: bytes


class Gallery:
    def __init__(self):
        self.assets = ()
        self.index = 0
        self.scales = {}
        self.direction = 0
        self.revision = 0

    @property
    def current(self):
        return self.assets[self.index] if self.assets else None

    @property
    def scale(self):
        return self.scales.get(self.current.key, 1.) if self.current else 1.

    def replace(self, assets):
        if assets:
            self.assets = tuple(assets)
            self.index = 0
            self.scales = {}
            self.direction = 0
            self.revision += 1

    def move(self, delta):
        old = self.index
        self.index = max(0, min(len(self.assets)-1, old+delta))
        self.direction = (self.index > old)-(self.index < old)
        self.revision += 1

    def zoom(self, factor):
        if self.current:
            self.scales[self.current.key] = min(4., max(.25, self.scale*factor))
            self.direction = 0
            self.revision += 1

    def fit(self):
        if self.current:
            self.scales[self.current.key] = 1.
            self.direction = 0
            self.revision += 1
