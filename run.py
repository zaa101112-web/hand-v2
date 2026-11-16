from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from hand_v2.__main__ import main

if __name__=="__main__":
    from multiprocessing import freeze_support
    freeze_support()
    raise SystemExit(main())
