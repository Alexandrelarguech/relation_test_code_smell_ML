from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePath
from typing import Iterable

TRUE_VALUES = {"true", "yes", "1", "x", "y"}
FALSE_VALUES = {"false", "no", "0", "", "nan", "none", "null"}
FILE_COLUMN_HINTS = ("file", "path", "filepath", "testfilepath", "productionfilepath")
TEST_NAME_RE = re.compile(r"^(?:Test)?(?P<name>.*?)(?:Tests?|TestCase|IT|ITCase)?$")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def norm_path(value: str) -> str:
    return value.strip().replace("\\", "/")


def java_class_key(path: str) -> str:
    """Return a stable key from a Java file path: package-ish path + class name."""
    path = norm_path(path)
    if not path:
        return ""
    if path.endswith(".java"):
        path = path[:-5]
    parts = [p for p in PurePath(path).parts if p not in {".", ""}]
    for marker in ("src/main/java", "src/test/java"):
        marker_parts = marker.split("/")
        for idx in range(len(parts) - len(marker_parts) + 1):
            if parts[idx : idx + len(marker_parts)] == marker_parts:
                return "/".join(parts[idx + len(marker_parts) :])
    return "/".join(parts[-4:]) if len(parts) > 4 else "/".join(parts)


def production_key_from_test(path: str) -> str:
    key = java_class_key(path)
    if not key:
        return ""
    package, _, class_name = key.rpartition("/")
    match = TEST_NAME_RE.match(class_name)
    base_name = match.group("name") if match else class_name
    return f"{package}/{base_name}" if package else base_name


def class_name_from_key(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def find_column(columns: Iterable[str], preferred: Iterable[str], fuzzy: bool = True) -> str | None:
    lowered = {column.lower().replace("_", ""): column for column in columns}
    for name in preferred:
        hit = lowered.get(name.lower().replace("_", ""))
        if hit:
            return hit
    if fuzzy:
        for column in columns:
            flat = column.lower().replace("_", "")
            if any(hint in flat for hint in FILE_COLUMN_HINTS):
                return column
    return None


def is_truthy(value: str) -> bool:
    value = str(value).strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    try:
        return float(value) > 0
    except ValueError:
        return bool(value)


def aggregate_code_smells(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, object]], list[str]]:
    if not rows:
        return {}, []
    file_col = find_column(rows[0].keys(), ["File", "FilePath", "Path"])
    rule_col = find_column(rows[0].keys(), ["Rule", "Rule name", "RuleName", "Problem"])
    by_class: dict[str, dict[str, object]] = {}
    all_rules: set[str] = set()

    for row in rows:
        file_path = norm_path(row.get(file_col or "", ""))
        if not file_path:
            continue
        key = java_class_key(file_path)
        item = by_class.setdefault(key, {"class_file": file_path, "code_smell_total": 0, "_rules": Counter()})
        item["code_smell_total"] = int(item["code_smell_total"]) + 1
        rule = (row.get(rule_col or "", "") or "unknown_code_smell").strip().replace(" ", "_")
        item["_rules"][rule] += 1
        all_rules.add(rule)

    columns = [f"code_smell_{rule}" for rule in sorted(all_rules)]
    for item in by_class.values():
        rules = item.pop("_rules")
        for rule in sorted(all_rules):
            item[f"code_smell_{rule}"] = rules.get(rule, 0)
    return by_class, columns


def aggregate_test_smells(rows: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    if not rows:
        return {}, []
    columns = list(rows[0].keys())
    test_file_col = find_column(columns, ["TestFilePath", "FilePath", "File", "Path"])
    prod_file_col = find_column(columns, ["ProductionFilePath", "ProductionFile", "ClassFile", "TestedFile"], fuzzy=False)
    smell_cols = [c for c in columns if c not in {test_file_col, prod_file_col} and "smell" in c.lower()]
    if not smell_cols:
        smell_cols = [c for c in columns if c not in {test_file_col, prod_file_col, "Project", "TestClass", "Class"}]

    by_prod: dict[str, list[dict[str, object]]] = defaultdict(list)
    out_cols = [f"test_smell_{c}" for c in smell_cols]
    for row in rows:
        test_file = norm_path(row.get(test_file_col or "", ""))
        prod_file = norm_path(row.get(prod_file_col or "", "")) if prod_file_col else ""
        key = java_class_key(prod_file) if prod_file else production_key_from_test(test_file)
        item = {"test_file": test_file, "test_smell_total": 0}
        for col in smell_cols:
            value = 1 if is_truthy(row.get(col, "")) else 0
            item[f"test_smell_{col}"] = value
            item["test_smell_total"] = int(item["test_smell_total"]) + value
        by_prod[key].append(item)
    return by_prod, out_cols


def build_project(project: str, code_csv: Path, test_csv: Path) -> tuple[list[dict[str, object]], list[str]]:
    code_by_class, code_rule_cols = aggregate_code_smells(read_csv(code_csv))
    tests_by_class, test_smell_cols = aggregate_test_smells(read_csv(test_csv))
    base_cols = ["project", "class_key", "class_name", "class_file", "test_file", "has_code_smell", "code_smell_total", "has_test_smell", "test_smell_total"]
    columns = base_cols + code_rule_cols + test_smell_cols
    rows: list[dict[str, object]] = []

    for class_key in sorted(set(code_by_class) | set(tests_by_class)):
        code = code_by_class.get(class_key, {"class_file": "", "code_smell_total": 0})
        tests = tests_by_class.get(class_key) or [{"test_file": "", "test_smell_total": 0}]
        for test in tests:
            row = {col: 0 for col in columns}
            row.update({"project": project, "class_key": class_key, "class_name": class_name_from_key(class_key)})
            row.update(code)
            row.update(test)
            row["has_code_smell"] = 1 if int(row.get("code_smell_total", 0)) > 0 else 0
            row["has_test_smell"] = 1 if int(row.get("test_smell_total", 0)) > 0 else 0
            rows.append(row)
    return rows, columns


def main() -> None:
    parser = argparse.ArgumentParser(description="Pair production-class and test-class smell CSV files.")
    parser.add_argument("--code-smells-dir", type=Path, default=Path("dataset/code_smells"))
    parser.add_argument("--test-smells-dir", type=Path, default=Path("dataset/test_smells"))
    parser.add_argument("--output-dir", type=Path, default=Path("dataset/final"))
    parser.add_argument("--projects", nargs="*", help="Optional project names. Default: CSV stems from smell directories.")
    args = parser.parse_args()

    projects = args.projects or sorted({p.stem for p in args.code_smells_dir.glob("*.csv")} | {p.stem for p in args.test_smells_dir.glob("*.csv")})
    all_rows: list[dict[str, object]] = []
    all_columns: list[str] = []
    for project in projects:
        rows, columns = build_project(project, args.code_smells_dir / f"{project}.csv", args.test_smells_dir / f"{project}.csv")
        write_csv(args.output_dir / f"{project}.csv", rows, columns)
        all_rows.extend(rows)
        all_columns = list(dict.fromkeys(all_columns + columns))
        print(f"[OK] {project}: {len(rows)} paires classe/test écrites")
    if all_rows:
        normalized = [{col: row.get(col, 0) for col in all_columns} for row in all_rows]
        write_csv(args.output_dir / "all_projects.csv", normalized, all_columns)
        print(f"[OK] all_projects.csv: {len(all_rows)} lignes")


if __name__ == "__main__":
    main()