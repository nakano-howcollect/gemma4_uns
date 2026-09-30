#!/usr/bin/env python3
"""llama.cpp のローカルサーバーと会話する標準ライブラリのみのクライアント。"""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelOutputError(RuntimeError):
    """モデルが予約トークンを繰り返した場合の異常。"""


def chat_completion(messages, *, base_url="http://127.0.0.1:8080/v1",
                    temperature=1.0, max_tokens=2048):
    """system/user/assistant メッセージを送り、回答を逐次表示して返す。"""
    payload = {
        "model": "gemma4", "messages": messages, "stream": True,
        "temperature": temperature, "top_p": 0.95, "top_k": 64,
        "min_p": 0.0, "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    chunks = []
    recent_output = ""
    finished = False
    with urlopen(request, timeout=600) as response:
        for raw in response:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                finished = True
                break
            event = json.loads(data)
            if "error" in event:
                raise RuntimeError(str(event["error"]))
            for choice in event.get("choices", []):
                content = choice.get("delta", {}).get("content") or ""
                recent_output = (recent_output + content)[-512:]
                if re.search(r"(<unused\d+>)(?:\1){7}", recent_output):
                    raise ModelOutputError(
                        "予約トークンの異常な連続出力を検出したため中断しました。"
                        "今回の入力・回答は履歴に追加していません。\n"
                        "サーバーを停止し、bash start_server.sh でモデルを検証して再起動してください。"
                    )
                print(content, end="", flush=True)
                chunks.append(content)
                if choice.get("finish_reason") == "length":
                    print("\n[生成上限に達しました。必要なら --max-tokens を増やしてください]",
                          file=sys.stderr)
    if not finished:
        raise RuntimeError("応答が途中で切断されました。今回の入力は履歴に追加していません。")
    print()
    return "".join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    system = parser.add_mutually_exclusive_group()
    system.add_argument("--system", help="system prompt を直接指定")
    system.add_argument("--system-file", type=Path,
                        default=Path(__file__).with_name("system2.txt"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--prompt", help="1回だけ質問して終了")
    args = parser.parse_args()
    if args.max_tokens < 1 or args.temperature < 0:
        parser.error("max-tokens は正の整数、temperature は0以上にしてください")
    try:
        prompt = args.system if args.system is not None else args.system_file.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(str(exc))
    messages = [{"role": "system", "content": prompt}]
    if args.prompt is None:
        print("Gemma 4 チャット | /exit: 終了 | /reset: 会話履歴をクリア")
    while True:
        try:
            user_text = args.prompt if args.prompt is not None else input("\nあなた> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if args.prompt is None:
            if user_text.strip() == "/exit":
                return 0
            if user_text.strip() == "/reset":
                messages = messages[:1]
                print("会話履歴をクリアしました。system prompt は保持しています。")
                continue
            if not user_text.strip():
                continue
        pending = messages + [{"role": "user", "content": user_text}]
        try:
            print("Gemma> ", end="", flush=True)
            answer = chat_completion(pending, base_url=args.base_url,
                                     temperature=args.temperature, max_tokens=args.max_tokens)
        except HTTPError as exc:
            print(f"\nHTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
            print("会話が長すぎる場合は /reset を実行してください。", file=sys.stderr)
            if args.prompt is not None:
                return 1
            continue
        except ModelOutputError as exc:
            print(f"\nモデル出力エラー: {exc}", file=sys.stderr)
            return 1
        except (URLError, OSError, ValueError, RuntimeError) as exc:
            print(f"\n通信エラー: {exc}\n先に bash start_server.sh を起動してください。", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n中断しました。")
            return 130
        messages = pending + [{"role": "assistant", "content": answer}]
        if args.prompt is not None:
            return 0


if __name__ == "__main__":
    sys.exit(main())
