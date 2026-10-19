"""check_all.py：批量体检指定目录下的所有技能并输出报告（沙箱内运行，仅用标准库）。

（命名避开标准库 inspect，防止同名遮蔽导致 argparse 等崩溃。）

支持两种技能布局，凡目录内直接含 SKILL.md 的即视为一个技能：
- 一层：<root>/<skill>/SKILL.md
- 两层：<root>/<agent>/<skill>/SKILL.md（<agent> 目录自身不含 SKILL.md 时自动向下再扫一层）

用法:
    python3 check_all.py [root] [--json] [--output index.json]

选项:
    root      待扫描目录（默认 /workspace/dist）
    --json    以 JSON 输出报告
    --output  同时把索引写入指定文件（技能名/版本/状态/问题清单）
"""

import argparse
import json
import os
import sys

# 复用同目录 validate.py 的校验逻辑（脚本目录自动在 sys.path）
from validate import validate_skill


def _is_skill_dir(path: str) -> bool:
    """目录内是否直接含 SKILL.md（是则视为一个技能目录）。"""
    return os.path.isfile(os.path.join(path, "SKILL.md"))


def _validate_one(skill_dir: str, dir_name: str, agent: str) -> dict:
    """校验单个技能目录，返回结果条目（agent 为空表示一层布局）。"""
    errors, warnings, meta = validate_skill(skill_dir)
    status = "error" if errors else ("warn" if warnings else "ok")
    return {
        "name": meta.get("name", dir_name),
        "agent": agent,
        "dir": dir_name,
        "version": meta.get("version", ""),
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def inspect_root(root: str):
    """扫描并校验 root 下所有技能，返回结果列表。

    支持两种布局：
    - 一层：<root>/<skill>/SKILL.md
    - 两层：<root>/<agent>/<skill>/SKILL.md（agent 目录自身不含 SKILL.md 时向下再扫一层）
    """
    results = []
    if not os.path.isdir(root):
        return results
    for entry in sorted(os.listdir(root)):
        top = os.path.join(root, entry)
        if not os.path.isdir(top):
            continue
        if _is_skill_dir(top):
            # 一层布局：<root>/<skill>/
            results.append(_validate_one(top, entry, agent=""))
            continue
        # 否则视为 agent 目录，向下扫描两层布局：<root>/<agent>/<skill>/
        for sub_entry in sorted(os.listdir(top)):
            sub = os.path.join(top, sub_entry)
            if os.path.isdir(sub) and _is_skill_dir(sub):
                results.append(_validate_one(sub, sub_entry, agent=entry))
    return results


def main():
    parser = argparse.ArgumentParser(description="批量体检技能目录")
    parser.add_argument("root", nargs="?", default="/workspace/dist", help="待扫描目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--output", default=None, help="把索引写入指定文件")
    args = parser.parse_args()

    results = inspect_root(args.root)
    summary = {
        "root": args.root,
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "warn": sum(1 for r in results if r["status"] == "warn"),
        "error": sum(1 for r in results if r["status"] == "error"),
        "skills": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"体检目录：{args.root}（共 {summary['total']} 个技能）")
        for r in results:
            label = f"{r['agent']}/{r['dir']}" if r.get("agent") else r["dir"]
            print(f"  [{r['status']:5}] {label} (v{r['version'] or '-'})")
            for e in r["errors"]:
                print(f"         报错: {e}")
            for w in r["warnings"]:
                print(f"         告警: {w}")
        print(f"汇总：ok={summary['ok']} warn={summary['warn']} error={summary['error']}")

    # 可选：输出索引文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"索引已写入：{args.output}")

    sys.exit(1 if summary["error"] else 0)


if __name__ == "__main__":
    main()
