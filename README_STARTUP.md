# PPP Stock Screener - 起動ガイド

## 🚀 起動方法

### 方法1：ローカル開発環境（推奨）

フロントエンド + バックエンドを一度に起動：

```bash
cd stock_screener
python run_dev.py
```

**自動で以下が起動します：**
- ✅ Vite dev server: http://localhost:5173
- ✅ FastAPI backend: http://localhost:8000
- ✅ ブラウザが自動で開く

終了するには **Ctrl+C** を押してください。

---

### 方法2：スタンドアロン実行ファイル（配布用）

ビルドが完了した後：

```bash
dist/PPPStockScreener/PPPStockScreener.exe
```

をダブルクリックすると、一つのアプリケーションとして起動します。

- フロントエンド、バックエンドが統合
- ブラウザが自動で http://localhost:8000 を開く
- 全ての依存ファイルがバンドルされている

詳細は [STANDALONE_SETUP.md](STANDALONE_SETUP.md) を参照

---

### 方法3：手動で別々に起動（デバッグ用）

**ターミナル1 - フロントエンド：**
```bash
cd frontend
npm run dev
```
→ http://localhost:5173

**ターミナル2 - バックエンド：**
```bash
cd backend
python -m uvicorn app.main:app --reload
```
→ http://localhost:8000

---

## 📝 必要な設定

### `.env` ファイル設定

バックエンドが JQuants API を使用する場合：

```bash
# backend/.env
JQUANTS_API_KEY=your_api_key_here
```

---

## 🛠️ 初回セットアップ

```bash
# 1. Node.js + npm をインストール
# https://nodejs.org/

# 2. Python 3.9+ をインストール
# https://www.python.org/

# 3. 依存パッケージをインストール
cd frontend
npm install

cd ../backend
pip install -r requirements.txt
```

---

## 📦 ビルド（EXE生成）

```bash
cd stock_screener
python build.py
```

**出力:** `dist/PPPStockScreener/PPPStockScreener.exe`

初回ビルドは 15-30分かかります。

---

## 🆘 トラブルシューティング

| 問題 | 解決策 |
|------|--------|
| `npm: command not found` | Node.jsをインストール: https://nodejs.org/ |
| `python: command not found` | Pythonをインストール: https://www.python.org/ |
| ポート8000が使用中 | 別のアプリが使用中。`taskkill /PID <PID> /F` で終了 |
| ブラウザが開かない | 手動で http://localhost:5173 を開く |
| `venv not found` | `pip install -r requirements.txt` を実行 |

---

## 📚 詳細ドキュメント

- [AGENTS.md](AGENTS.md) - 開発者向けガイド
- [STANDALONE_SETUP.md](STANDALONE_SETUP.md) - EXE配布ガイド
