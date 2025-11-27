# シフト管理システム V2.0

小規模施設（5名程度）向けの高度な自動シフト最適化システムです。

## 🆕 V2.0 新機能

- ✨ **4項目スキルスコア**: リハ室、受付午前/午後、総合対応力を個別評価
- 👥 **職員タイプ制約**: TYPE_A〜Dによる業務エリア制限機能
- 🕐 **勤務形態管理**: フルタイム、時短、パートの詳細管理
- ☕ **休憩ローテーション**: 自動休憩時間割り当て（窓口常駐人数を保証）
- 🎚️ **最適化モード**: バランス/スキル重視/日数重視の3モード選択可能

## 特徴

- 🎯 **高度な最適化**: 4項目スキルスコアと職員タイプを考慮した最適シフト自動生成
- 💻 **ローカル実行**: サーバー不要、PC上で完結
- 📊 **詳細な視覚化**: グラフや統計でシフトバランスを多角的に分析
- 📥 **Excel出力**: 印刷・配布用にExcel形式で出力可能
- ⚡ **簡単操作**: ブラウザベースの直感的なUI
- 🔄 **完全互換**: V1.0データを自動マイグレーション

## クイックスタート

### 方法1: 実行可能ファイル（推奨）

1. `dist/shift_system/shift_system.exe` をダブルクリック
2. ブラウザが自動的に開きます
3. 初回起動時にV2.0へ自動マイグレーション

### 方法2: Pythonから実行

```powershell
# 依存パッケージのインストール
pip install -r requirements.txt

# アプリケーションの起動
streamlit run main.py
```

または、`scripts/run.bat` をダブルクリック

## 機能一覧

| 機能 | 説明 |
|-----|------|
| 👥 職員管理 | 職員タイプ、4項目スキルスコア、勤務形態の詳細管理 |
| ⏰ 時間帯設定 | 業務エリア、時間区分、目標スキルスコアの設定 |
| 📅 勤務可能情報 | 勤務不可の日時を登録（未登録は自動的に勤務可能） |
| 🎯 シフト生成 | 3つの最適化モードによる自動シフト作成 |
| ☕ 休憩管理 | 自動休憩時間割り当てと窓口カバレッジ検証 |
| 📋 シフト表示 | カレンダー表示、休憩時間、統計分析、Excel出力 |

## V2.0 主要機能詳細

### 職員タイプ

- **TYPE_A**: リハ室・受付両方可能（最も柔軟）
- **TYPE_B**: 受付のみ
- **TYPE_C**: リハ室のみ（正職員）
- **TYPE_D**: リハ室のみ（パート、特殊ルール適用）

### スキルスコア（4項目）

- **リハ室スキル**: リハビリ室での業務能力（0-100）
- **受付午前スキル**: 受付業務（午前）の能力（0-100）
- **受付午後スキル**: 受付業務（午後）の能力（0-100）
- **総合対応力**: 全般的な対応能力（0-100）

### 最適化モード

- **バランス**: 勤務回数とスキルの両方を考慮（推奨）
- **スキル重視**: 目標スキルスコアへの近似を優先
- **日数重視**: 勤務回数の均等化を優先

### 休憩ローテーション

- フルタイム職員: 1時間×2回
- 時短勤務職員: 1時間×1回
- パート職員: 休憩なし
- 受付窓口には常に2名以上が実働状態を保証

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

### 4. テスト実行（オプション）

```powershell
# シフト生成ロジックのテスト
python tests/test_new_logic.py

# サンプルデータの投入
python scripts/init_sample_data.py
```

## プロジェクト構成

```text
shift-scheduler/
├── main.py                 # アプリケーションエントリーポイント
├── requirements.txt        # Python依存関係
├── README.md               # このファイル
├── src/                    # ソースコード
│   ├── database.py         # データベース操作（V2拡張対応）
│   ├── optimizer_v2.py     # V2.0最適化エンジン
│   ├── optimizer.py        # V2ラッパー（後方互換）
│   ├── migration.py        # V1→V2マイグレーション
│   ├── break_scheduler.py  # 休憩時間自動割り当て
│   └── utils.py            # ユーティリティ関数
├── pages/                  # Streamlitページ
│   ├── 1_👥_職員管理.py    # V2.0対応（4項目スキル）
│   ├── 2_⏰_時間帯設定.py   # V2.0対応（業務エリア、目標スキル）
│   ├── 3_📅_勤務可能情報.py
│   ├── 4_🎯_シフト生成.py   # V2.0対応（最適化モード選択）
│   └── 5_📋_シフト表示.py   # V2.0対応（休憩時間表示）
├── docs/                   # ドキュメント
│   ├── USER_GUIDE.md       # 利用ガイド（V2.0更新）
│   ├── ARCHITECTURE.md     # 設計書
│   ├── SYSTEM_REQUIREMENTS_V2.md  # V2.0要件定義
│   ├── MIGRATION_PLAN_V2.md       # V2.0改修計画
│   ├── IMPLEMENTATION_COMPLETE_V2.md  # V2.0実装完了レポート
│   └── MIGRATION_GUIDE_V1_TO_V2.md    # マイグレーションガイド
├── scripts/                # ユーティリティスクリプト
│   ├── run.bat             # 起動用バッチファイル
│   ├── launcher.py         # GUIランチャー
│   ├── init_sample_data.py # サンプルデータ投入
│   ├── update_time_slots.py # 時間帯更新
│   └── build.spec          # PyInstallerビルド設定
├── tests/                  # テストファイル
│   ├── test_v2_features.py # V2.0機能テスト
│   ├── test_new_logic.py   # シフト生成ロジックテスト
│   ├── test_overlap.py     # 時間重複チェックテスト
│   └── check_capacity.py   # 人数チェック
├── data/                   # データベース（自動生成）
│   └── shift.db            # SQLiteデータベース（V2.0スキーマ）
├── build/                  # ビルド成果物
└── dist/                   # 配布用実行ファイル
```

## ドキュメント

### V2.0関連

- **[V2.0システム要件](docs/SYSTEM_REQUIREMENTS_V2.md)**: V2.0の詳細仕様
- **[V2.0実装完了レポート](docs/IMPLEMENTATION_COMPLETE_V2.md)**: 実装内容のサマリ
- **[マイグレーションガイド](docs/MIGRATION_GUIDE_V1_TO_V2.md)**: V1.0からV2.0への移行手順

### 基本ドキュメント

- **[利用ガイド](docs/USER_GUIDE.md)**: 詳細な操作方法とトラブルシューティング
- **[設計書](docs/ARCHITECTURE.md)**: システムアーキテクチャと設計思想
- **[実装計画](docs/IMPLEMENTATION_PLAN.md)**: 開発計画と進捗管理

## 実行可能ファイルのビルド

開発者向け: `.exe` ファイルを作成する場合

```powershell
# PyInstallerのインストール
pip install pyinstaller

# ビルド実行
pyinstaller scripts/build.spec

# 出力先: dist/shift_system/shift_system.exe
```

## バックアップ

データベースファイル (`data/shift.db`) を定期的にバックアップしてください:

```powershell
Copy-Item data/shift.db "shift_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

## ライセンス

このソフトウェアは社内利用を目的としています。

## サポート

システムに関するご質問は、システム管理者までお問い合わせください。

---

**Version**: 1.0.0  
**リリース日**: 2025年11月26日
