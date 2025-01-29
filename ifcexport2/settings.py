import os
from pathlib import Path
VOLUME_PATH=Path(os.getenv("VOLUME_PATH", "./vol")).absolute()
if not VOLUME_PATH.exists():
    raise OSError(f"VOLUME_PATH ({VOLUME_PATH}) is not exists!")

UPLOADS_PATH=Path(os.getenv("UPLOADS_PATH", VOLUME_PATH/"uploads")).absolute()
BLOBS_PATH=Path(os.getenv("BLOBS_PATH", VOLUME_PATH/"blobs")).absolute()
if not UPLOADS_PATH.exists():
    UPLOADS_PATH.mkdir(parents=True,exist_ok=False)
if not BLOBS_PATH.exists():
    BLOBS_PATH.mkdir(parents=True,exist_ok=False)
