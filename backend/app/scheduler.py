"""PySAT を用いたタスクスケジューリングエンジン。

モデル:
  - 各タスクは締切までのいずれか1日に「まとめて」割り当てる（exactly-one）。
  - 依存タスクは、依存元より厳密に早い日に割り当てる（ペアワイズ節）。
  - 各日の合計所要時間は、その日の作業可能時間（既定値または自然言語制約による
    上書き）を超えない（擬似ブール制約。sequential weight counter 法で自前にCNF化）。
  - 重要度が高いタスクほど早い日に配置されるよう、MaxSAT (RC2) でソフト制約
    として最適化する。
  - 充足不可能な場合は、容量制約の復元・締切の延長を1つずつ試すグリーディ探索で
    「どの制約を緩めれば解決するか」を提案する。
"""

from dataclasses import dataclass
from datetime import date, timedelta

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool, WCNF
from pysat.solvers import Glucose3
from pysat.examples.rc2 import RC2

HOUR_SCALE = 2  # 0.5時間単位で丸める


@dataclass
class DayCapacity:
    hours: float
    is_override: bool
    constraint_id: int | None
    reason: str | None


def _units(hours: float) -> int:
    return max(1, round(hours * HOUR_SCALE))


def build_horizon(tasks: list[dict], today: date, horizon_days: int) -> list[date]:
    end = today + timedelta(days=horizon_days - 1)
    if tasks:
        max_deadline = max(t["deadline"] for t in tasks)
        if max_deadline > end:
            end = min(max_deadline, today + timedelta(days=179))
    days = []
    d = today
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def compute_day_capacity(
    horizon: list[date], constraints: list[dict], default_hours: float
) -> dict[date, DayCapacity]:
    result: dict[date, DayCapacity] = {
        d: DayCapacity(default_hours, False, None, None) for d in horizon
    }
    for c in constraints:
        ctype = c["constraint_type"]
        for d in horizon:
            matched = False
            candidate_hours = None
            if ctype == "recurring_weekday_limit" and c.get("weekday") is not None:
                if d.weekday() == c["weekday"]:
                    matched = True
                    candidate_hours = c.get("available_hours", 0) or 0
            elif ctype == "specific_date_limit" and c.get("date"):
                if d.isoformat() == c["date"]:
                    matched = True
                    candidate_hours = c.get("available_hours", 0) or 0
            elif ctype == "specific_date_unavailable" and c.get("date"):
                if d.isoformat() == c["date"]:
                    matched = True
                    candidate_hours = 0
            elif ctype == "date_range_unavailable" and c.get("start_date") and c.get("end_date"):
                if c["start_date"] <= d.isoformat() <= c["end_date"]:
                    matched = True
                    candidate_hours = 0
            if matched and candidate_hours is not None:
                current = result[d]
                if candidate_hours < current.hours:
                    result[d] = DayCapacity(candidate_hours, True, c["id"], c.get("reason"))
    return result


def detect_cycle(tasks: list[dict]) -> list[int] | None:
    graph = {t["id"]: t["depends_on"] for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in graph}
    parent = {}

    def dfs(u):
        color[u] = GRAY
        for v in graph.get(u, []):
            if v not in color:
                continue
            if color[v] == WHITE:
                parent[v] = u
                cyc = dfs(v)
                if cyc:
                    return cyc
            elif color[v] == GRAY:
                cycle = [v]
                cur = u
                while cur != v:
                    cycle.append(cur)
                    cur = parent[cur]
                cycle.append(v)
                cycle.reverse()
                return cycle
        color[u] = BLACK
        return None

    for tid in graph:
        if color[tid] == WHITE:
            cyc = dfs(tid)
            if cyc:
                return cyc
    return None


def _pb_at_most(lits: list[int], weights: list[int], bound: int, pool: IDPool, tag: str) -> list[list[int]]:
    """sum(weights[i] * lits[i]) <= bound を CNF に変換する（sequential weight counter法）。

    s[i][j] は「先頭 i 個の中の重み付き和が j 以上」を意味する補助変数（i=1..n, j=1..bound）。
    実際の和が j 以上ならば s[i][j] は真になる（一方向の含意で十分＝健全性維持）。
    x_i を真にすると和が bound を超えてしまう場合は x_i を禁止する節を追加する。
    """
    clauses: list[list[int]] = []
    n = len(lits)

    def s(i: int, j: int):
        if j <= 0:
            return None  # 常に真として扱う（特別扱い）
        if i == 0:
            return False  # 常に偽（アイテムなしでは和>0にならない）
        return pool.id((tag, "s", i, j))

    for i in range(1, n + 1):
        w = weights[i - 1]
        x = lits[i - 1]
        for j in range(1, bound + 1):
            cur = s(i, j)
            prev_j = s(i - 1, j)
            if prev_j is not False:
                clauses.append([-prev_j, cur])
            src = s(i - 1, j - w)
            if src is None:
                clauses.append([-x, cur])
            elif src is not False:
                clauses.append([-x, -src, cur])
        overflow_src = s(i - 1, bound - w + 1)
        if overflow_src is None:
            clauses.append([-x])
        elif overflow_src is not False:
            clauses.append([-x, -overflow_src])
    return clauses


def _allowed_days(tasks: list[dict], horizon: list[date], capacity: dict[date, DayCapacity]):
    allowed = {}
    for t in tasks:
        allowed[t["id"]] = [d for d in horizon if d <= t["deadline"] and capacity[d].hours > 0]
    return allowed


def _build_hard_clauses(
    tasks: list[dict],
    allowed: dict[int, list[date]],
    capacity: dict[date, DayCapacity],
):
    pool = IDPool()
    var = {}
    for t in tasks:
        for d in allowed[t["id"]]:
            var[(t["id"], d)] = pool.id(("x", t["id"], d.isoformat()))

    clauses: list[list[int]] = []

    for t in tasks:
        lits = [var[(t["id"], d)] for d in allowed[t["id"]]]
        if not lits:
            continue
        eq = CardEnc.equals(lits=lits, bound=1, vpool=pool, encoding=EncType.seqcounter)
        clauses.extend(eq.clauses)

    tasks_by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        for dep_id in t["depends_on"]:
            dep = tasks_by_id.get(dep_id)
            if dep is None:
                continue
            for d_t in allowed[t["id"]]:
                for d_dep in allowed[dep_id]:
                    if d_dep >= d_t:
                        clauses.append([-var[(t["id"], d_t)], -var[(dep_id, d_dep)]])

    by_day: dict[date, list[tuple[int, int]]] = {}
    for t in tasks:
        for d in allowed[t["id"]]:
            by_day.setdefault(d, []).append((var[(t["id"], d)], _units(t["estimated_hours"])))

    for d, entries in by_day.items():
        cap_units = round(capacity[d].hours * HOUR_SCALE)
        lits = [e[0] for e in entries]
        weights = [e[1] for e in entries]
        if cap_units <= 0:
            for lit in lits:
                clauses.append([-lit])
            continue
        if sum(weights) <= cap_units:
            continue  # 制約を追加しなくても自明に満たされる
        clauses.extend(_pb_at_most(lits, weights, cap_units, pool, tag=f"cap-{d.isoformat()}"))

    return clauses, pool, var


def _solve_sat(clauses: list[list[int]]) -> bool:
    with Glucose3(bootstrap_with=clauses) as solver:
        return solver.solve()


def _optimize(tasks: list[dict], allowed: dict[int, list[date]], clauses: list[list[int]], var, horizon: list[date]):
    wcnf = WCNF()
    wcnf.extend(clauses)
    day_index = {d: i for i, d in enumerate(horizon)}
    for t in tasks:
        for d in allowed[t["id"]]:
            weight = t["importance"] * (day_index[d] + 1)
            wcnf.append([-var[(t["id"], d)]], weight=weight)

    with RC2(wcnf) as rc2:
        model = rc2.compute()
    true_vars = {l for l in model if l > 0}
    assignment = {}
    for t in tasks:
        for d in allowed[t["id"]]:
            if var[(t["id"], d)] in true_vars:
                assignment[t["id"]] = d
                break
    return assignment


def _diagnose(
    tasks: list[dict],
    horizon: list[date],
    capacity: dict[date, DayCapacity],
    allowed: dict[int, list[date]],
    default_hours: float,
):
    issues: list[str] = []
    suggestions: list[dict] = []

    zero_alloc = [t for t in tasks if not allowed[t["id"]]]
    if zero_alloc:
        for t in zero_alloc:
            issues.append(f"「{t['name']}」は締切({t['deadline'].isoformat()})までに作業可能な日がありません。")
            suggestions.append(
                {
                    "kind": "extend_deadline",
                    "task_id": t["id"],
                    "description": f"「{t['name']}」の締切を延長してください。",
                }
            )
        return issues, suggestions

    # 1タスク=1日に割り当てるモデルのため、タスクの所要時間が「期間内でその日に
    # 得られる最大の作業可能時間」を超える場合、締切をいくら延長しても絶対に
    # 割り当て不可能。これを先に特定しないと、後続の緩和探索が全て空振りして
    # 原因不明の「合計時間」メッセージしか出せなくなる。
    max_daily_capacity = max((c.hours for c in capacity.values()), default=default_hours)
    oversized = [t for t in tasks if t["estimated_hours"] > max_daily_capacity]
    if oversized:
        for t in oversized:
            issues.append(
                f"「{t['name']}」の所要時間は{t['estimated_hours']}時間ですが、"
                f"期間内でその日に得られる最大の作業可能時間は{max_daily_capacity}時間しかないため、"
                "締切を延長してもどの日にも収まりません（1タスクは1日にまとめて割り当てる仕様のため分割できません）。"
            )
            suggestions.append(
                {
                    "kind": "reduce_hours",
                    "task_id": t["id"],
                    "description": (
                        f"「{t['name']}」の推定所要時間を{max_daily_capacity}時間以下に減らすか、"
                        "設定の「1日の作業可能時間」を増やしてください。"
                    ),
                }
            )
        return issues, suggestions

    capacity = dict(capacity)
    deadlines = {t["id"]: t["deadline"] for t in tasks}
    cur_allowed = {tid: list(days) for tid, days in allowed.items()}

    def rebuild_and_solve():
        cap_only_hours = {d: capacity[d] for d in horizon}
        clauses, _, _ = _build_hard_clauses(tasks, cur_allowed, cap_only_hours)
        return _solve_sat(clauses)

    overridden_days = sorted(
        [d for d in horizon if capacity[d].is_override],
        key=lambda d: capacity[d].hours,
    )
    for d in overridden_days:
        old = capacity[d]
        capacity[d] = DayCapacity(default_hours, False, None, None)
        for t in tasks:
            if d <= t["deadline"] and d not in cur_allowed[t["id"]]:
                cur_allowed[t["id"]] = sorted(cur_allowed[t["id"]] + [d])
        if rebuild_and_solve():
            suggestions.append(
                {
                    "kind": "restore_capacity",
                    "constraint_id": old.constraint_id,
                    "description": (
                        f"{d.isoformat()} の作業可能時間の制約"
                        f"（{old.reason or '入力された制約'}）を"
                        f"{old.hours}時間から{default_hours}時間に緩めると解決します。"
                    ),
                }
            )
            issues.append(f"{d.isoformat()} の作業時間制約が厳しく、全タスクを収めることができませんでした。")
            return issues, suggestions

    sorted_tasks = sorted(tasks, key=lambda t: t["importance"])
    horizon_end = horizon[-1]
    for t in sorted_tasks:
        for d in horizon:
            if d <= deadlines[t["id"]] or capacity[d].hours <= 0:
                continue
            cur_allowed[t["id"]] = [dd for dd in horizon if dd <= d and capacity[dd].hours > 0]
            if rebuild_and_solve():
                extended_days = (d - t["deadline"]).days
                suggestions.append(
                    {
                        "kind": "extend_deadline",
                        "task_id": t["id"],
                        "description": (
                            f"「{t['name']}」（重要度{t['importance']}）の締切を"
                            f"{extended_days}日延長し{d.isoformat()}までにすると解決します。"
                        ),
                    }
                )
                issues.append(f"「{t['name']}」の締切が厳しく、全タスクを収めることができませんでした。")
                return issues, suggestions
        deadlines[t["id"]] = horizon_end

    # 単純な「全期間の合計時間」比較では、締切が近い日に作業が集中して破綻して
    # いるケースを見逃す（期間全体では余裕があっても、特定の締切までの窓では
    # 足りないことがある）。締切の早い順に必要時間を積み上げ、その締切までに
    # 得られる作業可能時間の累計と比較し、最初に破綻する締切とその原因タスクを
    # 特定する（Earliest-Deadline-First 方式の必要条件チェック）。
    sorted_by_deadline = sorted(tasks, key=lambda t: t["deadline"])
    cumulative_required = 0.0
    for t in sorted_by_deadline:
        cumulative_required += t["estimated_hours"]
        cumulative_capacity = sum(
            c.hours for d, c in capacity.items() if d <= t["deadline"]
        )
        if cumulative_required > cumulative_capacity:
            due_names = [
                tt["name"] for tt in sorted_by_deadline if tt["deadline"] <= t["deadline"]
            ]
            issues.append(
                f"{t['deadline'].isoformat()}までに完了させる必要があるタスク"
                f"（{'、'.join(due_names)}）の合計所要時間は{round(cumulative_required, 2)}時間ですが、"
                f"{t['deadline'].isoformat()}までに得られる合計作業可能時間は"
                f"{round(cumulative_capacity, 2)}時間しかありません。"
            )
            break

    total_required = sum(t["estimated_hours"] for t in tasks)
    total_capacity = sum(c.hours for c in capacity.values())
    issues.append(
        "締切の延長や時間制約の緩和を最大限試しても全タスクを収めることができませんでした"
        "（依存関係の順序制約が原因の可能性もあります）。"
        f"参考: 期間全体で必要な合計作業時間は{total_required}時間、"
        f"期間全体の合計作業可能時間は{total_capacity}時間です。"
        "タスクを減らすか所要時間を見直してください。"
    )
    return issues, suggestions


def generate_schedule(
    tasks: list[dict],
    constraints: list[dict],
    default_hours: float,
    horizon_days: int,
    today: date,
) -> dict:
    if not tasks:
        return {"feasible": True, "items": [], "day_loads": [], "suggestions": [], "issues": []}

    cycle = detect_cycle(tasks)
    if cycle:
        names = {t["id"]: t["name"] for t in tasks}
        cycle_desc = " → ".join(names.get(tid, str(tid)) for tid in cycle)
        return {
            "feasible": False,
            "items": [],
            "day_loads": [],
            "suggestions": [],
            "issues": [f"依存関係が循環しています: {cycle_desc}"],
        }

    horizon = build_horizon(tasks, today, horizon_days)
    capacity = compute_day_capacity(horizon, constraints, default_hours)
    allowed = _allowed_days(tasks, horizon, capacity)

    clauses, pool, var = _build_hard_clauses(tasks, allowed, capacity)
    feasible = all(allowed[t["id"]] for t in tasks) and _solve_sat(clauses)

    if not feasible:
        issues, suggestions = _diagnose(tasks, horizon, capacity, allowed, default_hours)
        return {
            "feasible": False,
            "items": [],
            "day_loads": [],
            "suggestions": suggestions,
            "issues": issues,
        }

    assignment = _optimize(tasks, allowed, clauses, var, horizon)

    items = []
    used_hours: dict[date, float] = {d: 0.0 for d in horizon}
    for t in tasks:
        d = assignment[t["id"]]
        used_hours[d] += t["estimated_hours"]
        items.append(
            {
                "task_id": t["id"],
                "task_name": t["name"],
                "day": d,
                "estimated_hours": t["estimated_hours"],
                "importance": t["importance"],
            }
        )
    items.sort(key=lambda i: (i["day"], -i["importance"]))

    day_loads = [
        {
            "day": d,
            "capacity_hours": capacity[d].hours,
            "used_hours": round(used_hours[d], 2),
            "is_override": capacity[d].is_override,
            "note": capacity[d].reason,
        }
        for d in horizon
        if used_hours[d] > 0
    ]

    return {
        "feasible": True,
        "items": items,
        "day_loads": day_loads,
        "suggestions": [],
        "issues": [],
    }
