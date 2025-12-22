# シフト生成アルゴリズム詳細解説

**バージョン**: 0.0.3  
**最終更新日**: 2025年12月22日

---

## 目次

1. [概要](#1-概要)
2. [アルゴリズムの全体構造](#2-アルゴリズムの全体構造)
3. [職員の可用性評価](#3-職員の可用性評価)
4. [職員の選択戦略](#4-職員の選択戦略)
5. [時間帯処理とシフト生成](#5-時間帯処理とシフト生成)
6. [制約条件の検証](#6-制約条件の検証)
7. [休憩時間の自動割り当て](#7-休憩時間の自動割り当て)
8. [エラーハンドリングと診断](#8-エラーハンドリングと診断)
9. [最適化戦略の比較](#9-最適化戦略の比較)
10. [アルゴリズムの計算量](#10-アルゴリズムの計算量)

---

## 1. 概要

### 1.1 目的

診療所における職員のシフトを自動生成し、以下の目標を達成します：

1. **スキルバランスの均一化**: 各時間帯に配置される職員のスキル能力を平均化し、日によってサービス品質が変動しないようにする
2. **勤務回数の公平化**: 職員の勤務日数を均等に配分し、特定の職員への負担集中を防ぐ
3. **制約条件の遵守**: 休暇、勤務形態、職員タイプなどの各種制約を厳格に守る
4. **医事能力の優先**: 受付業務では医事業務（保険登録、会計など）の能力を優先して配置し、事務スキルの高い職員を優先的に選択する

### 1.2 アルゴリズムの特徴

- **ヒューリスティック手法**: 最適解の探索ではなく、実用的な良解を高速に求める
- **グリーディアプローチ**: 1日ずつ、1時間帯ずつ順次処理していく逐次割り当て方式
- **多様な最適化モード**: バランス重視、スキル重視、日数重視の3つのモードを提供
- **詳細なエラー診断**: 割り当てに失敗した場合、原因を詳細に報告

---

## 2. アルゴリズムの全体構造

### 2.1 メイン処理フロー

```
generate_shifts(employees, time_slots, start_date, end_date, optimisation_mode)
    ↓
入力検証 (_validate_shift_inputs)
    ↓
初期化（勤務カウンター、スケジュール配列）
    ↓
日付ループ（start_date → end_date）
    ↓
    その日の時間帯を取得
    ↓
    1日分の処理 (_process_daily_slots)
        ↓
        午前時間帯の処理
        ↓
        午後時間帯の処理（午前勤務者を優先活用）
        ↓
        パートタイム制約の検証
    ↓
完成したシフトを返す
```

### 2.2 データ構造

#### 主要な入力データ

```python
# 職員情報
Employee {
    id: int
    name: str
    employee_type: str  # TYPE_A～TYPE_F
    skill_reha: int     # リハ室スキル (0-100)
    skill_reception_am: int  # 受付午前スキル (0-100)
    skill_reception_pm: int  # 受付午後スキル (0-100)
    skill_general: int  # 総合対応力 (0-100)
    employment_pattern_id: str  # 勤務形態ID
}

# 時間帯情報
TimeSlot {
    id: str
    day_of_week: int    # 0=月曜, 6=日曜
    period: str         # "morning" or "afternoon"
    start_time: str     # "HH:MM"
    end_time: str       # "HH:MM"
    area: str           # "リハ室" or "受付"
    required_staff: int # 必要人数
    target_skill_score: int  # 目標スキルスコア
    is_active: bool     # 有効/無効
}
```

#### 生成されるシフト

```python
GeneratedShift {
    date: str           # "YYYY-MM-DD"
    time_slot_id: str
    employee_id: int
    employee_name: str
    time_slot_name: str
    start_time: str
    end_time: str
    skill_score: int    # この配置でのスキルスコア
    employee: Employee  # 参照
    time_slot: TimeSlot # 参照
}
```

### 2.3 処理の粒度

アルゴリズムは以下の階層で処理を行います：

1. **期間レベル**: 指定された期間全体（開始日～終了日）
2. **日レベル**: 各日ごとに処理
3. **時間帯レベル**: 各時間帯ごとに職員を割り当て
4. **職員レベル**: 個々の職員の可用性を評価し選択

---

## 3. 職員の可用性評価

### 3.1 可用性判定の流れ

職員が特定の日・時間帯に勤務可能かどうかを多段階でチェックします。

```
is_employee_available(employee, date_str, time_slot)
    ↓
【ステップ1】基本的な時間帯チェック
    - 時間帯が有効か (is_active)
    - 日曜日でないか
    - 曜日が一致するか
    ↓
【ステップ2】休暇チェック
    - 終日休暇でないか
    - 午前休と午前時間帯が重複していないか
    - 午後休と午後時間帯が重複していないか
    ↓
【ステップ3】勤務形態チェック
    - 午後勤務可能な形態か
    - 勤務開始時刻より前でないか
    - 勤務終了時刻より後でないか
    ↓
【ステップ4】エリア配置可否チェック
    - 職員タイプがエリアに適合するか
    - 必要なスキルを持っているか
    ↓
利用可能 / 不可能
```

### 3.2 エリア配置ルール

職員タイプとエリアの対応：

| 職員タイプ | リハ室 | 受付 | 条件 |
|-----------|--------|------|------|
| TYPE_A | ✓ | ✓ | オールラウンダー（両方可能） |
| TYPE_B | ✗ | ✓ | 受付専任（正職員・パート共通） |
| TYPE_C | ✓ | ✗ | リハ室専任（正職員） |
| TYPE_D | ✓ | ✗ | リハ室専任（パート） |
| TYPE_E | ✗ | ✓ | 受付専任（パート） |
| TYPE_F | ✗ | ✓ | 受付専任（時短） |
| TYPE_E | ✗ | ✓ | 受付専任（パート） |
| TYPE_F | ✗ | ✓ | 受付専任（時短） |

```python
def _can_assign_to_area(employee: Employee, time_slot: TimeSlot) -> bool:
    if time_slot.area == "リハ室":
        if employee.employee_type not in {"TYPE_A", "TYPE_C", "TYPE_D"}:
            return False
        return employee.skill_reha > 0
    
    if time_slot.area == "受付":
        if employee.employee_type not in {"TYPE_A", "TYPE_B", "TYPE_E", "TYPE_F"}:
            return False
        return employee.skill_reception_am > 0 or employee.skill_reception_pm > 0
    
    return True
```

### 3.3 二重割り当て防止

同じ日の重複する時間帯に同一職員を割り当てないようチェックします：

```python
# 既に生成済みのシフトと時間が重複していないか確認
conflict = any(
    s.employee_id == employee.id 
    and s.date == date_str 
    and check_time_overlap(slot, s.time_slot)
    for s in schedule
)
```

時間重複判定：

```python
def check_time_overlap(slot_a: TimeSlot, slot_b: TimeSlot) -> bool:
    """2つの時間帯が重複するかどうかを判定"""
    start_a = _time_to_minutes(slot_a.start_time)  # 分単位に変換
    end_a = _time_to_minutes(slot_a.end_time)
    start_b = _time_to_minutes(slot_b.start_time)
    end_b = _time_to_minutes(slot_b.end_time)
    
    # 日をまたぐ場合の処理（例: 18:00-翌02:00）
    if end_a < start_a:
        end_a += 24 * 60
    if end_b < start_b:
        end_b += 24 * 60
    
    # 重複なし: 一方が終わってからもう一方が始まる
    return not (end_a <= start_b or end_b <= start_a)
```

---

## 4. 職員の選択戦略

### 4.1 スキルスコアの計算

職員が特定の時間帯に配置されたときのスキルスコアを計算します：

```python
def calculate_skill_score(employee: Employee, time_slot: TimeSlot) -> int:
    """職員のその時間帯でのスキルスコアを計算"""
    general = employee.skill_general
    
    if time_slot.area == "リハ室":
        return employee.skill_reha + general
    
    if time_slot.area == "受付":
        if time_slot.period == "morning":
            return employee.skill_reception_am + general
        if time_slot.period == "afternoon":
            return employee.skill_reception_pm + general
        # 期間指定なしの場合は平均
        return ((employee.skill_reception_am + employee.skill_reception_pm) // 2) + general
    
    return general
```

**スキルスコアの構成**:
- リハ室: `リハ室スキル + 総合対応力`
- 受付（午前）: `受付午前スキル（医事能力優先） + 総合対応力`
- 受付（午後）: `受付午後スキル（医事能力優先） + 総合対応力`

**注**: 受付業務では医事業務（保険登録、会計など）の能力を優先して評価します。スキルスコアが同程度の場合、医事能力の高い職員を優先的に配置します。

### 4.2 3つの最適化モード

#### モード1: 日数重視 (`days`)

**目的**: 勤務日数を最も均等に配分する

```python
def _select_by_workday_count(candidates, count, work_count):
    """勤務日数が最も少ない職員から選択"""
    selected = []
    remaining = list(candidates)
    
    for _ in range(count):
        if not remaining:
            break
        # 最小勤務日数を持つ職員を抽出
        min_work = min(work_count[e.id] for e in remaining)
        pool = [e for e in remaining if work_count[e.id] == min_work]
        # プールから1人選択（最初の人）
        chosen = pool[0]
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected
```

**特徴**:
- スキルは考慮せず、勤務日数のみで判断
- 最も公平な勤務配分が可能
- スキルバランスが偏る可能性がある

#### モード2: スキル重視 (`skill`)

**目的**: 目標スキルスコアに最も近づける

```python
def _select_by_skill_score(candidates, count, work_count, time_slot, current_selected):
    """目標スキルスコアに近い職員を選択"""
    selected = list(current_selected)
    remaining = list(candidates)
    
    for _ in range(count - len(selected)):
        if not remaining:
            break
        
        # 目標スコアの計算
        target = time_slot.target_skill_score or (time_slot.required_staff * 150)
        current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
        remaining_slots = max(1, count - len(selected))
        per_person_target = (target - current_score) / remaining_slots
        
        # 1人あたりの目標に最も近い職員を選択
        chosen = min(
            remaining,
            key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
        )
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected
```

**特徴**:
- 勤務日数は考慮せず、スキルのみで判断
- 各時間帯のスキルバランスが最適化される
- 特定の職員に勤務が集中する可能性がある

#### モード3: バランス (`balance`) - **推奨**

**目的**: 勤務日数とスキルの両方を考慮する

```python
def _select_by_balance(candidates, count, work_count, time_slot):
    """勤務日数とスキルのバランスを取る"""
    selected = []
    remaining = list(candidates)
    
    for _ in range(count):
        if not remaining:
            break
        
        # まず勤務日数でフィルタリング
        min_work = min(work_count[e.id] for e in remaining)
        pool = [e for e in remaining if work_count[e.id] == min_work]
        
        # フィルタされた候補の中からスキルで選択
        target = time_slot.target_skill_score or (time_slot.required_staff * 150)
        current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
        remaining_slots = max(1, count - len(selected))
        per_person_target = (target - current_score) / remaining_slots
        
        chosen = min(
            pool,
            key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
        )
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected
```

**特徴**:
- 勤務日数の少ない職員の中からスキルに適した人を選ぶ
- 公平性とサービス品質の両立
- 実務で最も推奨されるモード

### 4.3 選択戦略の統合

```python
def _select_employees_for_slot(candidates, time_slot, count, work_count, mode):
    """モードに応じた職員選択"""
    if len(candidates) < count:
        return []  # 候補が不足している場合は空配列
    
    if mode == "days":
        return _select_by_workday_count(candidates, count, work_count)
    elif mode == "skill":
        return _select_by_skill_score(candidates, count, work_count, time_slot, [])
    else:  # balance
        return _select_by_balance(candidates, count, work_count, time_slot)
```

---

## 5. 時間帯処理とシフト生成

### 5.1 単一時間帯の処理

```python
def _process_time_slot(slot, date_str, employees, schedule, work_count, 
                       optimisation_mode, morning_workers):
    """1つの時間帯に職員を割り当てる"""
    
    # ステップ1: 利用可能な職員をフィルタリング
    available, rejection_log = _filter_available_employees(
        employees, date_str, slot, schedule
    )
    
    # ステップ2: 必要人数の確認
    if len(available) < slot.required_staff:
        raise ShiftGenerationError(
            _create_insufficient_staff_error(date_str, slot, available, rejection_log)
        )
    
    # ステップ3: 職員の選択
    selected = _assign_employees_to_slot(
        available, slot, date_str, optimisation_mode, work_count, morning_workers
    )
    
    # ステップ4: 選択失敗のチェック
    if len(selected) < slot.required_staff:
        raise ShiftGenerationError(...)
    
    # ステップ5: シフトオブジェクトの生成
    shifts = []
    for employee in selected:
        shift = GeneratedShift(
            date=date_str,
            time_slot_id=slot.id,
            employee_id=employee.id,
            employee_name=employee.name,
            time_slot_name=slot.display_name,
            start_time=slot.start_time,
            end_time=slot.end_time,
            skill_score=calculate_skill_score(employee, slot),
            employee=employee,
            time_slot=slot,
        )
        shifts.append(shift)
        work_count[employee.id] += 1  # 勤務カウントを増やす
    
    return shifts
```

### 5.2 午後時間帯での午前勤務者優先

終日勤務の原則に従い、午前に勤務した職員を午後も優先的に配置します：

```python
def _assign_employees_to_slot(available, slot, date_str, optimisation_mode, 
                               work_count, morning_workers):
    """午後時間帯では午前勤務者を優先"""
    required = slot.required_staff
    selected = []
    
    # 午後時間帯で、午前勤務者がいる場合
    if slot.period == "afternoon" and morning_workers:
        # 午前に勤務した人で午後も可能な人を抽出
        afternoon_capable = [e for e in available if e.id in morning_workers]
        
        if afternoon_capable:
            needed = min(len(afternoon_capable), required)
            # 午前勤務者から優先的に選択
            selected = _select_employees_for_slot(
                afternoon_capable, slot, needed, work_count, optimisation_mode
            )
    
    # 残りの枠を埋める
    if len(selected) < required:
        remaining_available = [e for e in available if e not in selected]
        additional_needed = required - len(selected)
        additional = _select_employees_for_slot(
            remaining_available, slot, additional_needed, work_count, optimisation_mode
        )
        selected.extend(additional)
    
    return selected
```

### 5.3 1日分の処理

```python
def _process_daily_slots(date_str, daily_slots, employees, schedule, 
                         work_count, optimisation_mode, time_slots):
    """1日分の全時間帯を処理"""
    
    # 午前と午後に分類
    morning_slots = [s for s in daily_slots if s.period == "morning"]
    afternoon_slots = [s for s in daily_slots if s.period == "afternoon"]
    
    morning_workers_by_area = {}  # エリアごとの午前勤務者を記録
    daily_assignments = []

    # 午前時間帯を処理
    for slot in morning_slots:
        shifts = _process_time_slot(
            slot, date_str, employees, schedule, work_count, optimisation_mode, []
        )
        schedule.extend(shifts)
        daily_assignments.extend(shifts)
        
        # 午前勤務者を記録（エリア別）
        for shift in shifts:
            morning_workers_by_area.setdefault(slot.area, []).append(shift.employee_id)

    # 午後時間帯を処理（同じエリアの午前勤務者を優先）
    for slot in afternoon_slots:
        morning_workers = morning_workers_by_area.get(slot.area, [])
        shifts = _process_time_slot(
            slot, date_str, employees, schedule, work_count, 
            optimisation_mode, morning_workers
        )
        schedule.extend(shifts)
        daily_assignments.extend(shifts)

    # その日のパートタイム制約を検証
    if daily_assignments:
        violation = _evaluate_part_time_rule(daily_assignments, time_slots)
        if violation:
            raise ShiftGenerationError(violation)
    
    return daily_assignments
```

---

## 6. 制約条件の検証

### 6.1 パートタイム職員の配置ルール

TYPE_D職員（リハ室専任パート）は、必ずTYPE_AまたはTYPE_C（正職員）と一緒に配置する必要があります。

```python
def _evaluate_part_time_rule(shifts, time_slots):
    """TYPE_D職員が単独でないか検証"""
    
    if not shifts:
        return None

    slot_lookup = {slot.id: slot for slot in time_slots}

    # 時間帯ごとにシフトをグループ化
    grouped = {}
    for shift in shifts:
        grouped.setdefault(shift.time_slot_id, []).append(shift)

    # 各時間帯をチェック
    for slot_id, slot_shifts in grouped.items():
        slot = slot_lookup.get(slot_id, slot_shifts[0].time_slot)
        
        # リハ室のみチェック
        if slot.area != "リハ室":
            continue

        # 配置された職員のタイプを集める
        types = {s.employee.employee_type for s in slot_shifts}
        
        # TYPE_DがいるのにTYPE_AまたはTYPE_Cがいない場合はエラー
        if "TYPE_D" in types and not ({"TYPE_A", "TYPE_C"} & types):
            employees = [s.employee_name for s in slot_shifts]
            issue = ShiftGenerationIssue(
                code="part_time_rule",
                message=(
                    "リハ室の時間帯でTYPE_D職員のみが割り当てられています。"
                    "TYPE_AまたはTYPE_Cを同じ時間帯に配置してください。"
                ),
                date=slot_shifts[0].date,
                time_slot_id=slot_id,
                time_slot_name=slot.display_name,
                required=slot.required_staff,
                available=len(slot_shifts),
                available_employees=employees,
            )
            return issue

    return None
```

### 6.2 入力の事前検証

```python
def _validate_shift_inputs(employees, time_slots, start_date, end_date):
    """シフト生成前の入力検証"""
    
    # 職員の存在確認
    if not employees:
        raise ShiftGenerationError(
            ShiftGenerationIssue(code="no_employees", message="職員が登録されていません。")
        )
    
    # 時間帯の存在確認
    if not time_slots:
        raise ShiftGenerationError(
            ShiftGenerationIssue(code="no_time_slots", message="時間帯が登録されていません。")
        )
    
    # 日付範囲の妥当性確認
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if end < start:
        raise ShiftGenerationError(
            ShiftGenerationIssue(
                code="invalid_range",
                message="終了日は開始日以降の日付を指定してください。",
            )
        )
```

---

## 7. 休憩時間の自動割り当て

### 7.1 休憩割り当ての基本方針

1. **受付窓口の常駐人数を確保**: 休憩中でも受付に必要な人数（午前4-5名、午後3名）を維持
2. **勤務形態に応じた休憩時間**: 各職員の勤務パターンに基づいて適切な休憩を割り当て
3. **優先時間帯の活用**: 11:00-12:00、12:00-13:00、13:00-14:00の3つの時間帯を優先的に使用

### 7.2 休憩時間ウィンドウの決定

**休憩時間の基本原則**:
- **正職員B/C（月火金）と通常/△（水曜）**: 基本的に2時間連続で休憩を取得
- **忙しい日は分割可能**: 当日の状況に応じて1時間×2回に分割することも可能
- **正職員A（月火金）と◯（水曜）**: 60分休憩（1時間×1回）
- **時短勤務者・パート（午後まで）**: 60分休憩（1時間×1回）
- **パート午前のみ・木土勤務**: 休憩なし

**緊急時の休憩短縮対応**:
- 欠勤者が出た場合、休憩時間を1時間（60分）に短縮可能
- 短縮した1時間分は残業時間として計上
- これにより休憩返上（サービス残業）を防止

```python
# 優先する3つの時間帯
PREFERRED_WINDOWS = (
    ("11:00", "12:00"),
    ("12:00", "13:00"),
    ("13:00", "14:00"),
)

def _break_windows_for_pattern(pattern_break_hours):
    """勤務形態に応じた休憩ウィンドウを返す"""
    if pattern_break_hours >= 2:
        # 2時間休憩: 基本的に連続取得（11:00-13:00 または 12:00-14:00）
        # ただし、忙しい日は分割も可能（11:00-12:00 + 13:00-14:00）
        return [PREFERRED_WINDOWS[0], PREFERRED_WINDOWS[2]]
    if pattern_break_hours >= 1:
        # 1時間休憩: 12:00-13:00
        return [PREFERRED_WINDOWS[1]]
    return []  # 休憩なし
```

### 7.3 職員への休憩割り当て

```python
def _assign_break_for_employee(employee_id, blocks, window_usage, coverage_limit):
    """1人の職員に休憩時間を割り当てる"""
    
    # 勤務パターンから必要な休憩時間を取得
    pattern_id = blocks[0]["employee"].get("employment_pattern_id")
    pattern = get_employment_pattern(pattern_id) if pattern_id else None
    break_windows = _break_windows_for_pattern(pattern.break_hours if pattern else 0.0)
    
    # 割り当て可能なウィンドウを試す
    for window in break_windows:
        usable_windows = list(PREFERRED_WINDOWS)
        if window not in usable_windows:
            usable_windows.insert(0, window)
        
        for candidate in usable_windows:
            # このウィンドウの使用状況を確認
            if candidate not in window_usage:
                window_usage[candidate] = []
            
            # 上限チェック（受付常駐人数を確保）
            if len(window_usage[candidate]) >= coverage_limit:
                continue
            
            # このシフトがウィンドウをカバーしているか確認
            target_shift = _find_covering_shift(blocks, candidate)
            if not target_shift:
                continue
            
            # 割り当て成功
            window_usage[candidate].append(employee_id)
            return candidate
    
    return None  # 割り当て失敗
```

### 7.4 受付カバレッジの検証

```python
def validate_reception_coverage(date, shifts, break_schedules):
    """受付の常駐人数が確保されているか検証"""
    
    reception_shifts = _filter_reception_shifts(shifts)
    if not reception_shifts:
        return True, []

    warnings = []
    # 15分刻みでチェック
    intervals = generate_time_intervals("08:30", "19:00", 15)
    
    for window in intervals:
        working = _count_working_staff(reception_shifts, break_schedules, window)
        if working < 2:  # 最低2名必要
            warnings.append(
                f"{window[0]}-{window[1]}の受付常駐人数が不足しています ({working}名)"
            )

    return (len(warnings) == 0), warnings
```

### 7.5 休憩割り当て全体フロー

```python
def auto_assign_and_save_breaks(date, shifts):
    """休憩時間を自動割り当てしてDBに保存"""
    
    # 受付シフトのみ抽出
    reception_shifts = _filter_reception_shifts(shifts)
    if len(reception_shifts) < 3:
        return 0, True, ["受付職員が3名未満のため自動割り当てをスキップしました"]

    # カバレッジ上限を計算（受付人数 - 2）
    coverage_limit = len(reception_shifts) - 2
    
    # ウィンドウ使用状況を初期化
    window_usage = {window: [] for window in PREFERRED_WINDOWS}
    
    # 職員ごとにシフトをグループ化
    employee_blocks = _group_shifts_by_employee(reception_shifts)

    assignments = []
    warnings = []

    # 各職員に休憩を割り当て
    for employee_id, blocks in employee_blocks.items():
        assigned_window = _assign_break_for_employee(
            employee_id, blocks, window_usage, coverage_limit
        )
        if assigned_window:
            assignments.append((employee_id, assigned_window))
        else:
            warnings.append(
                f"{blocks[0]['employee_name']}の休憩時間を自動割り当てできませんでした"
            )

    if not assignments:
        return 0, False, warnings or ["有効な休憩割り当てがありません"]

    # DBに保存
    saved = _save_break_assignments(date, assignments, employee_blocks)
    return saved, not warnings, warnings
```

---

## 8. エラーハンドリングと診断

### 8.1 エラー情報の構造

```python
@dataclass
class ShiftGenerationIssue:
    """シフト生成エラーの詳細情報"""
    code: str                    # エラーコード
    message: str                 # エラーメッセージ
    date: Optional[str]          # 問題が発生した日
    time_slot_id: Optional[str]  # 問題の時間帯ID
    time_slot_name: Optional[str]  # 時間帯名
    required: Optional[int]      # 必要人数
    available: Optional[int]     # 利用可能人数
    shortage: Optional[int]      # 不足人数
    available_employees: List[str]  # 利用可能な職員のリスト
    rejections: List[RejectionSummary]  # 除外理由の集計
```

### 8.2 除外理由の集計

```python
@dataclass
class RejectionSummary:
    """職員が除外された理由の集計"""
    reason: str       # 除外理由
    count: int        # 該当人数
    examples: List[str]  # 例（職員名）
```

### 8.3 詳細エラー生成

```python
def _create_insufficient_staff_error(date_str, slot, available, rejection_log):
    """人員不足エラーの詳細情報を生成"""
    
    # 除外理由を件数順にソート
    rejections = [
        RejectionSummary(
            reason=reason,
            count=len(names),
            examples=sorted(names)[:5],  # 最大5件の例を記録
        )
        for reason, names in sorted(
            rejection_log.items(), 
            key=lambda item: len(item[1]), 
            reverse=True
        )
    ]
    
    return ShiftGenerationIssue(
        code="insufficient_staff",
        message=(
            f"{date_str} {slot.display_name}で必要人数{slot.required_staff}名を"
            "確保できませんでした。"
        ),
        date=date_str,
        time_slot_id=slot.id,
        time_slot_name=slot.display_name,
        required=slot.required_staff,
        available=len(available),
        shortage=slot.required_staff - len(available),
        available_employees=[emp.name for emp in available],
        rejections=rejections,
    )
```

### 8.4 エラー情報の活用例

生成されたエラー情報をUI上で表示することで、ユーザーは以下を把握できます：

1. **どの日のどの時間帯で**問題が発生したか
2. **何人不足**しているか
3. **誰が利用可能**か
4. **なぜ他の職員が除外**されたか（理由別の集計）

例：
```
2025-01-15 リハ室（午前）で必要人数2名を確保できませんでした。

必要人数: 2名
利用可能: 1名
不足: 1名

利用可能な職員:
- 山田太郎

除外理由:
1. 担当エリアの要件を満たしていません (3名)
   例: 佐藤花子, 鈴木一郎, 高橋美咲
2. 終日休暇 (2名)
   例: 田中次郎, 伊藤三郎
3. 同日の別時間帯と重複しています (1名)
   例: 渡辺四郎
```

---

## 9. 最適化戦略の比較

### 9.1 各モードの動作比較

具体例で各モードの違いを見てみましょう。

**状況**:
- 時間帯: 受付（午前）、必要人数3名
- 目標スキルスコア: 450点（1人あたり150点）
- 候補職員:

| 職員名 | 勤務回数 | スキルスコア |
|--------|---------|------------|
| 佐藤 | 2回 | 200点 |
| 鈴木 | 2回 | 140点 |
| 高橋 | 3回 | 180点 |
| 田中 | 3回 | 120点 |
| 伊藤 | 4回 | 160点 |

#### 日数重視モード

```
選択プロセス:
1. 最小勤務回数は2回 → 佐藤、鈴木が候補
2. プールから佐藤を選択（勤務回数2回→3回）
3. 最小勤務回数は2回 → 鈴木が候補
4. 鈴木を選択（勤務回数2回→3回）
5. 最小勤務回数は3回 → 高橋、田中が候補
6. プールから高橋を選択（勤務回数3回→4回）

結果: 佐藤、鈴木、高橋
合計スキル: 520点
判定: ○（目標450点を上回る）
```

#### スキル重視モード

```
選択プロセス:
1. 目標450点、1人あたり150点
2. 150点に最も近いのは伊藤(160点) → 選択
3. 現在160点、残り290点、1人あたり145点
4. 145点に最も近いのは鈴木(140点) → 選択
5. 現在300点、残り150点、1人あたり150点
6. 150点に最も近いのは伊藤(160点)だが既に選択済み
   次に近いのは高橋(180点) → 選択

結果: 伊藤、鈴木、高橋
合計スキル: 480点
判定: ○（目標450点に近い）
```

#### バランスモード（推奨）

```
選択プロセス:
1. 最小勤務回数は2回 → 佐藤、鈴木
2. 目標450点、1人あたり150点
   150点に近いのは鈴木(140点) → 選択
3. 現在140点、最小勤務回数は2回 → 佐藤
4. 残り310点、1人あたり155点
   佐藤(200点)を選択
5. 現在340点、最小勤務回数は3回 → 高橋、田中
6. 残り110点、1人あたり110点
   110点に近いのは田中(120点) → 選択

結果: 鈴木、佐藤、田中
合計スキル: 460点
判定: ○（目標に近く、勤務回数も考慮）
```

### 9.2 モード選択のガイドライン

| モード | 適用シーン | メリット | デメリット |
|--------|----------|---------|----------|
| 日数重視 | - 負担の公平性を最優先<br>- スキル差が小さい<br>- 新人育成期 | - 勤務配分が最も公平<br>- シンプルで理解しやすい | - スキルバランスが偏る可能性<br>- サービス品質のばらつき |
| スキル重視 | - サービス品質重視<br>- 繁忙期<br>- スキル差が大きい | - 安定したサービス品質<br>- 患者満足度の向上 | - 特定職員への偏り<br>- 不公平感が生じる可能性 |
| **バランス** | - **通常運用（推奨）**<br>- 公平性と品質の両立 | - **最もバランスが良い**<br>- 実務的に最適 | - やや複雑な選択ロジック |

---

## 10. アルゴリズムの計算量

### 10.1 時間計算量

主要な処理の計算量を分析します。

#### 全体の計算量

```
O(D × S × E)
```

where:
- `D`: 期間の日数
- `S`: 1日あたりの時間帯数（通常4-8）
- `E`: 職員数

#### 詳細な計算量

**1日分の処理** (`_process_daily_slots`):
```
O(S × E)
```
- 各時間帯(S個)について、職員(E人)の可用性をチェック

**職員の可用性チェック** (`_filter_available_employees`):
```
O(E × M)
```
where:
- `M`: 既存のシフト数（最悪ケースで O(D × S × R)、R=必要人数）

**職員の選択** (`_select_employees_for_slot`):
```
- 日数重視: O(R × E)
- スキル重視: O(R × E)
- バランス: O(R × E)
```
where:
- `R`: 必要人数（通常2-5名）

**全体の実効計算量**:
```
O(D × S × E × (E + D × S × R))
```

しかし、実際には:
- D: 7-31日（1週間〜1ヶ月）
- S: 4-8時間帯
- E: 5-10名
- R: 2-5名

なので、実用上は十分高速です。

### 10.2 空間計算量

```
O(D × S × R + E)
```

主要なメモリ使用:
- 生成されたシフト: `O(D × S × R)`
- 勤務カウンター: `O(E)`
- 時間帯リスト: `O(S)`

### 10.3 最適化の余地

現在のアルゴリズムは実用的な速度ですが、さらなる最適化が可能です：

1. **可用性キャッシュ**: 職員の可用性を事前計算してキャッシュ
2. **並列処理**: 異なる日の処理を並列化
3. **インデックス構造**: 職員の検索を高速化
4. **早期枝刈り**: 不可能な割り当てを早期に除外

---

## まとめ

このシフト生成アルゴリズムは、以下の特徴を持つヒューリスティック手法です：

### 強み

1. **実用性**: 実際の診療所の要件に完全に対応
2. **柔軟性**: 3つの最適化モードで様々なニーズに対応
3. **診断性**: 詳細なエラー情報で問題解決を支援
4. **効率性**: 実用的な規模で十分高速

### 制限事項

1. **最適解の保証なし**: ヒューリスティックのため、理論的な最適解は保証されない
2. **逐次処理**: 後の日付の処理が前の日付の結果に依存
3. **局所最適**: グローバルな最適化ではなく、各時間帯での局所最適化

### 改善の方向性

将来的には以下の改善が考えられます：

1. **機械学習の導入**: 過去のシフトパターンから学習
2. **制約充足問題(CSP)の適用**: より理論的なアプローチ
3. **遺伝的アルゴリズム**: グローバル最適化の探索
4. **ユーザーフィードバック**: 生成されたシフトへの評価を反映

---

**本ドキュメントの更新履歴**

- 2025-12-10: 初版作成
