#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_skillmd.py — SKILL.md 机械项确定性 lint（skill-md-optimizer 配套）

零出网、零必需凭据。仅标准库 + PyYAML（缺失时自动尝试安装，装不上则 BLOCKED）。
职责：判「机械项」（H6）——frontmatter 语法/字段、name/slug 规范、描述长度、
正文行数、token 预算估算、references 路径悬空、trigger 无 NOT-for 边界。
模型只做「判断层」（该不该拆 references、措辞好坏），机械项交给本脚本，保证跨 Agent 可复现。

用法：
  python check_skillmd.py <SKILL.md 路径> [--platform skillhub|clawhub|claude|workbuddy|github] \
      [--token-budget 8000] [--json]

退出码契约（与 skill-publish-gate 同构，CI 友好）：
  0  PASS      无 blocker（可有 medium/low 建议项）
  2  NEEDS_FIX  仅建议项（medium/low）
  1  BLOCKED    命中 blocker（语法解析失败 / 缺 name / 预算超硬上限等）
"""
import argparse
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------- 基础工具

def log(level, rule_id, msg, level_label=None):
    """统一命中记录。"""
    global _FINDINGS
    _FINDINGS.append({
        "rule_id": rule_id,
        "severity": level,           # "blocker" | "medium" | "low"
        "msg": msg,
    })
    label = level_label or {
        "blocker": "BLOCKER", "medium": "MEDIUM", "low": "LOW",
    }[level]
    print(f"[{label}] {rule_id}: {msg}", file=sys.stderr)


_FINDINGS = []


def parse_frontmatter(text):
    """分离 YAML frontmatter 与正文。返回 (fm_text, body_text)。"""
    if not text.startswith("---"):
        log("blocker", "FM-001", "文件未以 '---' 开头，无 frontmatter。")
        return "", text
    lines = text.split("\n")
    # 找闭合的 '---'
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            close = i
            break
    if close is None:
        log("blocker", "FM-002", "frontmatter 缺少闭合 '---'（YAML 块未关闭）。")
        return "", text
    fm_text = "\n".join(lines[1:close])
    body = "\n".join(lines[close + 1:])
    return fm_text, body


def load_yaml(fm_text, path, platform):
    """解析 frontmatter YAML。失败即 BLOCKED（不静默通过）。"""
    try:
        import yaml  # type: ignore
    except ImportError:
        # 尝试自动安装（离线时失败 → 升级为 BLOCKER）
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", "pyyaml"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            import yaml
        except Exception:
            log("blocker", "FM-003", "缺 PyYAML 且自动安装失败；无法解析 frontmatter（BLOCKED，不静默通过）。")
            return None
    try:
        data = yaml.safe_load(fm_text)
        if not isinstance(data, dict):
            log("blocker", "FM-004", "frontmatter 顶层不是 mapping（YAML 解析异常）。")
            return None
        return data
    except yaml.YAMLError as e:
        log("blocker", "FM-005", f"YAML 解析失败（很可能是半角冒号+空格或引号问题）：{e}")
        return None


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESC_CHAR_LIMIT = 1024        # Claude 触发元数据字符上限（保守）
BODY_LINE_SOFT = 200         # 软上限（建议）
BODY_LINE_HARD = 500         # 硬上限（blocker）


def check_name(slug, name, data, platform):
    # name 规范
    if not name:
        log("blocker", "FM-101", "缺 name（YAML 必需）。")
        return
    if not NAME_RE.match(name):
        log("medium", "FM-102", f"name '{name}' 不符合小写连字符 slug 规范（^[a-z0-9]+(-[a-z0-9]+)*$）。")
    # slug（若存在）须等于 name
    slug_val = data.get("slug")
    if slug_val and slug_val != name:
        log("low", "FM-103", f"slug '{slug_val}' 与 name '{name}' 不一致。")
    # description 必需
    desc = data.get("description")
    if not desc:
        log("blocker", "FM-104", "缺 description（触发核心，YAML 必需）。")
        return
    # description 长度
    if len(str(desc)) > DESC_CHAR_LIMIT:
        log("low", "FM-105", f"description 长 {len(str(desc))} 字符 > {DESC_CHAR_LIMIT}，宿主可能截断。")
    # 平台特定字段
    if platform == "clawhub":
        if not data.get("license"):
            log("medium", "PL-CL-1", "ClawHub 强制 MIT-0；缺 license 字段。")
        if not data.get("requires"):
            log("low", "PL-CL-2", "ClawHub：若脚本读 env/调二进制/联网，需在 requires 声明（一致性红线）。")
    if platform == "skillhub":
        if not data.get("license"):
            log("low", "PL-SH-1", "SkillHub：建议保留 license（GitHub 同源分发）。")


def check_body(body, data, platform, token_budget):
    lines = body.count("\n") + (1 if body else 0)
    if lines > BODY_LINE_HARD:
        log("blocker", "BD-001", f"正文 {lines} 行 > 硬上限 {BODY_LINE_HARD}；请拆 references。")
    elif lines > BODY_LINE_SOFT:
        log("medium", "BD-002", f"正文 {lines} 行 > 软上限 {BODY_LINE_SOFT}（建议拆 references）。")
    # token 预算估算（正文约 4 字符/token，粗算）
    est = len(body) // 4
    if est > token_budget:
        log("blocker", "BD-003", f"正文估算 ~{est} token > 预算 {token_budget}；请下沉细则。")
    elif est > token_budget * 0.8:
        log("low", "BD-004", f"正文估算 ~{est} token 贴近预算 {token_budget}（80% 以上）。")
    # trigger 边界检查：description/when_to_use 是否有 NOT-for / 不适用
    desc = str(data.get("description") or "") + " " + str(data.get("when_to_use") or "")
    has_boundary = bool(re.search(r"(NOT for|不适用|不触发|不用于|do NOT use|not for)", desc, re.I))
    if not has_boundary:
        log("medium", "TR-001", "frontmatter 缺触发边界（NOT-for / 不适用）——易误触发。")
    # 硬约束层检查：正文是否显式标「每轮/硬约束/HARD」
    has_hard = bool(re.search(r"(硬约束|HARD CONSTRAINT|每轮必须|must obey every)", body, re.I))
    if not has_hard:
        log("low", "ST-001", "正文未见显式「硬约束/每轮必须」层——压缩后规则易丢。")


def check_refs(body, base_dir):
    """references/assets 相对路径悬空检测。"""
    pat = re.compile(r"\((?:references|assets|scripts)/[^\s\)\'\"\]\[]+")
    for m in pat.finditer(body):
        token = m.group(0).strip("(")
        # 去掉锚点/行号
        token = token.split("#")[0]
        p = token.split("(")[0]
        rel = p.strip("`").strip()
        if not rel:
            continue
        full = os.path.join(base_dir, rel)
        if not os.path.exists(full):
            log("medium", "RF-001", f"引用路径 '{rel}' 不存在（悬空）。")


# ---------------------------------------------------------------- 主流程

def run(path, platform, token_budget, as_json):
    global _FINDINGS
    _FINDINGS = []
    if not os.path.isfile(path):
        log("blocker", "IO-001", f"文件不存在或不可读：{path}")
        if as_json:
            print(json.dumps({"verdict": "BLOCKED", "issues": _FINDINGS}, ensure_ascii=False))
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    base_dir = os.path.dirname(os.path.abspath(path))
    fm_text, body = parse_frontmatter(text)
    data = load_yaml(fm_text, path, platform)

    if data is not None:
        name = data.get("name") or ""
        check_name(os.path.basename(path), name, data, platform)
        check_body(body, data, platform, token_budget)
        check_refs(body, base_dir)

    # verdict 判定
    has_blocker = any(f["severity"] == "blocker" for f in _FINDINGS)
    has_adv = any(f["severity"] in ("medium", "low") for f in _FINDINGS)
    if has_blocker:
        verdict, code = "BLOCKED", 1
    elif has_adv:
        verdict, code = "NEEDS_FIX", 2
    else:
        verdict, code = "PASS", 0

    counts = {"blocker": 0, "medium": 0, "low": 0}
    for f in _FINDINGS:
        counts[f["severity"]] += 1

    if as_json:
        print(json.dumps({
            "verdict": verdict, "counts": counts, "issues": _FINDINGS,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== verdict: {verdict} (exit {code}) ===")
        print(f"blocker={counts['blocker']}  medium={counts['medium']}  low={counts['low']}")

    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(description="SKILL.md 机械项确定性 lint")
    ap.add_argument("target", help="SKILL.md 路径")
    ap.add_argument("--platform", default="skillhub",
                    choices=["skillhub", "clawhub", "claude", "workbuddy", "github"],
                    help="目标平台口径（默认 skillhub）")
    ap.add_argument("--token-budget", type=int, default=8000,
                    help="正文 token 预算（默认 8000）")
    ap.add_argument("--json", action="store_true", help="stdout 仅输出 JSON")
    args = ap.parse_args()
    run(args.target, args.platform, args.token_budget, args.json)


if __name__ == "__main__":
    main()
