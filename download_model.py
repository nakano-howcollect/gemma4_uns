"""競合を防ぎ、SHA-256を確認してからGGUFを使用可能にする。"""
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
REVISION = "45b6a334b4bcd1d7f37179df58b3b1d66a184e5d"
SHA256 = "d0027dd3a9128d9323e9f282c8bf010a8526c46477584535991dc1a869b56e96"
SIZE = 5335285728
URL = ("https://huggingface.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive/resolve/"
       + REVISION + "/" + MODEL.name)


def valid(path):
    if not path.is_file() or path.stat().st_size != SIZE:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == SHA256


def main():
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    with MODEL.with_suffix(".lock").open("a") as lock:
        print("モデルのダウンロードロックを取得しています…", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        print("モデルのサイズとSHA-256を確認しています…", flush=True)
        if valid(MODEL):
            print("モデル検証OK", flush=True)
            return
        partial = MODEL.with_suffix(".gguf.part")
        print("モデルを新規取得します（約5.34 GB）。", flush=True)
        # 不正な既存ファイルへの追記・並列ダウンロードを避ける。
        subprocess.run(["curl", "--fail", "--location", "--retry", "3",
                        "--connect-timeout", "30", "--output", str(partial), URL], check=True)
        if not valid(partial):
            raise RuntimeError("モデルの検証に失敗しました。サーバーは起動しません。再実行してください。")
        os.replace(partial, MODEL)
        print("ダウンロード・SHA-256検証完了", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
