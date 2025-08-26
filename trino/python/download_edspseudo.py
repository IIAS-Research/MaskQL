import argparse
import os
from pathlib import Path
from huggingface_hub import snapshot_download

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo_id", default="AP-HP/eds-pseudo-public")
    p.add_argument("--out_dir", default="/models/eds-pseudo-public")
    p.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    args = p.parse_args()

    if not args.token:
        raise SystemExit("ERROR : HF_TOKEN missing.")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    local_path = snapshot_download(
        repo_id=args.repo_id,
        local_dir=str(out),
        local_dir_use_symlinks=False,
        token=args.token,
    )
    print("EDSNLP downloaded !")

if __name__ == "__main__":
    main()
