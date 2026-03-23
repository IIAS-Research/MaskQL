import os, sys, importlib, pkgutil, json, traceback
from pathlib import Path
from pseudocare import PseudoCare

try:
    # PIPE variable must be loaded
    _ERR = None

    print('[py] sys.executable =', sys.executable)
    print('[py] sys.path[0]   =', sys.path[0])
    print('[py] PIPELINE_DIR   =', PIPE)
    print('[py] exists?        =', os.path.isdir(PIPE))
    print('[py] listdir        =', os.listdir(PIPE) if os.path.isdir(PIPE) else 'N/A')

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    REPO = Path(os.environ.get("EDS_REPO", "/opt/models/eds-pseudo-public/"))
    PKG  = os.environ.get("EDS_PKG", "eds_pseudo")

    # Import EDSNLP manually
    sys.path.insert(0, str(REPO))
    pkg = importlib.import_module(PKG)
    for _, name, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        try: importlib.import_module(name)
        except Exception: pass

    model_dir = REPO/"artifacts"

    import edsnlp

    nlp_model = PseudoCare(model=edsnlp.load(str(model_dir), auto_update=False))

    def _process_text(text, seed):
        return nlp_model.run(text, seed)
    
except Exception:
    _ERR = traceback.format_exc()
