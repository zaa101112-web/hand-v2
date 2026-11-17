from pathlib import Path
from datetime import datetime
import os
import tempfile
from PIL import Image


def atomic_png(image, folder, stamp=None):
    """Publish a verified PNG without replacing any existing path."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    stamp=stamp or datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    fd,temp=tempfile.mkstemp(prefix='.hand-capture-',suffix='.tmp',dir=folder)
    os.close(fd)
    try:
        image.save(temp,format='PNG')
        with Image.open(temp) as check:
            check.load()
            if check.format!='PNG' or check.size!=image.size:raise ValueError('PNG verification failed')
        with open(temp,'r+b') as stream:stream.flush();os.fsync(stream.fileno())
        for serial in range(100000):
            destination=folder/f'capture_{stamp}_{serial:04d}.png'
            try:
                # Windows rename is no-clobber; POSIX rename would overwrite.
                if os.name == 'nt':os.rename(temp,destination)
                else:os.link(temp,destination)
                return destination
            except FileExistsError:continue
        raise OSError('capture filename space exhausted')
    finally:
        Path(temp).unlink(missing_ok=True)
