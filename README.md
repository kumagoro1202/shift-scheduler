# シフト管理システム

小規模施設（5名程度）向けの自動シフト最適化システムです。

## 特徴

- 🎯 **自動最適化**: 職員のスキルスコアを考慮した最適なシフトを自動生成
- 💻 **ローカル実行**: サーバー不要、PC上で完結
- 📊 **視覚化**: グラフや統計でシフトの偏りを確認
- 📥 **Excel出力**: 印刷・配布用にExcel形式で出力可能
- ⚡ **簡単操作**: ブラウザベースの直感的なUI

## クイックスタート

### 方法1: 実行可能ファイル（推奨）

1. `dist/shift_system/shift_system.exe` をダブルクリック
2. ブラウザが自動的に開きます

### 方法2: Pythonから実行

```powershell
# 依存パッケージのインストール
pip install -r requirements.txt

# アプリケーションの起動
streamlit run main.py
```

または、`run.bat` をダブルクリック

## 機能一覧

| 機能 | 説明 |
|-----|------|
| 👥 職員管理 | 職員の登録・編集・削除、スキルスコア設定 |
| ⏰ 時間帯設定 | 勤務時間帯の登録（早番、日勤、遅番など） |
| 📅 勤務可能情報 | カレンダー形式での勤務可能日入力 |
| 🎯 シフト生成 | 最適化アルゴリズムによる自動シフト作成 |
| 📋 シフト表示 | カレンダー表示、統計分析、Excel出力 |

## システム要件

- **OS**: Windows 10/11
- **メモリ**: 2GB以上推奨
- **ディスク**: 100MB以上の空き容量
- **ブラウザ**: Chrome, Edge, Firefox など

## 技術スタック

- **言語**: Python 3.11+
- **フレームワーク**: Streamlit 1.28.0
- **データベース**: SQLite 3.x
- **最適化エンジン**: PuLP 2.7.0
- **可視化**: Plotly, Pandas

## 開発環境セットアップ

Pythonから実行する場合の手順:

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd shift-scheduler
```

### 2. 依存パッケージのインストール

```powershell
pip install -r requirements.txt
```

### 3. アプリケーションの起動

```powershell
streamlit run main.py
```

ブラウザで <http://localhost:8501> が自動的に開きます。

## プロジェクト構成

```text
shift-scheduler/
├── main.py                 # アプリケーションエントリーポイント
├── requirements.txt        # Python依存関係
├── init_sample_data.py     # サンプルデータ投入スクリプト
├── run.bat                 # 起動用バッチファイル
├── build.spec              # PyInstallerビルド設定
├── shift.db                # SQLiteデータベース（自動生成）
├── src/                    # ソースコード
│   ├── database.py         # データベース操作
│   ├── optimizer.py        # シフト最適化エンジン
│   └── utils.py            # ユーティリティ関数
├── pages/                  # Streamlitページ
│   ├── 1_👥_職員管理.py
│   ├── 2_⏰_時間帯設定.py
│   ├── 3_📅_勤務可能情報.py
│   ├── 4_🎯_シフト生成.py
│   └── 5_📋_シフト表示.py
├── exports/                # Excel出力先（自動生成）
└── USER_GUIDE.md           # 利用ガイド
```

## ドキュメント

- **[利用ガイド](USER_GUIDE.md)**: 詳細な操作方法とトラブルシューティング
- **[設計書](ARCHITECTURE.md)**: システムアーキテクチャと設計思想
- **[実装計画](IMPLEMENTATION_PLAN.md)**: 開発計画と進捗管理

## 実行可能ファイルのビルド

開発者向け: `.exe` ファイルを作成する場合

```powershell
# PyInstallerのインストール
pip install pyinstaller

# ビルド実行
pyinstaller build.spec

# 出力先: dist/shift_system/shift_system.exe
```

## バックアップ

データベースファイル (`shift.db`) を定期的にバックアップしてください:

```powershell
Copy-Item shift.db "shift_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

## ライセンス

このソフトウェアは社内利用を目的としています。

## サポート

システムに関するご質問は、システム管理者までお問い合わせください。

---

**Version**: 1.0.0  
**リリース日**: 2025年11月26日
