import os, sys, importlib, pkgutil, json, traceback
from pathlib import Path

try:
    # PIPE variable must be loaded
    _ERR = None

    print('[py] sys.executable =', sys.executable)
    print('[py] sys.path[0]   =', sys.path[0])
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    # Keep the legacy override while using the same path as the Java bridge.
    REPO = Path(os.environ.get("EDS_REPO") or PIPE)
    PKG  = os.environ.get("EDS_PKG", "eds_pseudo")
    print('[py] PIPELINE_DIR   =', REPO)
    if not (REPO / "artifacts").is_dir():
        raise FileNotFoundError(f"EDS pipeline artifacts not found in {REPO}")

    from pseudocare import PseudoCare

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
