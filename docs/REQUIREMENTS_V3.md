# シフト作成システム V3.0 要求事項定義書

## 変更日: 2025年11月27日

---

## 1. 変更の背景と目的

### 1.1 現状の課題
- V2.0では時間帯ごとに職員の勤務可否を登録する必要があり、運用が煩雑
- 診療時間が固定されているにも関わらず、時間帯設定が柔軟すぎる
- 職員の勤務形態によって勤務可能な時間帯は自動的に決まるため、個別登録は不要

### 1.2 改善の目的
- **運用の簡素化**: 日付単位での休暇登録のみで運用可能に
- **データ整合性の向上**: 診療時間と勤務形態を固定化し、誤入力を防止
- **初期データの整備**: 新要件に適合したサンプルデータの準備

---

## 2. 新要件定義

### 2.1 診療時間（固定）

#### 営業日と診療時間

| 曜日 | 午前診療 | 午後診療 | 備考 |
|------|---------|---------|------|
| 月曜 | 09:00-12:30 | 15:30-18:30 | 通常診療 |
| 火曜 | 09:00-12:30 | 15:30-18:30 | 通常診療 |
| 水曜 | 09:00-12:30 | 15:30-17:30 | 午後は1時間短縮 |
| 木曜 | 09:00-12:30 | 休診 | 午前のみ |
| 金曜 | 09:00-12:30 | 15:30-18:30 | 通常診療 |
| 土曜 | 09:00-13:30 | 休診 | 午前のみ（延長） |
| 日曜 | 休診 | 休診 | 定休日 |

**重要**: 時間帯設定は上記の通り固定とし、ユーザーによる変更は不可とする。

### 2.2 勤務形態による勤務時間の固定化

職員の勤務形態によって、勤務可能な時間帯は自動的に決定される。

#### 勤務形態マスタ

| 勤務形態 | 分類 | 勤務可能時間 | 休憩時間 | 実働時間 |
|---------|------|------------|---------|---------|
| フルタイム（早番） | 正職員 | 08:30-18:30 | 2時間 | 8時間 |
| フルタイム（中番） | 正職員 | 08:45-18:45 | 2時間 | 8時間 |
| フルタイム（遅番） | 正職員 | 09:00-19:00 | 2時間 | 8時間 |
| 時短勤務 | 正職員 | 08:45-16:45 | 1時間 | 7時間 |
| パート午前 | パート | 08:45-12:45 | なし | 4時間 |
| パート午前延長 | パート | 08:45-13:45 | なし | 5時間 |

#### 勤務形態ごとの時間帯対応表

| 勤務形態 | 月〜金午前 | 月火金午後 | 水午後 | 木午前 | 土午前 |
|---------|-----------|-----------|--------|--------|--------|
| フルタイム（早番） | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| フルタイム（中番） | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| フルタイム（遅番） | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| 時短勤務 | ⭕ | ❌ | ❌ | ⭕ | ⭕ |
| パート午前 | ⭕ | ❌ | ❌ | ⭕ | ⭕ |
| パート午前延長 | ⭕ | ❌ | ❌ | ⭕ | ⭕ |

**自動判定ロジック**:
- 職員の勤務形態と勤務開始/終了時間から、各時間帯の勤務可否を自動判定
- ユーザーは時間帯単位での可否登録は不要

### 2.3 勤務可否登録の簡素化

#### 変更前（V2.0）
```
職員: 山田太郎
日付: 2025-12-01
├─ 午前 (09:00-12:30): 勤務可能 ✅
└─ 午後 (15:30-18:30): 勤務不可 ❌
```

#### 変更後（V3.0）
```
職員: 山田太郎
日付: 2025-12-01 → 終日休暇 🏖️
```

**新しい運用**:
- 休暇を取る日付のみを登録
- 登録のない日は、その職員の勤務形態に応じて自動的に勤務可能と判定
- 半日休暇の場合は「午前休」「午後休」を指定可能

---

## 3. データモデルの変更

### 3.1 時間帯マスタ（time_slots）の固定化

**変更内容**: ユーザーによる編集を禁止し、システム定義の時間帯のみを使用

```sql
-- 固定時間帯マスタ
CREATE TABLE time_slots (
    id TEXT PRIMARY KEY,           -- 'mon_am', 'mon_pm', 'tue_am'など
    day_of_week INTEGER NOT NULL,  -- 0=月曜, 1=火曜, ..., 6=日曜
    period TEXT NOT NULL,          -- 'morning' or 'afternoon'
    start_time TEXT NOT NULL,      -- 例: '09:00'
    end_time TEXT NOT NULL,        -- 例: '12:30'
    is_active BOOLEAN DEFAULT 1,   -- 休診日はfalse
    required_staff INTEGER DEFAULT 2,
    area TEXT,                     -- 'リハ室', '受付'など
    CHECK(day_of_week >= 0 AND day_of_week <= 6),
    CHECK(period IN ('morning', 'afternoon'))
);
```

**初期データ**:
```sql
INSERT INTO time_slots VALUES
('mon_am', 0, 'morning', '09:00', '12:30', 1, 2, '受付'),
('mon_pm', 0, 'afternoon', '15:30', '18:30', 1, 2, '受付'),
('tue_am', 1, 'morning', '09:00', '12:30', 1, 2, '受付'),
('tue_pm', 1, 'afternoon', '15:30', '18:30', 1, 2, '受付'),
('wed_am', 2, 'morning', '09:00', '12:30', 1, 2, '受付'),
('wed_pm', 2, 'afternoon', '15:30', '17:30', 1, 2, '受付'),
('thu_am', 3, 'morning', '09:00', '12:30', 1, 2, '受付'),
('fri_am', 4, 'morning', '09:00', '12:30', 1, 2, '受付'),
('fri_pm', 4, 'afternoon', '15:30', '18:30', 1, 2, '受付'),
('sat_am', 5, 'morning', '09:00', '13:30', 1, 2, '受付');
```

### 3.2 勤務可否テーブル（availability）の簡素化

**変更内容**: 時間帯IDを廃止し、日付単位での休暇登録に変更

```sql
-- V3.0 休暇登録テーブル
CREATE TABLE employee_absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    absence_date DATE NOT NULL,
    absence_type TEXT NOT NULL,  -- 'full_day', 'morning', 'afternoon'
    reason TEXT,                 -- 休暇理由（任意）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    UNIQUE(employee_id, absence_date, absence_type),
    CHECK(absence_type IN ('full_day', 'morning', 'afternoon'))
);
```

### 3.3 勤務形態マスタの拡張

**変更内容**: 勤務形態ごとの時間範囲を明確に定義

```sql
-- V3.0 勤務形態マスタ
CREATE TABLE employment_patterns (
    id TEXT PRIMARY KEY,              -- 'full_early', 'full_mid', 'full_late', etc.
    name TEXT NOT NULL,               -- 表示名
    category TEXT NOT NULL,           -- 'full_time', 'short_time', 'part_time'
    start_time TEXT NOT NULL,         -- 勤務開始時刻
    end_time TEXT NOT NULL,           -- 勤務終了時刻
    break_hours REAL NOT NULL,        -- 休憩時間（時間）
    work_hours REAL NOT NULL,         -- 実働時間（時間）
    can_work_afternoon BOOLEAN DEFAULT 1,  -- 午後勤務可否
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK(category IN ('full_time', 'short_time', 'part_time'))
);
```

**初期データ**:
```sql
INSERT INTO employment_patterns VALUES
('full_early', 'フルタイム（早番）', 'full_time', '08:30', '18:30', 2.0, 8.0, 1),
('full_mid', 'フルタイム（中番）', 'full_time', '08:45', '18:45', 2.0, 8.0, 1),
('full_late', 'フルタイム（遅番）', 'full_time', '09:00', '19:00', 2.0, 8.0, 1),
('short_time', '時短勤務', 'short_time', '08:45', '16:45', 1.0, 7.0, 0),
('part_morning', 'パート午前', 'part_time', '08:45', '12:45', 0.0, 4.0, 0),
('part_morning_ext', 'パート午前延長', 'part_time', '08:45', '13:45', 0.0, 5.0, 0);
```

### 3.4 職員マスタ（employees）の修正

**変更内容**: work_patternをemployment_patterns.idに関連付け

```sql
ALTER TABLE employees 
ADD COLUMN employment_pattern_id TEXT 
REFERENCES employment_patterns(id);

-- work_patternの廃止（employment_pattern_idに統合）
-- work_typeの廃止（employment_patterns.categoryから取得）
```

---

## 4. 機能要件の変更

### 4.1 時間帯設定ページの廃止

**変更内容**: 
- `2_⏰_時間帯設定.py` ページを削除
- 時間帯はシステム固定値として扱う
- 必要人数のみ設定画面から変更可能（オプション）

**代替機能**:
- ホーム画面に診療時間の一覧表示
- 「診療スケジュール確認」として読み取り専用で表示

### 4.2 勤務可能情報ページの改修

**ページ名変更**: `3_📅_勤務可能情報.py` → `3_🏖️_休暇管理.py`

**機能変更**:

#### 変更前
- カレンダー形式で各日の各時間帯の可否を登録
- 時間帯ごとのチェックボックス

#### 変更後
- カレンダー形式で休暇日を登録
- 各日付に対して以下を選択:
  - ✅ 勤務可能（デフォルト）
  - 🌅 午前休
  - 🌆 午後休
  - 🏖️ 終日休暇

**UI例**:
```
職員: 山田太郎（フルタイム・早番）

2025年12月カレンダー
┌────┬────┬────┬────┬────┬────┬────┐
│ 月 │ 火 │ 水 │ 木 │ 金 │ 土 │ 日 │
├────┼────┼────┼────┼────┼────┼────┤
│  1 │  2 │  3 │  4 │  5 │  6 │  7 │
│ ✅ │🏖️ │ ✅ │🌅 │ ✅ │ ✅ │ 休 │
├────┼────┼────┼────┼────┼────┼────┤
│  8 │  9 │ 10 │ 11 │ 12 │ 13 │ 14 │
│ ✅ │ ✅ │🌆 │ ✅ │ ✅ │ ✅ │ 休 │
└────┴────┴────┴────┴────┴────┴────┘

凡例:
✅ 勤務可能  🌅 午前休  🌆 午後休  🏖️ 終日休暇  休 定休日
```

### 4.3 シフト生成ロジックの修正

**変更内容**: 勤務可否判定ロジックの変更

```python
def is_available(employee, date, time_slot):
    """
    職員が指定日の指定時間帯に勤務可能かを判定
    
    判定順序:
    1. 曜日チェック（日曜日や休診日は全員不可）
    2. 休暇登録チェック（employee_absencesテーブル）
    3. 勤務形態チェック（employment_patternsの時間範囲）
    """
    # 1. 曜日・時間帯チェック
    if not time_slot.is_active:
        return False
    
    # 2. 休暇チェック
    absence = get_absence(employee.id, date)
    if absence:
        if absence.type == 'full_day':
            return False
        if absence.type == 'morning' and time_slot.period == 'morning':
            return False
        if absence.type == 'afternoon' and time_slot.period == 'afternoon':
            return False
    
    # 3. 勤務形態チェック
    pattern = get_employment_pattern(employee.employment_pattern_id)
    if time_slot.period == 'afternoon' and not pattern.can_work_afternoon:
        return False
    
    # 時間範囲チェック
    if time_slot.start_time < pattern.start_time:
        return False
    if time_slot.end_time > pattern.end_time:
        return False
    
    return True
```

### 4.4 職員管理ページの修正

**変更内容**: 勤務形態選択をemployment_patternsから選択

```python
# 勤務形態の選択（ドロップダウン）
patterns = get_all_employment_patterns()
employment_pattern = st.selectbox(
    "勤務形態",
    options=patterns,
    format_func=lambda p: f"{p['name']} ({p['start_time']}-{p['end_time']})"
)
```

---

## 5. サンプルデータ仕様

### 5.1 職員データ（5名）

| ID | 氏名 | 職員タイプ | 勤務形態 | リハ室 | 受付午前 | 受付午後 | 総合 |
|----|------|-----------|---------|--------|---------|---------|------|
| 1 | 山田太郎 | TYPE_A | フルタイム（早番） | 85 | 90 | 85 | 90 |
| 2 | 佐藤花子 | TYPE_A | フルタイム（中番） | 80 | 85 | 90 | 85 |
| 3 | 鈴木一郎 | TYPE_B | フルタイム（遅番） | 0 | 95 | 95 | 80 |
| 4 | 田中美咲 | TYPE_C | 時短勤務 | 90 | 0 | 0 | 75 |
| 5 | 高橋健太 | TYPE_D | パート午前 | 70 | 0 | 0 | 60 |

### 5.2 休暇データサンプル

2025年12月の休暇例:

| 職員 | 日付 | 休暇種別 | 理由 |
|------|------|---------|------|
| 山田太郎 | 2025-12-05 | 終日休暇 | 年次有給休暇 |
| 佐藤花子 | 2025-12-12 | 午前休 | 通院 |
| 鈴木一郎 | 2025-12-20 | 終日休暇 | 年次有給休暇 |
| 田中美咲 | 2025-12-25 | 終日休暇 | 年次有給休暇 |

---

## 6. マイグレーション要件

### 6.1 V2.0からV3.0へのマイグレーション

#### Phase 1: テーブル構造の変更
1. `employment_patterns` テーブルの作成
2. `time_slots` テーブルの再構築（固定データ投入）
3. `employee_absences` テーブルの作成
4. `employees` テーブルへの `employment_pattern_id` 追加

#### Phase 2: データ移行
1. 既存の `availability` データを `employee_absences` に変換
   - `is_available = 0` のレコードを休暇データに変換
   - 同一日の全時間帯が不可 → 終日休暇
   - 午前のみ不可 → 午前休
   - 午後のみ不可 → 午後休

2. 既存の `work_pattern` を `employment_pattern_id` にマッピング
   - P1 → full_early
   - P2 → full_mid
   - P3 → full_late
   - P4 → short_time
   - PT1 → part_morning
   - PT2 → part_morning_ext

#### Phase 3: 旧データの削除
1. `availability` テーブルの削除（バックアップ後）
2. `work_patterns` テーブルの削除（バックアップ後）
3. `employees` テーブルから `work_pattern`, `work_type` カラムの削除

### 6.2 バックアップとロールバック

**バックアップ戦略**:
- マイグレーション実行前に `shift.db` を `shift_v2_backup.db` として保存
- V2.0のプログラムファイルも別途保管

**ロールバック手順**:
1. アプリケーション停止
2. `shift.db` を削除
3. `shift_v2_backup.db` を `shift.db` にリネーム
4. V2.0のプログラムに戻す

---

## 7. 非機能要件

### 7.1 互換性
- Windows 10/11 対応
- Python 3.11+ 環境
- 既存のV2.0データベースからの自動マイグレーション

### 7.2 性能
- UI応答時間: 1秒以内（データベース操作）
- シフト生成時間: 1ヶ月分を30秒以内

### 7.3 ユーザビリティ
- カレンダーUIで直感的な休暇登録
- 誤操作防止のための確認ダイアログ
- 明確なエラーメッセージ

---

## 8. テスト要件

### 8.1 単体テスト
- [ ] 勤務可否判定ロジックのテスト
- [ ] 休暇登録・削除機能のテスト
- [ ] 勤務形態マスタの取得テスト
- [ ] 時間帯マスタの取得テスト

### 8.2 結合テスト
- [ ] シフト生成の全体フロー
- [ ] 休暇登録からシフト生成までの連携
- [ ] マイグレーション処理の検証

### 8.3 受け入れテスト
- [ ] 実際の休暇パターンでのシフト生成
- [ ] UI操作の使いやすさ確認
- [ ] V2.0データの正常移行確認

---

## 9. リリース計画

### 9.1 マイルストーン

| Phase | 内容 | 期間 |
|-------|------|------|
| Phase 1 | データベース設計・マイグレーション実装 | 2日 |
| Phase 2 | UIの改修（休暇管理ページ） | 2日 |
| Phase 3 | シフト生成ロジックの改修 | 2日 |
| Phase 4 | テストとバグ修正 | 2日 |
| Phase 5 | サンプルデータ投入・ドキュメント整備 | 1日 |

**合計**: 約9日間

### 9.2 リリース手順
1. V2.0の完全バックアップ
2. V3.0へのマイグレーション実行
3. サンプルデータ投入
4. 動作確認
5. ユーザーへの引き渡し

---

## 10. 付録

### 10.1 用語集

| 用語 | 説明 |
|------|------|
| 勤務形態 | フルタイム、時短、パートなどの勤務タイプ |
| 時間帯 | 診療時間の区分（午前・午後） |
| 休暇種別 | 終日休暇、午前休、午後休の区分 |
| 職員タイプ | TYPE_A〜Dの業務範囲分類 |

### 10.2 参照ドキュメント
- `SYSTEM_REQUIREMENTS_V2.md`: V2.0の要件定義
- `MIGRATION_PLAN_V2.md`: V1→V2マイグレーション実績
- `USER_GUIDE.md`: ユーザーマニュアル

---

**文書管理**
- 版数: 1.0
- 作成日: 2025-11-27
- 承認: 未承認
