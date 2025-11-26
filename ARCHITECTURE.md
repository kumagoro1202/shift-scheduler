# シフト作成プログラム - システム設計書（小規模施設版）

## 1. システム概要

**対象**: 5名程度の小規模施設  
**目的**: 職員の能力を点数化し、各時間帯の能力値が均等になるよう最適化されたシフト表を自動生成  
**動作環境**: ローカルPC（サーバー不要）

## 2. 採用アーキテクチャ

### 2.1 アーキテクチャパターン
**デスクトップアプリケーション（オールインワン）**

```
┌─────────────────────────────────────────────┐
│     デスクトップアプリケーション             │
│                                             │
│  ┌───────────────────────────────────┐     │
│  │   UI層 (Streamlit / Tkinter)     │     │
│  └────────────┬──────────────────────┘     │
│               │                             │
│  ┌────────────▼──────────────────────┐     │
│  │   ビジネスロジック層              │     │
│  │   (Python)                        │     │
│  │  ┌─────────────────────────────┐ │     │
│  │  │ シフト最適化エンジン         │ │     │
│  │  │ (PuLP - 軽量)               │ │     │
│  │  └─────────────────────────────┘ │     │
│  └────────────┬──────────────────────┘     │
│               │                             │
│  ┌────────────▼──────────────────────┐     │
│  │   データ層                        │     │
│  │   (SQLite - ファイルベース)      │     │
│  └───────────────────────────────────┘     │
│                                             │
│  ローカルPC (Windows/Mac)                  │
└─────────────────────────────────────────────┘
```

### 2.2 設計の理由

1. **Pythonスタンドアロン**: インストール簡単、依存関係が少ない
2. **SQLite**: サーバー不要、ファイルベースで管理が容易
3. **Streamlit**: Webブラウザで動作するがローカル完結、開発が高速
4. **PuLP**: OR-Toolsより軽量で小規模データに最適

## 3. 技術スタック（小規模・シンプル構成）

### 3.1 コアテクノロジー
| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.11+ | メイン言語 |
| Streamlit | 1.28+ | UIフレームワーク |
| SQLite | 3.x | データベース（ファイルベース） |
| PuLP | 2.7+ | 最適化ソルバー |
| Pandas | 2.x | データ操作 |

### 3.2 補助ライブラリ
| 技術 | バージョン | 用途 |
|------|-----------|------|
| plotly | 5.x | グラフ・チャート表示 |
| openpyxl | 3.x | Excelファイル出力 |
| python-dateutil | 2.x | 日付処理 |

### 3.3 開発ツール
| 技術 | 用途 |
|------|------|
| PyInstaller | 実行ファイル化（.exe作成） |
| pytest | テスティング |
| black | コードフォーマッター |

### 3.4 動作環境
- **OS**: Windows 10/11, macOS 12+, Linux
- **メモリ**: 4GB以上推奨
- **ストレージ**: 500MB以上の空き容量
- **ブラウザ**: Chrome, Firefox, Edge（Streamlit表示用）

## 4. データモデル設計（簡素版）

### 4.1 主要テーブル（SQLite）

#### employees（職員）
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    skill_score INTEGER NOT NULL,  -- 1-100
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### time_slots（時間帯）
```sql
CREATE TABLE time_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,  -- 例: "午前", "午後", "夜間"
    start_time TEXT NOT NULL,  -- HH:MM
    end_time TEXT NOT NULL,    -- HH:MM
    required_employees INTEGER DEFAULT 2
);
```

#### shifts（シフト）
```sql
CREATE TABLE shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    time_slot_id INTEGER,
    employee_id INTEGER,
    FOREIGN KEY (time_slot_id) REFERENCES time_slots(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    UNIQUE(date, time_slot_id, employee_id)
);
```

#### availability（勤務可能情報）
```sql
CREATE TABLE availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    date DATE NOT NULL,
    time_slot_id INTEGER,
    is_available BOOLEAN DEFAULT 1,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (time_slot_id) REFERENCES time_slots(id)
);
```

#### settings（設定）
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- 例: max_consecutive_days, target_average_score
```

## 5. 最適化アルゴリズム（シンプル版）

### 5.1 最適化問題の定式化

**目的**: 各時間帯のスキルスコアが均等になること

```python
# 目的関数: 各時間帯のスキル合計値の差を最小化
minimize: Σ |time_slot_score[i] - target_average|
```

**制約条件**（最小限）:
1. 各シフトの必要人数を満たす
2. 職員の勤務可能時間内
3. 1人1日1シフトまで（簡素化）

### 5.2 ソルバー

**PuLP + CBC Solver**
- 理由: インストール簡単、小規模データに十分、軽量
- 5名程度なら数秒で解決可能

### 5.3 アルゴリズムフロー

```
1. データ取得（職員、時間帯、可能情報）
2. 制約条件の設定
3. 目的関数の設定
4. ソルバー実行（最大60秒）
5. 結果の取得とDB保存
```

## 6. 機能設計（最小限）

### 6.1 画面構成

**Streamlitのマルチページアプリ**

```
🏠 ホーム（ダッシュボード）
├─ 📊 今月のシフト概要
└─ 📈 スキル分布グラフ

👥 職員管理
├─ 職員一覧
├─ 職員追加・編集
└─ スキルスコア設定

⏰ 時間帯設定
├─ 時間帯一覧
└─ 時間帯追加・編集

📅 勤務可能情報
├─ カレンダー入力
└─ 一括設定

🎯 シフト生成
├─ 生成パラメータ設定
├─ 自動生成実行
└─ 結果プレビュー

📋 シフト表示・編集
├─ 月別カレンダー表示
├─ 手動編集
└─ Excel出力
```

### 6.2 主要機能

| 機能 | 説明 |
|------|------|
| 職員管理 | 名前とスキルスコアの登録・編集 |
| 時間帯設定 | 1日の時間帯を定義（午前・午後等） |
| 可能情報入力 | 職員ごとの勤務可能日時を登録 |
| シフト自動生成 | 最適化エンジンでシフト作成 |
| シフト表示 | カレンダー形式で表示 |
| 手動調整 | 自動生成後の微調整 |
| Excel出力 | 印刷用にExport |

## 7. セキュリティ設計（シンプル版）

### 7.1 データ保護
- データベースファイル（.db）の適切な配置
- バックアップ機能（手動コピー推奨）
- データのローカル保存（外部送信なし）

### 7.2 アクセス制御
- 基本的な認証は不要（ローカルPC使用のため）
- 必要に応じて起動時パスワード追加可能

## 8. 配布・インストール

### 8.1 配布形態

**オプション1: Pythonスクリプト配布**
- requirements.txt同梱
- ユーザーがPythonインストール必要

**オプション2: 実行ファイル（推奨）**
- PyInstallerで.exe化（Windows）
- ダブルクリックで起動
- Python不要

### 8.2 インストール手順（実行ファイル版）

```
1. ZIPファイルをダウンロード
2. 任意のフォルダに解凍
3. shift_app.exe をダブルクリック
4. ブラウザが自動起動
```

### 8.3 データ保存場所

```
shift_app/
├── shift_app.exe        # 実行ファイル
├── data/
│   └── shift.db        # データベース（自動作成）
└── exports/            # Excel出力先
```
