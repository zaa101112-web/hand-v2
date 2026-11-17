from dataclasses import dataclass
from pathlib import Path
import re
from PIL import Image, ImageOps
from hand_v2.domain.images import ImageAsset


@dataclass(frozen=True)
class ImageLoadResult:
    assets: tuple
    excluded: tuple


def load_images(paths):
    found={};excluded=[]
    for raw in paths:
        p=Path(raw)
        try:
            candidates=list(p.iterdir()) if p.is_dir() else [p]
            for candidate in candidates:
                if candidate.is_file() and candidate.suffix.casefold() in ('.png','.jpg','.jpeg'):
                    resolved=str(candidate.resolve())
                    found[resolved.casefold()]=resolved
        except OSError as exc:excluded.append(f'{p.name}: {type(exc).__name__}')
    def natural(p):
        return tuple((1,int(x)) if x.isdigit() else (0,x.casefold()) for x in re.split(r'(\d+)',p))
    assets=[]
    for name in sorted(found.values(),key=natural):
        try:
            with Image.open(name) as image:
                image=ImageOps.exif_transpose(image).convert('RGBA')
                image.load()
                assets.append(ImageAsset(name,image.width,image.height,image.tobytes()))
        except (OSError,ValueError,Image.DecompressionBombError) as exc:
            excluded.append(f'{Path(name).name}: {type(exc).__name__}')
    return ImageLoadResult(tuple(assets),tuple(excluded))
