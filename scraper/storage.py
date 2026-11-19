import os
from pathlib import Path
import tempfile


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as file:
            name = file.name
            file.write(content)
            file.flush()
            os.fchmod(file.fileno(), 0o644)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
