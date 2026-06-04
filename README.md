# music-library

PC 上で YouTube から MP3 を取り込み、フォルダで曲を管理する個人プロジェクト。  
スマホには選んだ曲だけ USB でコピーして、標準の音楽アプリで再生する想定。

**YouTube 利用規約・著作権に注意。** 自分が権利を持つ／ダウンロードが許可されているコンテンツにのみ使うこと。

## できること

- YouTube URL から音声だけを MP3 でダウンロード
- 先頭・末尾の無音を自動削除（デフォルト ON）
- 音量を一定に正規化（デフォルト ON、-14 LUFS 目標）
- `library/` フォルダへの保存と一覧表示（Web UI）
- 曲のメタデータ編集（ファイル名・曲名・アーティスト・アルバム → MP3 の ID3 タグ）
- `library/済み/` に移した曲も Web UI で一覧・編集・ライブラリへ戻す
- 音質・YouTube プレイリスト一括取得のオプション
- ファイル名編集時の重複防止（`library/` と `済み/` に同名があれば `_xxxxxxxx` の ID を付与）

## 構成

```
music-library/
  start.cmd         # ショートカットから Web UI を起動（ASCII のみ・日本語を書かない）
  core/             # 共通ロジック（取り込み・音声処理・メタデータ）
  tools/ingest/     # CLI
  tools/web/        # ローカル Web UI
  library/          # ローカル音源（git 管理外）
    *.mp3           # 取り込み直後・スマホ投入前の曲
    済み/           # スマホに入れた曲（エクスプローラーで手動移動）
```

プレイリスト管理や `phone/` への自動コピー UI は未実装（[ロードマップ](#ロードマップ) 参照）。

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

### ショートカット（おすすめ）

デスクトップの **music-library起動** をダブルクリックする。

- venv の有効化（`Activate.ps1`）は **不要**（`start.cmd` が `.venv\Scripts\python.exe` を直接使う）
- サーバー起動後（約2秒）にブラウザが開く
- 8765 が既に使用中なら、ブラウザだけ開いて警告を表示（古い cmd 窓が残っている可能性）
- 黒い窓（cmd）はサーバー実行中ずっと開いたまま（**Ctrl+C** で停止）
- **表示が古い・ボタンがない** ときは、以前起動した cmd 窓が残っていないか確認し、すべて **Ctrl+C** してからショートカットを再度実行

> `start.cmd` は Windows の cmd 向けに **英語（ASCII）のみ** で書く。日本語を入れると文字化けして起動に失敗することがある。

ショートカットを作り直す場合:

```powershell
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut("$env:USERPROFILE\OneDrive\デスクトップ\music-library起動.lnk")
$s.TargetPath = "C:\Windows\System32\cmd.exe"
$s.Arguments = '/k "D:\github\music-library\start.cmd"'
$s.WorkingDirectory = "D:\github\music-library"
$s.Save()
```

### 手動（ターミナル）

#### 1. プロジェクトへ移動して venv を有効化

```powershell
cd D:\github\music-library
.venv\Scripts\Activate.ps1
```

#### 2. サーバーを起動

```powershell
python tools/web/app.py
```

venv を有効化しない場合:

```powershell
.venv\Scripts\python.exe tools\web\app.py
```

次のように表示されれば OK:

```
music-library: http://127.0.0.1:8765
library: D:\github\music-library\library
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

#### 3. ブラウザで開く

**http://127.0.0.1:8765**

YouTube URL を貼って「ダウンロード」を押す。完了すると `library/` に MP3 が保存され、画面下部のライブラリ一覧が更新される。

#### 4. 停止

サーバーを起動したターミナルで **`Ctrl+C`**

---

## Web UI

### ダウンロード

| 項目 | 説明 |
|------|------|
| YouTube URL | 取り込む動画の URL |
| 音質 (kbps) | 128 / 192 / 256 / 320（デフォルト 192） |
| プレイリスト全体 | チェック時、YouTube プレイリスト内の全曲を取得 |
| 先頭・末尾の無音を削除 | チェック時、FFmpeg で無音部分をトリム（デフォルト ON） |
| 音量を一定にする | チェック時、FFmpeg loudnorm で音量を正規化（デフォルト ON） |

### ライブラリ

取り込んだ MP3 を **ライブラリ**（`library/` 直下）と **済み**（`library/済み/`）の2セクションで表示する。

各曲には次が表示される。

- **曲名** — ID3 タグ（未設定時はファイル名）
- **アーティスト** — ID3 タグ（未設定時は「（未設定）」）
- **アルバム** — ID3 タグ（未設定時は「（未設定）」）
- ファイル名・サイズ

**編集** ボタンから次を変更できる。

| 項目 | 保存先 |
|------|--------|
| ファイル名（拡張子なし） | MP3 ファイルのリネーム（`library/` と `済み/` に同名があるときは `名前_8桁ID` に自動変更） |
| 曲名 | ID3 `TIT2` |
| アーティスト | ID3 `TPE1` |
| アルバム | ID3 `TALB` |

スマホの標準音楽アプリでは、曲名・アーティスト・アルバムは主に ID3 タグが使われる。USB コピー前に編集しておくと表示が整いやすい。

`library/済み/` への移動は **エクスプローラーで手動**（ドラッグ＆ドロップ）。**済み** セクションの **ライブラリに戻す** で `library/` 直下へ戻せる。移動後は Web UI の「更新」で反映される。

---

## スマホへ入れる（フォルダ運用）

1. PC の `library/` から入れたい曲を USB で Pixel の **Music/** などにコピー
2. コピー済みの曲は `library/済み/` に移動して整理（手動）
3. Pixel の標準音楽アプリで再生。プレイリストはスマホ側で作成

専用 Android アプリは作らない方針。PC 側のプレイリスト機能も未実装。

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

# YouTube プレイリスト全体
python tools/ingest/download.py "https://www.youtube.com/playlist?list=..." --playlist

# 無音トリムをスキップ
python tools/ingest/download.py "URL" --no-trim-silence

# 音量正規化をスキップ
python tools/ingest/download.py "URL" --no-normalize-loudness
```

メタデータ編集は Web UI のみ（CLI 未対応）。

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

### ショートカット起動で文字化けエラー（`'ause'` など）

`start.cmd` に日本語を書いた UTF-8 保存などで、cmd が行を誤読している。リポジトリの `start.cmd` をそのまま使う（内容は ASCII のみ）。メッセージは英語表示が正常。

### Web UI の表示が古い・ボタンがない

- 8765 で **古いサーバー** が動いていないか確認（すべて Ctrl+C）
- ブラウザで **Ctrl+Shift+R**（強制再読み込み）

### 済みに移した曲が一覧に出ない

- 移動先が `library/済み/` であることを確認（サブフォルダ名は `core/paths.py` の `SYNCED_FOLDER` と一致）
- Web UI の **更新** を押す

---

## ロードマップ

1. **ingest** — URL → MP3（CLI + Web） ✅
2. **library 管理** — メタデータ編集、`済み/` 一覧 ✅ / プレイリスト、スマホ用フォルダへの振り分け（未）
3. **同期補助** — 選んだ曲をコピーする UI、同期状態の記録（未）
