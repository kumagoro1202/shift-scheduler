# シフト管理システム V2.0 改修実装計画

## 改修概要

現行システム（V1.0）を新要件に対応させるための段階的な改修計画。
4項目スキルスコア、勤務形態管理、休憩ローテーション機能を追加実装する。

---

## 改修スケジュール

| フェーズ | 期間目安 | 内容 | 優先度 |
|---------|---------|------|--------|
| Phase 1 | 2日 | データベーススキーマ拡張 | 高 |
| Phase 2 | 3日 | 職員管理機能の拡張 | 高 |
| Phase 3 | 2日 | 時間帯・勤務パターン管理 | 高 |
| Phase 4 | 4日 | 最適化エンジンの改修 | 高 |
| Phase 5 | 3日 | UI改修（シフト生成・表示） | 中 |
| Phase 6 | 2日 | 休憩ローテーション機能 | 中 |
| Phase 7 | 2日 | テスト・デバッグ | 高 |
| Phase 8 | 1日 | ドキュメント更新 | 中 |

**合計**: 約19日（約3週間）

---

## Phase 1: データベーススキーマ拡張（2日）

### 1.1 現状分析

**現在のテーブル構造:**
- `employees`: id, name, skill_score（単一）, is_active, created_at
- `time_slots`: id, name, start_time, end_time, required_employees, created_at
- `shifts`: id, date, time_slot_id, employee_id, created_at
- `availability`: id, employee_id, date, time_slot_id, is_available, created_at

### 1.2 実装タスク

#### タスク 1.1: employeesテーブル拡張（マイグレーション）

**ファイル**: `src/database.py`

```python
# 追加するカラム
ALTER TABLE employees ADD COLUMN employee_type TEXT DEFAULT 'TYPE_A' 
    CHECK(employee_type IN ('TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D'));
ALTER TABLE employees ADD COLUMN work_type TEXT DEFAULT 'フルタイム' 
    CHECK(work_type IN ('フルタイム', '時短勤務', 'パートタイム'));
ALTER TABLE employees ADD COLUMN work_pattern TEXT DEFAULT 'P1';
ALTER TABLE employees ADD COLUMN employment_type TEXT DEFAULT '正職員' 
    CHECK(employment_type IN ('正職員', 'パート'));

# 新しいスキルスコア（4項目）
ALTER TABLE employees ADD COLUMN skill_reha_room INTEGER DEFAULT 0 
    CHECK(skill_reha_room >= 0 AND skill_reha_room <= 100);
ALTER TABLE employees ADD COLUMN skill_reception_am INTEGER DEFAULT 0 
    CHECK(skill_reception_am >= 0 AND skill_reception_am <= 100);
ALTER TABLE employees ADD COLUMN skill_reception_pm INTEGER DEFAULT 0 
    CHECK(skill_reception_pm >= 0 AND skill_reception_pm <= 100);
ALTER TABLE employees ADD COLUMN skill_flexibility INTEGER DEFAULT 0 
    CHECK(skill_flexibility >= 0 AND skill_flexibility <= 100);

# 既存のskill_scoreは互換性のため残す（後で削除予定）
```

**マイグレーション関数:**
```python
def migrate_to_v2():
    """V1.0 → V2.0 へのデータ移行"""
    # 1. カラム追加
    # 2. 既存データの移行（skill_score → skill_reha_room）
    # 3. デフォルト値の設定
```

#### タスク 1.2: time_slotsテーブル拡張

```python
ALTER TABLE time_slots ADD COLUMN area_type TEXT DEFAULT '受付' 
    CHECK(area_type IN ('受付', 'リハ室'));
ALTER TABLE time_slots ADD COLUMN time_period TEXT 
    CHECK(time_period IN ('午前', '午後', '終日'));
ALTER TABLE time_slots ADD COLUMN required_employees_min INTEGER DEFAULT 1;
ALTER TABLE time_slots ADD COLUMN required_employees_max INTEGER DEFAULT 2;
ALTER TABLE time_slots ADD COLUMN target_skill_score INTEGER DEFAULT 150;
ALTER TABLE time_slots ADD COLUMN skill_weight REAL DEFAULT 1.0;

# required_employees は required_employees_max と同義として残す
```

#### タスク 1.3: 新規テーブル作成

**work_patternsテーブル:**
```python
CREATE TABLE work_patterns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    work_type TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    break_hours REAL NOT NULL,
    break_division INTEGER DEFAULT 1,
    work_hours REAL NOT NULL,
    employment_type TEXT NOT NULL
);
```

**break_schedulesテーブル:**
```python
CREATE TABLE break_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    date DATE NOT NULL,
    break_number INTEGER NOT NULL CHECK(break_number IN (1, 2)),
    break_start_time TEXT NOT NULL,
    break_end_time TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
```

#### タスク 1.4: マスタデータ投入

```python
# work_patterns の初期データ
INSERT INTO work_patterns VALUES
('P1', '基本パターン1', 'フルタイム', '08:30', '18:30', 2.0, 2, 8.0, '正職員'),
('P2', '基本パターン2', 'フルタイム', '08:45', '18:45', 2.0, 2, 8.0, '正職員'),
('P3', '基本パターン3', 'フルタイム', '09:00', '19:00', 2.0, 2, 8.0, '正職員'),
('P4', '時短勤務', '時短勤務', '08:45', '16:45', 1.0, 1, 7.0, '正職員'),
('PT1', '午前パート', 'パートタイム', '08:45', '12:45', 0.0, 0, 4.0, 'パート'),
('PT2', '午前延長パート', 'パートタイム', '08:45', '13:45', 0.0, 0, 5.0, 'パート');
```

### 1.3 実装ファイル

**新規作成:**
- `src/migration.py` - マイグレーションスクリプト

**修正:**
- `src/database.py` - テーブル定義の更新、CRUD関数の追加

### 1.4 テストポイント

- [ ] 既存データが正しく移行されるか
- [ ] 新しいカラムのデフォルト値が正しいか
- [ ] 制約条件が正しく機能するか
- [ ] マスタデータが正しく投入されるか

---

## Phase 2: 職員管理機能の拡張（3日）

### 2.1 データベース関数の追加・修正

**ファイル**: `src/database.py`

#### タスク 2.1: 職員CRUD関数の修正

```python
def create_employee(
    name: str,
    employee_type: str,
    work_type: str,
    work_pattern: str,
    employment_type: str,
    skill_reha_room: int,
    skill_reception_am: int,
    skill_reception_pm: int,
    skill_flexibility: int
) -> int:
    """職員を新規登録（V2対応）"""
    # 実装
```

```python
def update_employee(
    employee_id: int,
    name: str = None,
    employee_type: str = None,
    # ... 全パラメータ
) -> bool:
    """職員情報を更新（V2対応）"""
    # 実装
```

```python
def get_all_employees(include_inactive=False) -> List[Dict[str, Any]]:
    """全職員を取得（V2フィールド含む）"""
    # 既存関数の拡張
```

#### タスク 2.2: 勤務パターン管理関数

```python
def get_all_work_patterns() -> List[Dict[str, Any]]:
    """全勤務パターンを取得"""

def get_work_pattern_by_id(pattern_id: str) -> Optional[Dict[str, Any]]:
    """IDで勤務パターンを取得"""

def get_work_patterns_by_type(work_type: str) -> List[Dict[str, Any]]:
    """勤務形態で勤務パターンをフィルタ"""
```

### 2.2 UI実装（職員管理画面）

**ファイル**: `pages/1_👥_職員管理.py`

#### タスク 2.3: 職員登録フォームの拡張

**追加入力項目:**
1. 職員タイプ（selectbox）
2. 雇用形態（radio）
3. 勤務形態（selectbox）
4. 勤務パターン（selectbox - 勤務形態に連動）
5. スキルスコア4項目（number_input × 4）

**実装例:**
```python
with st.form("employee_form"):
    name = st.text_input("職員名", max_chars=50)
    
    col1, col2 = st.columns(2)
    with col1:
        employment_type = st.radio("雇用形態", ["正職員", "パート"])
    with col2:
        employee_type = st.selectbox(
            "職員タイプ",
            ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"],
            format_func=lambda x: {
                "TYPE_A": "リハ室・受付両方可能",
                "TYPE_B": "受付のみ",
                "TYPE_C": "リハ室のみ（正職員）",
                "TYPE_D": "リハ室のみ（パート）"
            }[x]
        )
    
    # 勤務形態の選択（雇用形態に連動）
    if employment_type == "正職員":
        work_type = st.selectbox("勤務形態", ["フルタイム", "時短勤務"])
    else:
        work_type = "パートタイム"
        st.info("パート職員は自動的に「パートタイム」になります")
    
    # 勤務パターンの選択（勤務形態に連動）
    patterns = get_work_patterns_by_type(work_type)
    work_pattern = st.selectbox(
        "勤務パターン",
        [p['id'] for p in patterns],
        format_func=lambda x: next(p['name'] for p in patterns if p['id'] == x)
    )
    
    # スキルスコア入力（4項目）
    st.subheader("スキルスコア（0〜100）")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skill_reha = st.number_input(
            "リハ室スキル",
            0, 100, 0,
            disabled=(employee_type == "TYPE_B")  # 受付のみは無効
        )
        skill_am = st.number_input(
            "受付午前スキル",
            0, 100, 0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"])  # リハのみは無効
        )
    with col_s2:
        skill_pm = st.number_input(
            "受付午後スキル",
            0, 100, 0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"])
        )
        skill_flex = st.number_input("総合対応力", 0, 100, 0)
    
    submitted = st.form_submit_button("登録")
```

#### タスク 2.4: 職員一覧表示の拡張

**表示項目追加:**
- 職員タイプ（アイコン表示）
- 勤務形態（バッジ表示）
- 勤務パターン
- スキルスコア4項目（レーダーチャート）

### 2.3 実装ファイル

**修正:**
- `src/database.py` - CRUD関数の拡張
- `pages/1_👥_職員管理.py` - UI全面改修

**新規作成:**
- `src/employee_utils.py` - 職員タイプ判定、スキル検証などのヘルパー関数

### 2.4 テストポイント

- [ ] 職員タイプに応じたスキルスコアの自動制御
- [ ] 雇用形態と勤務形態の連動
- [ ] 勤務形態と勤務パターンの連動
- [ ] 既存職員データの表示互換性
- [ ] バリデーション（必須項目、範囲チェック）

---

## Phase 3: 時間帯・勤務パターン管理（2日）

### 3.1 時間帯管理機能の拡張

**ファイル**: `pages/2_⏰_時間帯設定.py`

#### タスク 3.1: データベース関数

```python
def create_time_slot(
    name: str,
    area_type: str,
    time_period: str,
    start_time: str,
    end_time: str,
    required_employees_min: int,
    required_employees_max: int,
    target_skill_score: int,
    skill_weight: float
) -> int:
    """時間帯を新規登録（V2対応）"""

def update_time_slot(time_slot_id: int, **kwargs) -> bool:
    """時間帯を更新（V2対応）"""
```

#### タスク 3.2: UI実装

**追加入力項目:**
1. 業務エリア（ラジオボタン: リハ室 / 受付）
2. 時間区分（セレクトボックス: 午前 / 午後 / 終日）
3. 必要人数（最小・最大）
4. 目標スキルスコア
5. 重み係数

**実装例:**
```python
with st.form("timeslot_form"):
    name = st.text_input("時間帯名", placeholder="例: 受付午前")
    
    col1, col2 = st.columns(2)
    with col1:
        area_type = st.radio("業務エリア", ["リハ室", "受付"])
    with col2:
        time_period = st.selectbox("時間区分", ["午前", "午後", "終日"])
    
    # 時刻設定
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        start_time = st.time_input("開始時刻")
    with col_t2:
        end_time = st.time_input("終了時刻")
    
    # 必要人数
    st.subheader("必要人数")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        req_min = st.number_input("最小", 1, 10, 1)
    with col_r2:
        req_max = st.number_input("最大", 1, 10, 2)
    
    # 最適化パラメータ
    st.subheader("最適化設定")
    target_score = st.number_input("目標スキルスコア合計", 0, 1000, 150)
    skill_weight = st.slider("重み係数", 0.1, 5.0, 1.0, 0.1)
    
    submitted = st.form_submit_button("登録")
```

### 3.2 勤務パターン管理画面（新規）

**ファイル**: `pages/2-2_📋_勤務パターン.py`（新規）

#### タスク 3.3: 勤務パターン管理UI

**機能:**
- 勤務パターン一覧表示
- 新規勤務パターン追加（管理者向け）
- 既存パターンの編集・削除

**実装:**
```python
st.title("📋 勤務パターン管理")

patterns = get_all_work_patterns()

for pattern in patterns:
    with st.expander(f"{pattern['name']} ({pattern['id']})"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**勤務形態**: {pattern['work_type']}")
            st.write(f"**雇用形態**: {pattern['employment_type']}")
        with col2:
            st.write(f"**勤務時間**: {pattern['start_time']} 〜 {pattern['end_time']}")
            st.write(f"**休憩**: {pattern['break_hours']}時間")
        with col3:
            st.write(f"**実働**: {pattern['work_hours']}時間")
            st.write(f"**休憩分割**: {pattern['break_division']}回")
```

### 3.3 実装ファイル

**修正:**
- `src/database.py` - 時間帯CRUD関数の拡張
- `pages/2_⏰_時間帯設定.py` - UI拡張

**新規作成:**
- `pages/2-2_📋_勤務パターン.py` - 勤務パターン管理画面

### 3.4 テストポイント

- [ ] 時間帯の新規登録・編集・削除
- [ ] 業務エリアと時間区分の組み合わせ
- [ ] 必要人数の範囲チェック
- [ ] 勤務パターンの一覧表示

---

## Phase 4: 最適化エンジンの改修（4日）

### 4.1 最適化ロジックの再設計

**ファイル**: `src/optimizer.py`

#### タスク 4.1: スキルスコア計算の変更

**従来（V1.0）:**
```python
# 単一のskill_scoreを使用
total_skill = sum(emp['skill_score'] for emp in assigned_employees)
```

**新方式（V2.0）:**
```python
# 時間帯の業務エリアに応じたスキルスコアを使用
def calculate_skill_score(employees, time_slot):
    """時間帯に適したスキルスコアを計算"""
    if time_slot['area_type'] == 'リハ室':
        return sum(emp['skill_reha_room'] for emp in employees)
    elif time_slot['area_type'] == '受付':
        if time_slot['time_period'] == '午前':
            return sum(emp['skill_reception_am'] for emp in employees)
        elif time_slot['time_period'] == '午後':
            return sum(emp['skill_reception_pm'] for emp in employees)
    return 0
```

#### タスク 4.2: 制約条件の追加

**新制約1: 職員タイプとエリアの整合性**
```python
def can_assign_to_area(employee, time_slot):
    """職員が時間帯に配置可能かチェック"""
    area_type = time_slot['area_type']
    emp_type = employee['employee_type']
    
    if area_type == 'リハ室':
        # リハ室にはTYPE_A, TYPE_C, TYPE_Dのみ
        if emp_type not in ['TYPE_A', 'TYPE_C', 'TYPE_D']:
            return False
        # リハ室スキルが0以下は不可
        if employee['skill_reha_room'] <= 0:
            return False
    
    elif area_type == '受付':
        # 受付にはTYPE_A, TYPE_Bのみ
        if emp_type not in ['TYPE_A', 'TYPE_B']:
            return False
        # 受付スキルが0以下は不可
        if employee['skill_reception_am'] <= 0 and employee['skill_reception_pm'] <= 0:
            return False
    
    return True
```

**新制約2: パート職員出勤時の特殊ルール**
```python
def apply_part_time_rule(date, shifts_for_date):
    """
    パート（TYPE_D）が出勤する日の特殊処理
    
    ルール:
    - TYPE_Dがリハ室に配置される日は、
    - TYPE_Aの職員1名が受付をサポート
    """
    # TYPE_Dの出勤チェック
    has_type_d = any(
        s['employee']['employee_type'] == 'TYPE_D' 
        for s in shifts_for_date
    )
    
    if has_type_d:
        # リハ室: TYPE_C or TYPE_A (1名) + TYPE_D (1名)
        # 受付: TYPE_A (1名) または TYPE_B (1名)
        # → TYPE_Aの2名のうち1名は受付へ
        pass  # 実装
```

#### タスク 4.3: 目的関数の変更

**従来（V1.0）:**
```python
# 全時間帯で均等化
Minimize: Σ |actual_skill - avg_skill|
```

**新方式（V2.0）:**
```python
# 時間帯ごとの重み付け + 目標値との差分
def objective_function(shifts):
    """
    目的関数: 各時間帯のスキルスコアを目標値に近づける
    """
    total_deviation = 0
    
    for time_slot in time_slots:
        # 時間帯のシフトを取得
        shifts_in_slot = [s for s in shifts if s['time_slot_id'] == time_slot['id']]
        
        # 実際のスキルスコア計算
        actual_score = calculate_skill_score(
            [s['employee'] for s in shifts_in_slot],
            time_slot
        )
        
        # 目標値との差分（重み付き）
        target_score = time_slot['target_skill_score']
        weight = time_slot['skill_weight']
        
        deviation = weight * abs(actual_score - target_score)
        total_deviation += deviation
    
    return total_deviation
```

#### タスク 4.4: グリーディアルゴリズムの改良

```python
def generate_shift_v2(
    employees: List[Dict],
    time_slots: List[Dict],
    start_date: str,
    end_date: str,
    availability_func=None
) -> Optional[List[Dict]]:
    """
    シフト生成（V2.0）
    
    改良点:
    1. 4項目スキルスコア対応
    2. 職員タイプ制約
    3. パート職員特殊ルール
    4. 重み付き最適化
    """
    # 実装
```

### 4.2 実装ファイル

**修正:**
- `src/optimizer.py` - 最適化ロジック全面改修

**新規作成:**
- `src/optimizer_v2.py` - 新しい最適化エンジン（V1と並行運用）
- `src/constraint_checker.py` - 制約条件チェック関数群

### 4.3 テストポイント

- [ ] スキルスコア計算の正確性（4項目）
- [ ] 職員タイプ制約の検証
- [ ] パート職員特殊ルールの動作
- [ ] 目標値との差分最小化
- [ ] 実行時間（1ヶ月分30秒以内）

---

## Phase 5: UI改修（シフト生成・表示）（3日）

### 5.1 シフト生成画面の改修

**ファイル**: `pages/4_🎯_シフト生成.py`

#### タスク 5.1: 最適化モード選択

```python
st.subheader("最適化設定")

col1, col2 = st.columns(2)
with col1:
    optimization_mode = st.selectbox(
        "最適化モード",
        ["バランス", "スキル重視", "日数重視"],
        help="""
        - バランス: スキルと日数の両方を考慮
        - スキル重視: スキルバランスを最優先
        - 日数重視: 勤務日数の均等化を優先
        """
    )

with col2:
    prioritize_parttime = st.checkbox(
        "パート職員の優先配置",
        value=True,
        help="パート職員の出勤可能日を優先的にシフトに組み込む"
    )
```

#### タスク 5.2: 生成結果のプレビュー拡張

```python
# スキルスコア内訳表示
st.subheader("📊 スキルスコア内訳")

for time_slot in time_slots:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.write(f"**{time_slot['name']}**")
    
    with col2:
        actual_score = calculate_actual_score(shifts, time_slot)
        target_score = time_slot['target_skill_score']
        st.metric("実スコア", actual_score)
    
    with col3:
        deviation = abs(actual_score - target_score)
        color = "🟢" if deviation <= 20 else "🟡" if deviation <= 40 else "🔴"
        st.metric("目標差分", f"{color} {deviation}")
```

### 5.2 シフト表示画面の改修

**ファイル**: `pages/5_📋_シフト表示.py`

#### タスク 5.3: 職員情報の詳細表示

```python
# 職員ごとのシフト表示
for shift in shifts_on_date:
    emp = shift['employee']
    ts = shift['time_slot']
    
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
    with col1:
        # 職員名 + タイプアイコン
        type_icon = {
            'TYPE_A': '🔄',  # 両方可能
            'TYPE_B': '📞',  # 受付のみ
            'TYPE_C': '🏥',  # リハのみ（正職員）
            'TYPE_D': '🏥👤' # リハのみ（パート）
        }
        st.write(f"{type_icon[emp['employee_type']]} **{emp['name']}**")
    
    with col2:
        # 勤務形態バッジ
        work_type_color = {
            'フルタイム': 'blue',
            '時短勤務': 'green',
            'パートタイム': 'orange'
        }
        st.markdown(
            f"<span style='background-color: {work_type_color[emp['work_type']]}; "
            f"padding: 2px 8px; border-radius: 4px; color: white;'>"
            f"{emp['work_type']}</span>",
            unsafe_allow_html=True
        )
    
    with col3:
        st.write(f"{ts['name']}")
    
    with col4:
        # 勤務パターン
        st.write(f"`{emp['work_pattern']}`")
```

#### タスク 5.4: スキルスコア可視化

```python
import plotly.graph_objects as go

# レーダーチャート: 時間帯別スキルスコア
fig = go.Figure()

for time_slot in time_slots:
    actual_scores = []
    for date in dates:
        score = calculate_score_for_date_slot(date, time_slot)
        actual_scores.append(score)
    
    fig.add_trace(go.Scatterpolar(
        r=actual_scores,
        theta=[f"{i+1}日" for i in range(len(dates))],
        fill='toself',
        name=time_slot['name']
    ))

fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 300])),
    showlegend=True
)

st.plotly_chart(fig, use_container_width=True)
```

### 5.3 実装ファイル

**修正:**
- `pages/4_🎯_シフト生成.py` - 最適化設定UI追加
- `pages/5_📋_シフト表示.py` - 表示内容の大幅拡張

**新規作成:**
- `src/visualization.py` - グラフ生成関数

### 5.4 テストポイント

- [ ] 最適化モードの切り替え
- [ ] スキルスコア内訳の正確性
- [ ] 職員情報の表示（タイプ、勤務形態）
- [ ] グラフ表示の正確性

---

## Phase 6: 休憩ローテーション機能（2日）

### 6.1 休憩時間自動割り当て

**ファイル**: `src/break_scheduler.py`（新規）

#### タスク 6.1: 休憩時間計算ロジック

```python
def assign_break_times(shifts_on_date: List[Dict], time_slots: List[Dict]) -> List[Dict]:
    """
    1日分のシフトに対して休憩時間を自動割り当て
    
    制約:
    1. 受付窓口には常に2名以上が実働
    2. フルタイム: 1時間×2回の休憩
    3. 時短勤務: 1時間×1回の休憩
    4. パート: 休憩なし
    5. 休憩時間は11:00-14:00の間で分散
    
    Returns:
        休憩スケジュールのリスト
    """
    break_schedules = []
    
    # 受付に配置されている職員を抽出
    reception_staff = [
        s for s in shifts_on_date 
        if s['time_slot']['area_type'] == '受付'
    ]
    
    # 各職員の勤務パターンを取得
    for shift in reception_staff:
        emp = shift['employee']
        pattern = get_work_pattern_by_id(emp['work_pattern'])
        
        if pattern['break_hours'] == 0:
            continue  # パートは休憩なし
        
        # 休憩時間帯の候補を生成
        break_slots = generate_break_slots(
            pattern['break_hours'],
            pattern['break_division']
        )
        
        # 他の職員と重複しないよう調整
        assigned_breaks = assign_non_overlapping_breaks(
            emp, break_slots, break_schedules, reception_staff
        )
        
        break_schedules.extend(assigned_breaks)
    
    return break_schedules
```

#### タスク 6.2: 窓口常駐人数チェック

```python
def validate_reception_coverage(
    shifts_on_date: List[Dict],
    break_schedules: List[Dict]
) -> bool:
    """
    受付窓口の常駐人数が常に2名以上であることを検証
    
    Returns:
        True: 制約を満たす / False: 制約違反
    """
    # 業務時間を15分刻みで分割
    time_intervals = generate_time_intervals("08:30", "19:00", 15)
    
    for interval in time_intervals:
        # この時間帯に実働している職員数をカウント
        working_count = count_working_staff(
            interval, shifts_on_date, break_schedules
        )
        
        if working_count < 2:
            print(f"⚠️ {interval}: 窓口人数不足 ({working_count}名)")
            return False
    
    return True
```

### 6.2 UI実装

**ファイル**: `pages/5_📋_シフト表示.py`

#### タスク 6.3: 休憩時間の表示

```python
# 日別表示に休憩時間を追加
st.subheader(f"{selected_date} の休憩時間")

# タイムライン表示
for shift in shifts_on_date:
    emp = shift['employee']
    
    # 休憩スケジュールを取得
    breaks = get_break_schedules_for_shift(shift['id'])
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.write(f"**{emp['name']}**")
    
    with col2:
        # タイムライン（Ganttチャート風）
        timeline_html = generate_timeline_html(
            emp, shift['time_slot'], breaks
        )
        st.markdown(timeline_html, unsafe_allow_html=True)

# 窓口常駐人数グラフ
st.subheader("受付窓口 実働人数")
coverage_chart = plot_reception_coverage(selected_date)
st.plotly_chart(coverage_chart, use_container_width=True)
```

#### タスク 6.4: 休憩時間の手動調整

```python
# 管理者向け: 休憩時間の手動調整機能
with st.expander("🔧 休憩時間を手動調整"):
    st.warning("⚠️ 手動調整後は窓口常駐人数の制約を満たすことを確認してください")
    
    for break_schedule in break_schedules:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.write(break_schedule['employee_name'])
        
        with col2:
            new_start = st.time_input(
                "開始",
                value=parse_time(break_schedule['break_start_time']),
                key=f"break_start_{break_schedule['id']}"
            )
        
        with col3:
            new_end = st.time_input(
                "終了",
                value=parse_time(break_schedule['break_end_time']),
                key=f"break_end_{break_schedule['id']}"
            )
        
        with col4:
            if st.button("更新", key=f"update_break_{break_schedule['id']}"):
                update_break_schedule(
                    break_schedule['id'],
                    new_start.strftime("%H:%M"),
                    new_end.strftime("%H:%M")
                )
                st.success("更新しました")
                st.rerun()
```

### 6.3 実装ファイル

**新規作成:**
- `src/break_scheduler.py` - 休憩時間自動割り当てロジック

**修正:**
- `src/database.py` - break_schedulesテーブルのCRUD関数追加
- `pages/5_📋_シフト表示.py` - 休憩時間表示機能追加

### 6.4 テストポイント

- [ ] 休憩時間の自動割り当て（重複なし）
- [ ] 窓口常駐人数が常に2名以上
- [ ] フルタイム・時短・パートの休憩時間の違い
- [ ] 手動調整機能の動作
- [ ] タイムライン表示の正確性

---

## Phase 7: テスト・デバッグ（2日）

### 7.1 単体テスト

**ファイル**: `tests/test_v2_features.py`（新規）

#### タスク 7.1: テストケース作成

```python
import pytest
from src.database import *
from src.optimizer_v2 import *
from src.break_scheduler import *

class TestEmployeeManagement:
    """職員管理機能のテスト"""
    
    def test_create_employee_v2(self):
        """職員登録（V2）のテスト"""
        emp_id = create_employee(
            name="テスト太郎",
            employee_type="TYPE_A",
            work_type="フルタイム",
            work_pattern="P1",
            employment_type="正職員",
            skill_reha_room=80,
            skill_reception_am=70,
            skill_reception_pm=90,
            skill_flexibility=75
        )
        assert emp_id > 0
        
        emp = get_employee_by_id(emp_id)
        assert emp['name'] == "テスト太郎"
        assert emp['skill_reha_room'] == 80
    
    def test_employee_type_skill_constraint(self):
        """職員タイプとスキルの整合性テスト"""
        # TYPE_B（受付のみ）はリハ室スキルが0であること
        pass

class TestOptimizer:
    """最適化エンジンのテスト"""
    
    def test_skill_score_calculation(self):
        """スキルスコア計算のテスト"""
        pass
    
    def test_employee_type_constraint(self):
        """職員タイプ制約のテスト"""
        pass
    
    def test_parttime_special_rule(self):
        """パート職員特殊ルールのテスト"""
        pass

class TestBreakScheduler:
    """休憩ローテーション機能のテスト"""
    
    def test_break_assignment(self):
        """休憩時間割り当てのテスト"""
        pass
    
    def test_reception_coverage(self):
        """窓口常駐人数チェックのテスト"""
        pass
```

### 7.2 統合テスト

#### タスク 7.2: エンドツーエンドテスト

```python
def test_full_shift_generation_v2():
    """シフト生成〜表示までの統合テスト"""
    
    # 1. サンプルデータ投入
    setup_sample_data_v2()
    
    # 2. 勤務可能情報登録
    register_availability()
    
    # 3. シフト生成
    shifts = generate_shift_v2(...)
    assert shifts is not None
    assert len(shifts) > 0
    
    # 4. 休憩時間割り当て
    break_schedules = assign_break_times(...)
    assert len(break_schedules) > 0
    
    # 5. 制約チェック
    assert validate_all_constraints(shifts, break_schedules)
    
    # 6. スキルスコア検証
    for time_slot in time_slots:
        actual = calculate_skill_score(...)
        target = time_slot['target_skill_score']
        assert abs(actual - target) <= 50  # 許容範囲
```

### 7.3 パフォーマンステスト

#### タスク 7.3: 実行時間測定

```python
import time

def test_performance():
    """パフォーマンステスト（1ヶ月分30秒以内）"""
    
    start_time = time.time()
    
    shifts = generate_shift_v2(
        employees=get_all_employees(),
        time_slots=get_all_time_slots(),
        start_date="2025-12-01",
        end_date="2025-12-31"
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"実行時間: {elapsed_time:.2f}秒")
    assert elapsed_time < 30.0  # 30秒以内
```

### 7.4 実装ファイル

**新規作成:**
- `tests/test_v2_features.py` - V2機能のテストケース
- `tests/test_integration_v2.py` - 統合テスト
- `scripts/setup_sample_data_v2.py` - V2用サンプルデータ

### 7.5 テストポイント

- [ ] 全単体テストがパス
- [ ] 統合テストがパス
- [ ] パフォーマンステストがパス
- [ ] 既存機能との互換性確認
- [ ] エラーハンドリングの確認

---

## Phase 8: ドキュメント更新（1日）

### 8.1 更新対象ドキュメント

#### タスク 8.1: ユーザーガイド更新

**ファイル**: `docs/USER_GUIDE.md`

**追加内容:**
- V2の新機能説明
- 4項目スキルスコアの入力方法
- 職員タイプの選択方法
- 勤務形態・勤務パターンの設定
- 休憩ローテーションの確認方法

#### タスク 8.2: システム設計書更新

**ファイル**: `docs/ARCHITECTURE.md`

**更新内容:**
- データベーススキーマの変更点
- 最適化アルゴリズムの改良点
- 新しい制約条件の説明

#### タスク 8.3: 実装計画更新

**ファイル**: `docs/IMPLEMENTATION_PLAN.md`

**更新内容:**
- V2.0の実装状況を反映
- 完了項目のチェック
- 今後の改善予定の更新

#### タスク 8.4: README更新

**ファイル**: `README.md`

**更新内容:**
- V2.0の新機能紹介
- インストール手順の確認
- スクリーンショットの更新

### 8.2 実装ファイル

**修正:**
- `docs/USER_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `README.md`

**新規作成:**
- `docs/MIGRATION_GUIDE_V1_TO_V2.md` - マイグレーションガイド
- `docs/API_REFERENCE.md` - 関数リファレンス（開発者向け）

---

## データ移行戦略

### 既存データの扱い

#### オプション1: 自動マイグレーション（推奨）

```python
def migrate_existing_data():
    """
    V1.0 のデータを V2.0 形式に自動変換
    
    変換ルール:
    - skill_score → skill_reha_room（デフォルト）
    - employee_type → TYPE_A（デフォルト）
    - work_type → フルタイム（デフォルト）
    - work_pattern → P1（デフォルト）
    """
    employees = get_all_employees()
    
    for emp in employees:
        # 既存のskill_scoreをリハ室スキルに設定
        update_employee(
            emp['id'],
            employee_type='TYPE_A',
            work_type='フルタイム',
            work_pattern='P1',
            employment_type='正職員',
            skill_reha_room=emp['skill_score'],
            skill_reception_am=emp['skill_score'] // 2,  # 仮の値
            skill_reception_pm=emp['skill_score'] // 2,
            skill_flexibility=emp['skill_score'] // 2
        )
```

#### オプション2: 手動設定を促す

- マイグレーション実行後、ユーザーに手動で職員情報を更新してもらう
- 画面上に「V2対応が必要です」の警告を表示

### バックアップ戦略

```python
def backup_database_before_migration():
    """マイグレーション前のデータベースバックアップ"""
    import shutil
    from datetime import datetime
    
    backup_path = f"shift_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ バックアップ完了: {backup_path}")
```

---

## リスク管理

### 主要リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| 既存データの破損 | 高 | マイグレーション前に必ずバックアップ |
| 最適化エンジンのパフォーマンス低下 | 中 | 並行テストで性能測定、必要に応じてアルゴリズム見直し |
| UI/UX の複雑化 | 中 | ユーザーテストを実施、フィードバック反映 |
| 休憩ローテーション制約が満たせない | 中 | 制約緩和オプションを用意 |
| 既存機能の互換性 | 低 | V1モードを残して段階的移行 |

### 段階的リリース計画

#### ステップ1: 内部テスト版（Alpha）
- Phase 1〜4 完了時点
- 開発環境でのみ動作確認

#### ステップ2: ユーザーテスト版（Beta）
- Phase 1〜6 完了時点
- 限定ユーザーにテスト依頼

#### ステップ3: 本番リリース（V2.0）
- 全Phase完了
- ドキュメント整備完了
- 正式リリース

---

## 開発環境セットアップ

### V2開発用ブランチ作成

```powershell
# 新ブランチ作成
git checkout -b feature/v2-upgrade

# 作業開始
git add .
git commit -m "Start V2.0 upgrade"
```

### 依存パッケージの追加

**requirements.txt に追加:**
```txt
# 既存
streamlit==1.28.0
pandas==2.1.0
pulp==2.7.0
openpyxl==3.1.0
plotly==5.17.0
python-dateutil==2.8.2

# V2で追加（必要に応じて）
numpy==1.25.0  # 数値計算
pytest==7.4.0  # テスト
```

---

## 実装チェックリスト

### Phase 1: データベース
- [ ] employeesテーブル拡張
- [ ] time_slotsテーブル拡張
- [ ] work_patternsテーブル作成
- [ ] break_schedulesテーブル作成
- [ ] マイグレーションスクリプト作成
- [ ] マスタデータ投入

### Phase 2: 職員管理
- [ ] CRUD関数の拡張
- [ ] 職員登録フォーム改修
- [ ] 職員一覧表示改修
- [ ] スキルスコア4項目入力
- [ ] 職員タイプ自動制御

### Phase 3: 時間帯管理
- [ ] 時間帯CRUD関数拡張
- [ ] 時間帯設定画面改修
- [ ] 勤務パターン管理画面作成

### Phase 4: 最適化エンジン
- [ ] スキルスコア計算変更
- [ ] 職員タイプ制約追加
- [ ] パート特殊ルール実装
- [ ] 目的関数変更
- [ ] グリーディアルゴリズム改良

### Phase 5: UI改修
- [ ] シフト生成画面改修
- [ ] 最適化モード選択
- [ ] シフト表示画面改修
- [ ] スキルスコア可視化

### Phase 6: 休憩ローテーション
- [ ] 休憩時間自動割り当て
- [ ] 窓口常駐人数チェック
- [ ] 休憩時間表示UI
- [ ] 手動調整機能

### Phase 7: テスト
- [ ] 単体テスト作成
- [ ] 統合テスト実施
- [ ] パフォーマンステスト
- [ ] バグ修正

### Phase 8: ドキュメント
- [ ] ユーザーガイド更新
- [ ] システム設計書更新
- [ ] README更新
- [ ] マイグレーションガイド作成

---

## 完了基準

### 必須要件
- ✅ 4項目スキルスコアが正しく機能
- ✅ 職員タイプ制約が正しく動作
- ✅ パート職員特殊ルールが動作
- ✅ 休憩ローテーションが正しく割り当てられる
- ✅ 窓口常駐人数が常に2名以上
- ✅ 既存データが正しく移行される
- ✅ 全テストがパス
- ✅ ドキュメントが更新される

### 推奨要件
- ✅ 実行時間が30秒以内
- ✅ UI/UXが直感的
- ✅ エラーメッセージが分かりやすい
- ✅ ヘルプドキュメントが充実

---

## 今後の拡張予定（V2.1以降）

### 高優先度
- [ ] データバックアップ・リストア機能
- [ ] PDF形式でのシフト表出力
- [ ] 詳細なログ記録

### 中優先度
- [ ] 職員の連続勤務日数制限
- [ ] 月次レポート機能
- [ ] ダークモード対応

### 低優先度
- [ ] マルチユーザー対応
- [ ] クラウド同期機能
- [ ] スマートフォン対応

---

**ドキュメント作成日**: 2025年11月27日  
**対象バージョン**: V2.0  
**想定期間**: 約3週間（19日）
