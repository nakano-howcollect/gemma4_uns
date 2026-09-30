# Gemma 4 + llama.cpp + Python

`HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive` の Q4_K_M を
llama.cpp で動かし、Python から system prompt と会話履歴を送ります。
Python は標準ライブラリのみで動作し、APIキーや pip install は不要です。

## 起動

このディレクトリで、ターミナルを2つ使います。

```bash
# ターミナル1: モデルを読み込む（初回は約5.34 GBをダウンロード）
bash start_server.sh
```

サーバーが起動したら、別のターミナルで:

```bash
# ターミナル2
python3.10 chat.py
```

既定の `system2.txt` を編集してから chat.py を起動すると、その内容が
`role: system` として毎回のリクエストに含まれます。
テンプレートは GGUF に含まれるものを `--jinja` で適用します。

同梱promptは `system_prompt.txt`（汎用の日本語アシスタント）、
`system1.txt`・`system2.txt`（SDXL向けプロンプト作成）です。
`--system-file` で切り替えられます。

```bash
python3.10 chat.py --system 'あなたはPythonの先生です。日本語で簡潔に説明してください。'
python3.10 chat.py --system-file ./system_prompt.txt
python3.10 chat.py --system '日本語で短く回答してください。' --prompt '自己紹介してください'
```

- `/reset`: system prompt を保持して会話履歴をクリア。
- `/exit` または Ctrl-D: チャット終了。サーバーはターミナル1で Ctrl-C で停止。
- 履歴はプロセス内のみで保持し、ファイルには保存しません。
- system prompt の編集はクライアント再起動で反映します。
- 応答はストリーミング表示。thinking は無効にしています。

## 設定

デフォルトはポート8080、コンテキスト8192トークン（system、会話履歴、回答の合計）、
最大回答2048トークンです。長い会話で上限エラーが出たら `/reset` を使ってください。

```bash
PORT=8081 CTX_SIZE=16384 bash start_server.sh
python3.10 chat.py --base-url http://127.0.0.1:8081/v1 --max-tokens 4096
```

モデルは `models/` に保存され、次回から再利用されます。
Python 3.10以上と curl が必要です。起動時にサイズとSHA-256を検証します。
ダウンロードをロックし、検証済みファイルのみを llama-server に渡します。
テキスト専用なので mmproj はダウンロードしません。
メモリ不足なら `CTX_SIZE=4096 bash start_server.sh` でコンテキストを減らしてください。
量子化を変更する場合は、download_model.py のファイル名・URL・サイズ・SHA-256と
start_server.sh のモデルパスを対応する値に揃える必要があります。
サーバーはローカルの127.0.0.1で待ち受けます。

ブラウザでは http://127.0.0.1:8080/ にアクセスすると案内ページが表示されます。
このページは稼働確認用です。チャットは `chat.py` で行います。
8000番はこの設定では使いません。`/health` が `{"status":"ok"}` ならAPIは稼働しています。
組み込みWeb UIがないllama.cppでも案内ページが表示されるよう、`--path web` を指定しています。

`<unused50>` の連続出力が発生した際、旧HFキャッシュのGGUFが配布元のサイズ・SHA-256と
一致しないことを確認しました。新しい起動スクリプトはそのキャッシュを使用しません。
古いサーバーをCtrl-Cで停止してから `bash start_server.sh` で起動し直してください。

llama-server がないMacでは `brew install llama.cpp` でインストールしてください。
`unknown model architecture: gemma4` などが出る場合は `brew upgrade llama.cpp` で更新してください。

## 参考

- [モデルと推奨設定](https://huggingface.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive)
- [llama.cpp server API](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

起動スクリプトは既定で `python3.10` を使います。別のPythonを使う場合は
`PYTHON=python3 bash start_server.sh` のように指定してください。
