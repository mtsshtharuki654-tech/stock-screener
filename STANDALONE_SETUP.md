# PPP Stock Screener - スタンドアロン化ガイド

このアプリをスタンドアロン実行ファイル（EXE）として配布・実行できるようにセットアップしました。

## セットアップ内容

### ✅ 実施済みの変更

1. **Vite設定更新** (`frontend/vite.config.ts`)
   - フロントエンドビルド出力先を `backend/static` に変更
   - バックエンドと一つのアプリケーションとして配布可能に

2. **FastAPI修正** (`backend/app/main.py`)
   - 静的ファイル（React UI）をバックエンド経由で提供
   - ビルド後、URLアクセスでUIが自動表示される

3. **ビルドスクリプト** (`build.py`)
   - NPM + Pythonパッケージをワンコマンドで構築
   - フロントエンド、バックエンド、PyInstallerを順序通りコンパイル

4. **PyInstallerスペック** (`stock_screener.spec`)
   - スタンドアロンEXE生成設定
   - 必要な依存ファイルを自動バンドル

---

## 🚀 実行手順

### 1. 環境準備

```bash
# Node.jsとPythonをインストール（未済の場合）
# Node.js: https://nodejs.org/ (LTS推奨)
# Python: https://www.python.org/ (3.9以上)
```

### 2. ビルド（初回）

```bash
cd stock_screener

# 依存パッケージ削除（クリーンビルド）
rm -r frontend/node_modules backend/venv frontend/dist
# PowerShell の場合
# Remove-Item frontend/node_modules -Recurse -Force
# Remove-Item backend/venv -Recurse -Force

# ビルド実行
python build.py
```

**初回は10〜15分かかる場合があります**（npm install + Python venv構築）

### 3. 出力ファイル確認

ビルド完了後、以下が生成されます：

```
stock_screener/
├── dist/
│   ├── PPPStockScreener.exe          # ← 実行ファイル
│   └── PPPStockScreener/             # 依存ファイルフォルダ
├── build/                            # PyInstallerの一時ファイル
└── ...
```

### 4. アプリケーション起動

**方法A：EXEをダブルクリック**
```
dist/PPPStockScreener.exe をダブルクリック
→ ブラウザが自動で開く（http://localhost:8000）
```

**方法B：コマンドラインから**
```bash
dist/PPPStockScreener/PPPStockScreener.exe
```

**方法C：配布用フォルダの作成**
```bash
# dist/PPPStockScreener フォルダ全体を配布
# ユーザーは PPPStockScreener.exe をダブルクリックするだけで動作
```

---

## ⚙️ .env設定

バックエンドが JQuants API を使用する場合、以下の設定が必要です：

```bash
# backend/.env または backend/app/config.py 確認
JQUANTS_API_KEY=your_api_key_here
```

EXEビルド前に `.env` ファイルをセットアップしてください。

---

## 🔧 変更が必要な場合

コード修正後に再ビルドする場合：

```bash
# 前のビルド削除
rm -r dist build backend/static

# 再ビルド
python build.py
```

---

## 📝 注意事項

1. **初回ビルドは遅い**
   - npm dependencies: 50-100個ファイル
   - Python環境構築: 30-50個パッケージ
   - PyInstaller: バンドルに3-5分

2. **EXEサイズ**
   - 予想サイズ: 150-250MB（全依存含む）
   - Windowsのみ対応（macOS/Linux向けはpyinstaller設定を別途調整必要）

3. **配布時の注意**
   - `dist/PPPStockScreener/` フォルダ全体が必要
   - `PPPStockScreener.exe` 単体では動作しません

4. **ウイルススキャン**
   - PyInstallerで生成されたEXEは、一部アンチウイルスで誤検知される可能性があります
   - その場合は、ホワイトリストに登録してください

---

## 🆘 トラブルシューティング

### `npm not found` エラー
→ Node.jsをインストールしてください: https://nodejs.org/

### `Python not found` エラー
→ Pythonをインストールしてください: https://www.python.org/

### `Permission denied` （Macの場合）
```bash
chmod +x dist/PPPStockScreener/PPPStockScreener
```

### EXE起動後、ブラウザが開かない
→ 手動で `http://localhost:8000` をブラウザで開いてください

### ポート 8000 が使用中
→ 別のアプリがポート 8000 を使用しています
```bash
# 既存プロセス確認
netstat -ano | findstr 8000

# プロセス削除
taskkill /PID <PID> /F
```

---

## 🎯 次のステップ

1. **カスタムアイコン追加** → `stock_screener.spec` の `icon=` を設定
2. **自動起動ポート変更** → `backend/app/config.py` で設定
3. **スタートアップショートカット** → `dist/PPPStockScreener.exe` へのショートカットをスタートメニューに配置
