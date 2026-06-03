# music-library

PC 上で YouTube から MP3 を取り込み、フォルダで曲を管理する個人プロジェクト。  
スマホには選んだ曲だけ USB でコピーして、標準の音楽アプリで再生する想定。

**YouTube 利用規約・著作権に注意。** 自分が権利を持つ／ダウンロードが許可されているコンテンツにのみ使うこと。

## できること

- YouTube URL から音声だけを MP3 でダウンロード
- 先頭・末尾の無音を自動削除（デフォルト ON）
- 音量を一定に正規化（デフォルト ON、-14 LUFS 目標）
- `library/` フォルダへの保存と一覧表示（Web UI）
- 音質・プレイリスト全体のオプション

## 構成（予定）

```
music-library/
  core/             # 共通ロジック（取り込み・音声処理）
  tools/ingest/     # CLI
  tools/web/        # ローカル Web UI
  library/          # ローカル音源（git 管理外）
    all/            # 取り込みした全曲（予定）
    phone/          # スマホに入れる曲だけ（予定）
    playlists/      # プレイリスト用フォルダ（予定）
```

## 必要なもの

| ソフト | 用途 | インストール例 |
|--------|------|----------------|
| Python 3.10+ | アプリ本体 | [python.org](https://www.python.org/downloads/) |
| FFmpeg | MP3 変換・無音トリム | `winget install Gyan.FFmpeg` |
| Deno | YouTube JS チャレンジ解決 | `winget install DenoLand.Deno` |

インストール後、**ターミナル（Cursor 含む）を再起動**して PATH を反映させる。

```powershell
ffmpeg -version
deno --version
```

PATH が反映されない場合は、セッションだけ更新できる:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

> Deno は PATH に無くても動作する（winget のインストール先を自動検出）。  
> 初回ダウンロード時のみ GitHub / npm から JS solver スクリプトを取得する（以降はキャッシュ）。

---

## 初回セットアップ

```powershell
cd D:\github\music-library   # クローン先に合わせて変更

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

プロンプトに `(.venv)` が表示されていれば仮想環境が有効。

---

## 起動方法（Web アプリ）

毎回、次の手順で起動する。

### 1. プロジェクトへ移動して venv を有効化

```powershell
cd D:\github\music-library
.venv\Scripts\Activate.ps1
```

### 2. サーバーを起動

```powershell
python tools/web/app.py
```

次のように表示されれば OK:

```
music-library: http://127.0.0.1:8765
library: D:\github\music-library\library
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

### 3. ブラウザで開く

**http://127.0.0.1:8765**

YouTube URL を貼って「ダウンロード」を押す。完了すると `library/` に MP3 が保存され、画面下部のライブラリ一覧が更新される。

### 4. 停止

サーバーを起動したターミナルで **`Ctrl+C`**

---

## Web UI のオプション

| 項目 | 説明 |
|------|------|
| YouTube URL | 取り込む動画の URL |
| 音質 (kbps) | 128 / 192 / 256 / 320（デフォルト 192） |
| プレイリスト全体 | チェック時、プレイリスト内の全曲を取得 |
| 先頭・末尾の無音を削除 | チェック時、FFmpeg で無音部分をトリム（デフォルト ON） |
| 音量を一定にする | チェック時、FFmpeg loudnorm で音量を正規化（デフォルト ON） |

---

## スマホへ入れる（フォルダ運用）

1. PC の `library/`（将来は `library/phone/`）に入れたい曲だけ置く
2. USB で Pixel の **Music/** などにコピー
3. Pixel の標準音楽アプリで再生

専用 Android アプリは作らない方針。

---

## CLI

venv を有効化したうえで:

```powershell
# 基本（./library に保存）
python tools/ingest/download.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 保存先を指定
python tools/ingest/download.py "https://youtu.be/VIDEO_ID" -o "D:\Music"

# 音質を指定（kbps）
python tools/ingest/download.py "URL" -q 320

# プレイリスト全体
python tools/ingest/download.py "https://www.youtube.com/playlist?list=..." --playlist

# 無音トリムをスキップ
python tools/ingest/download.py "URL" --no-trim-silence

# 音量正規化をスキップ
python tools/ingest/download.py "URL" --no-normalize-loudness
```

---

## トラブルシューティング

### ポート 8765 が使用中

```
ERROR: [Errno 10048] ... bind on address ('127.0.0.1', 8765)
```

前回起動したサーバーが残っている。次でプロセスを確認して停止:

```powershell
netstat -ano | findstr :8765
Stop-Process -Id <PID> -Force
```

または、サーバーを起動したターミナルで `Ctrl+C`。

### ffmpeg / deno が見つからない

- ターミナル（Cursor ごと）を再起動
- 上記の `$env:Path = ...` で PATH を更新
- `ffmpeg -version` / `deno --version` で確認

### YouTube ダウンロードの WARNING

Deno 導入後、初回は solver スクリプトの取得ログが出る（正常）:

```
[jsc:deno] Solving JS challenges using deno
[jsc:deno] Downloading challenge solver lib script from https://github.com/...
```

`Signature solving failed` が出る場合は Deno のインストールとサーバー再起動を確認。

---

## ロードマップ

1. **ingest** — URL → MP3（CLI + Web） ✅
2. **library 管理** — 曲名編集、プレイリスト、スマホ用フォルダへの振り分け
3. **同期補助** — 選んだ曲を `phone/` にコピーする UI
