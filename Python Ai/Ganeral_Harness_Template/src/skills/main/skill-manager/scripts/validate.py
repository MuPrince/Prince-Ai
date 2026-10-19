"""validate.py：校验单个技能目录的规范性（沙箱内运行，仅用标准库）。

校验规则:
    报错（退出码 1）: 缺 SKILL.md、缺 frontmatter、缺必填字段 name/description、
                      name 与目录名不一致、name 非法（非 kebab-case）
    告警（退出码 0）: 缺推荐字段 version/author/tags

用法:
    python3 validate.py <技能目录或SKILL.md路径> [--json]
"""

import argparse
import json
import os
import re
import sys

REQUIRED_FIELDS = ["name", "description"]            # 必填字段
RECOMMENDED_FIELDS = ["version", "author", "tags"]   # 推荐字段
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")        # kebab-case


def parse_frontmatter(text: str):
    """解析 SKILL.md 顶部的 YAML frontmatter（仅支持 key: value 与 '- item' 列表）。

    返回 (字段dict, 错误信息或None)。不依赖 PyYAML（沙箱无 pip）。
    """
    if not text.startswith("---"):
        return None, "缺少 frontmatter（文件须以 --- 开头）"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "frontmatter 未闭合（缺少结尾 ---）"

    fields = {}
    current_key = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if m:
            current_key = m.group(1)
            value = m.group(2).strip()
            fields[current_key] = value if value else []
        elif line.strip().startswith("- ") and current_key:
            # 列表项：挂在最近一个 key 下
            if not isinstance(fields.get(current_key), list):
                fields[current_key] = []
            fields[current_key].append(line.strip()[2:].strip())
    return fields, None


def validate_skill(path: str):
    """校验单个技能，返回 (错误列表, 告警列表, 元数据dict)。"""
    errors, warnings, meta = [], [], {}

    # 定位 SKILL.md 与技能目录名
    if os.path.isdir(path):
        skill_dir = path
        skill_md = os.path.join(path, "SKILL.md")
    else:
        skill_md = path
        skill_dir = os.path.dirname(os.path.abspath(path))
    dir_name = os.path.basename(os.path.normpath(skill_dir))

    if not os.path.isfile(skill_md):
        return [f"SKILL.md 不存在：{skill_md}"], warnings, meta

    with open(skill_md, "r", encoding="utf-8") as f:
        text = f.read()

    fields, err = parse_frontmatter(text)
    if err:
        return [err], warnings, meta
    meta = fields

    # 必填字段检查
    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            errors.append(f"缺少必填字段：{field}")

    # 推荐字段检查
    for field in RECOMMENDED_FIELDS:
        if not fields.get(field):
            warnings.append(f"缺少推荐字段：{field}")

    # name 合法性与目录名一致性检查
    name = fields.get("name")
    if isinstance(name, str) and name:
        if not NAME_RE.match(name):
            errors.append(f"name '{name}' 非法，需为小写字母/数字/中划线（kebab-case）")
        if name != dir_name:
            errors.append(f"name '{name}' 与目录名 '{dir_name}' 不一致")

    return errors, warnings, meta


def main():
    parser = argparse.ArgumentParser(description="校验技能目录规范性")
    parser.add_argument("path", help="技能目录或 SKILL.md 文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    errors, warnings, meta = validate_skill(args.path)
    status = "error" if errors else ("warn" if warnings else "ok")

    if args.json:
        print(json.dumps({
            "status": status, "path": args.path,
            "errors": errors, "warnings": warnings, "meta": meta,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"校验结果：{status}  ({args.path})")
        for e in errors:
            print(f"  [报错] {e}")
        for w in warnings:
            print(f"  [告警] {w}")
        if status == "ok":
            print("  全部通过")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
