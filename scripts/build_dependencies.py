#!/usr/bin/env python3
"""Generate the dependency map of this repository as two self-contained HTML files.

Usage: python scripts/build_dependencies.py [--out docs/review]

The language is detected from the repository: Kotlin (Gradle modules) or Python (a Home Assistant
custom integration). Writes `dependencies.html` (layers, cycles, per-topic details, index, module
reference) and `dependency-graph.html` (layered diagram). Imports are exact; "used by" and call lists
are a static approximation resolved by name through the imports.
"""

import argparse
import ast
from collections import Counter, defaultdict
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------------------------
# Repository profiles: layers (top = entry, bottom = foundation) and one-line topic descriptions.
# ---------------------------------------------------------------------------------------------
PROFILES = {
    "bridge": {
        "title": "HAAC Bridge",
        "layers": [
            ("Entry points and composition root", ["(root)"]),
            ("WebSocket API", ["api"]),
            (
                "Topic modules",
                [
                    "areas",
                    "config",
                    "disabling",
                    "entities",
                    "exposure",
                    "history",
                    "instance",
                    "schedules",
                    "services",
                ],
            ),
            ("Domain parts", ["audit"]),
            ("Foundation", ["core", "const"]),
        ],
        "notes": {
            "const": "Constants shared by all topics (`const.py`).",
            "(root)": "Setup, config flow, platform entry points, constants (`const.py`).",
            "api": "Parses haac_bridge/* requests and calls topic modules; no business logic (18.1).",
            "core": "Errors, error and reply factories, command wrapper, runtime data (18.2, 18.3).",
            "audit": "Audit log and Activity entries (concept 21).",
            "exposure": "Per-user filter of exposed entities and its revision (10.2, 10.3).",
            "schedules": "Schedules: store, planning, runner, user lifecycle, HA entities (19).",
            "disabling": "Deactivated entities per user and their effect on schedules (7.5).",
            "history": "Recorder queries for history and statistics (8.1, 8.3).",
            "services": "ServiceCallFactory and execution of allowed services (11.4).",
            "entities": "Descriptors, hidden attributes and the live state subscription (11.3).",
            "config": "YAML and UI user entries, schema, repairs (10.2).",
            "areas": "Area catalog for the app's import (6).",
            "instance": "Addresses the app may reach this instance by (4).",
        },
    },
    "android": {
        "title": "HAAC Android",
        "layers": [
            ("App", [":app"]),
            (
                "Features",
                [
                    ":feature:entities",
                    ":feature:instance",
                    ":feature:layout",
                    ":feature:notifications",
                    ":feature:onboarding",
                    ":feature:schedules",
                    ":feature:settings",
                ],
            ),
            ("Core services", [":core:database", ":core:network", ":core:security"]),
            ("Foundation", [":core:common", ":core:error"]),
        ],
        "notes": {
            ":app": "Activity, navigation, app lock, shortcuts, crash marker, start routing.",
            ":feature:entities": "Entity picker, rooms and tiles, controls, history, deactivation (7, 8).",
            ":feature:instance": "Instance bar and switching (4).",
            ":feature:layout": "Homes, levels and rooms, area import (6).",
            ":feature:notifications": "Notification list (9).",
            ":feature:onboarding": "Server address, login, first sync (4, 5).",
            ":feature:schedules": "Schedules: list, editor, detail, run log (19).",
            ":feature:settings": "Addresses, security, diagnostics, about (4, 5).",
            ":core:database": "Room database, DAOs, DataStore settings (12).",
            ":core:network": "HTTPS and WebSocket, TLS pinning, discovery, demo bridge (3, 4, 11).",
            ":core:security": "Keystore keys, token store, fingerprint unlock (5).",
            ":core:common": "Theme, shared UI, entity constants, dispatchers.",
            ":core:error": "ErrorCode, HaacException, ErrorFactory, ErrorReporter (17.3).",
            "build-logic": "Convention plugins and the code index generator.",
        },
    },
}

BRANCH_PY = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
    ast.comprehension,
    ast.AsyncFor,
    ast.Assert,
)


def first_line(text):
    """Return the first sentence-ish line of a docstring."""
    if not text:
        return ""
    line = text.strip().splitlines()[0].strip()
    return line[:200]


# ---------------------------------------------------------------------------------------------
# Python analysis
# ---------------------------------------------------------------------------------------------
def py_cc(node):
    """McCabe complexity of one function."""
    total = 1
    for sub in ast.walk(node):
        if isinstance(sub, BRANCH_PY):
            total += 1
        elif isinstance(sub, ast.BoolOp):
            total += len(sub.values) - 1
        elif isinstance(sub, ast.Match):
            total += len(sub.cases)
    return total


def analyse_python():
    """Return (modules, packages) for the integration under custom_components."""
    base = next((ROOT / "custom_components").glob("*"))
    pkg_name = base.name
    modules = {}
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(base)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1][:-3]
        mid = ".".join(parts) if parts else "(root)"
        if mid == "(root)" and rel.name == "__init__.py":
            mid = "__init__"
        package = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        code = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
        imports, imported_names, type_imports = set(), {}, set()
        here = list(rel.parts[:-1])
        type_only = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Name)
                and node.test.id == "TYPE_CHECKING"
            ):
                type_only.update(id(sub) for stmt in node.body for sub in ast.walk(stmt))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                anchor = here[: len(here) - (node.level - 1)] if node.level > 1 else here
                target = anchor + (node.module.split(".") if node.module else [])
                for alias in node.names:
                    cand = ".".join([*target, alias.name])
                    imported_names[alias.asname or alias.name] = (".".join(target), cand)
                (type_imports if id(node) in type_only else imports).add(".".join(target))
        entries = []
        classes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body_names = {
                    n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                    for n in ast.walk(node)
                    if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
                }
                signature = ast.unparse(node.args)
                entries.append(
                    {
                        "kind": "function",
                        "name": node.name,
                        "line": node.lineno,
                        "length": (node.end_lineno or node.lineno) - node.lineno + 1,
                        "cc": py_cc(node),
                        "signature": f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({signature})",
                        "doc": first_line(ast.get_docstring(node)),
                        "calls": sorted(body_names),
                    }
                )
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                entries.append(
                    {
                        "kind": "class",
                        "name": node.name,
                        "line": node.lineno,
                        "length": (node.end_lineno or node.lineno) - node.lineno + 1,
                        "cc": 0,
                        "signature": f"class {node.name}",
                        "doc": first_line(ast.get_docstring(node)),
                        "calls": [],
                    }
                )
        modules[mid] = {
            "id": mid,
            "package": package,
            "path": path.relative_to(ROOT).as_posix(),
            "doc": first_line(ast.get_docstring(tree)),
            "lines": len(lines),
            "code": code,
            "entries": entries,
            "raw_imports": imports,
            "raw_type": type_imports,
        }
        if mid == "const":
            modules[mid]["package"] = "const"
    # resolve imports to module ids
    ids = set(modules)
    for mod in modules.values():
        deps = set()
        for imp in mod["raw_imports"]:
            target = imp if imp in ids else (imp + "" if imp else "")
            if not target:
                target = "(root)"
            while target and target not in ids and "." in target:
                target = target.rsplit(".", 1)[0]
            if target in ids and target != mod["id"]:
                deps.add(target)
            elif target == "" and "(root)" in ids:
                pass
        mod["deps"] = sorted(deps)
        mod["type_deps"] = sorted(
            {_resolve(t, ids) for t in mod["raw_type"]} - {None, mod["id"]} - deps
        )
        del mod["raw_imports"], mod["raw_type"]
    return modules, pkg_name


def _resolve(target, ids):
    """Return the module id an import path points to, or None."""
    while target and target not in ids and "." in target:
        target = target.rsplit(".", 1)[0]
    return target if target in ids else None


# ---------------------------------------------------------------------------------------------
# Kotlin analysis
# ---------------------------------------------------------------------------------------------
KT_DECL = re.compile(
    r"^(?P<indent>[ ]*)(?P<mods>(?:(?:public|private|internal|protected|override|suspend|data|sealed|"
    r"abstract|open|inline|operator|infix|tailrec|inner|enum|annotation|value|fun|const|lateinit|"
    r"companion|expect|actual|external)\s+)*)(?P<kind>class|interface|object|fun)\b\s*"
    r"(?P<rest>.*)$"
)
KT_KEYWORDS = re.compile(r"\b(if|for|while|catch)\b|&&|\|\||\?:")
KT_WHEN = re.compile(r"\bwhen\b")


def kt_module_of(path):
    """Return the Gradle module for a source path."""
    parts = path.relative_to(ROOT).parts
    if parts[0] in ("core", "feature"):
        return f":{parts[0]}:{parts[1]}"
    if parts[0] == "app":
        return ":app"
    return parts[0]


def kt_split(source):
    """Return declaration entries with their bodies from one Kotlin file."""
    lines = source.splitlines()
    entries = []
    for idx, line in enumerate(lines):
        match = KT_DECL.match(line)
        if not match or False:
            continue
        kind = match.group("kind")
        rest = match.group("rest")
        mods = match.group("mods")
        if kind == "fun" and rest.startswith("interface"):
            kind, rest = "interface", rest[len("interface") :].strip()
        if kind == "object" and re.match(r"\s*:", rest) and "object :" in line:
            continue
        name = re.match(r"(?:<[^>]*>\s*)?(?:[\w.<>?, ]+\.)?(\w+)", rest)
        if not name:
            continue
        indent = len(match.group("indent"))
        end = idx
        for j in range(idx + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                end = j
                continue
            ind = len(nxt) - len(nxt.lstrip(" "))
            if ind > indent or (
                ind == indent
                and nxt.lstrip().startswith(
                    ("}", ")", ".", "?:", "&&", "||", "+", "-", "else", ":", "->")
                )
            ):
                end = j
            else:
                break
        while end > idx and not lines[end].strip():
            end -= 1
        # KDoc above
        doc = ""
        k = idx - 1
        while k >= 0 and (lines[k].lstrip().startswith("@") or not lines[k].strip()):
            k -= 1
        if k >= 0 and lines[k].strip().endswith("*/"):
            top = k
            while top >= 0 and "/**" not in lines[top]:
                top -= 1
            text = " ".join(
                re.sub(r"^\s*(/\*\*|\*/|\*)\s?", "", ln).strip() for ln in lines[top : k + 1]
            )
            doc = re.sub(r"\s+", " ", text.replace("/**", "").replace("*/", "")).strip()[:200]
        body = "\n".join(lines[idx : end + 1])
        cc = (
            1 + len(KT_KEYWORDS.findall(body)) + 2 * len(KT_WHEN.findall(body))
            if kind == "fun"
            else 0
        )
        calls = sorted(
            set(re.findall(r"\b([A-Za-z_]\w*)\s*[({]", body)) - {name.group(1)} - KT_STOP
        )
        entries.append(
            {
                "kind": "function" if kind == "fun" else "class",
                "name": name.group(1),
                "line": idx + 1,
                "length": end - idx + 1,
                "cc": cc,
                "indent": indent,
                "signature": (mods + kind + " " + rest).strip()[:160].rstrip("{ ").strip(),
                "doc": doc,
                "calls": calls if kind == "fun" else [],
            }
        )
    return entries


KT_STOP = {
    "if",
    "for",
    "while",
    "when",
    "catch",
    "try",
    "return",
    "listOf",
    "mapOf",
    "setOf",
    "emptyList",
    "emptyMap",
    "emptySet",
    "mutableListOf",
    "mutableMapOf",
    "mutableSetOf",
    "buildList",
    "buildMap",
    "also",
    "let",
    "apply",
    "run",
    "with",
    "takeIf",
    "require",
    "check",
    "error",
    "launch",
    "async",
    "withContext",
    "flow",
    "emit",
    "collect",
    "map",
    "filter",
    "first",
    "forEach",
    "mapNotNull",
    "joinToString",
    "copy",
    "to",
    "lazy",
    "remember",
    "mutableStateOf",
    "derivedStateOf",
    "else",
    "Modifier",
    "stringResource",
    "Text",
    "Column",
    "Row",
    "Box",
    "Spacer",
    "Icon",
    "put",
    "add",
    "get",
}


def analyse_kotlin():
    """Return (modules, None) where a module is one Kotlin package of one Gradle module."""
    packages = {}
    for path in sorted(ROOT.rglob("*.kt")):
        if any(part in ("build", ".git", ".gradle") for part in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "/src/test/" in rel or "/src/androidTest/" in rel or "/src/debug/" in rel:
            continue
        source = path.read_text(encoding="utf-8")
        match = re.search(r"^package\s+([\w.]+)", source, re.M)
        if not match:
            continue
        pkg = match.group(1)
        gradle = kt_module_of(path)
        mod = packages.setdefault(
            pkg,
            {
                "id": pkg.replace("com.stacknoise.haac.", ""),
                "package": gradle,
                "paths": set(),
                "doc": "",
                "lines": 0,
                "code": 0,
                "entries": [],
                "raw": set(),
                "full": pkg,
            },
        )
        mod["paths"].add(path.parent.relative_to(ROOT).as_posix())
        lines = source.splitlines()
        mod["lines"] += len(lines)
        mod["code"] += sum(
            1
            for ln in lines
            if ln.strip() and not ln.strip().startswith(("//", "*", "/*", "import ", "package "))
        )
        mod["raw"].update(re.findall(r"^import\s+([\w.]+)", source, re.M))
        for entry in kt_split(source):
            entry["file"] = path.name
            mod["entries"].append(entry)
        if not mod["doc"]:
            for entry in kt_split(source):
                if entry["doc"] and entry["indent"] == 0:
                    mod["doc"] = entry["doc"]
                    break
    names = sorted(packages, key=len, reverse=True)
    out = {}
    for pkg, mod in packages.items():
        deps = set()
        for imp in mod["raw"]:
            for cand in names:
                if imp.startswith(cand + ".") or imp == cand:
                    if cand != pkg:
                        deps.add(packages[cand]["id"])
                    break
        mod["deps"] = sorted(deps)
        mod["path"] = ", ".join(sorted(mod["paths"]))[:160]
        for key in ("paths", "raw", "full"):
            del mod[key]
        out[mod["id"]] = mod
    return out, None


# ---------------------------------------------------------------------------------------------
# Common post-processing
# ---------------------------------------------------------------------------------------------
def sccs(nodes, edges):
    """Strongly connected components with more than one node (Tarjan)."""
    graph = defaultdict(list)
    for src, dst in edges:
        graph[src].append(dst)
    index, low, stack, on, result, counter = {}, {}, [], set(), [], [0]

    def visit(node):
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on.add(node)
        for nxt in graph[node]:
            if nxt not in index:
                visit(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on:
                low[node] = min(low[node], index[nxt])
        if low[node] == index[node]:
            comp = []
            while True:
                item = stack.pop()
                on.discard(item)
                comp.append(item)
                if item == node:
                    break
            if len(comp) > 1:
                result.append(sorted(comp))

    sys.setrecursionlimit(10000)
    for node in nodes:
        if node not in index:
            visit(node)
    return result


def build():
    """Collect everything the two pages need into one JSON-serialisable dictionary."""
    is_python = (ROOT / "custom_components").exists()
    profile = PROFILES["bridge" if is_python else "android"]
    modules, _pkg_name = analyse_python() if is_python else analyse_kotlin()
    layer_of = {}
    for number, (_, members) in enumerate(profile["layers"], 1):
        for member in members:
            layer_of[member] = number
    for mod in modules.values():
        mod["layer"] = layer_of.get(mod["package"], 0)
    # resolve calls
    by_name = defaultdict(list)
    for mod in modules.values():
        for entry in mod["entries"]:
            if entry["kind"] == "function":
                by_name[entry["name"]].append((mod["id"], entry))
    for mod in modules.values():
        visible = {mod["id"], *mod["deps"]}
        for entry in mod["entries"]:
            resolved = []
            for call in entry["calls"]:
                cands = [
                    (m, e) for m, e in by_name.get(call, []) if m in visible and e is not entry
                ]
                if cands:
                    resolved.append((cands[0][0], cands[0][1]["name"], len(cands) > 1))
            entry["callees"] = resolved[:40]
    callers = defaultdict(list)
    for mod in modules.values():
        for entry in mod["entries"]:
            for target_mod, name, approx in entry["callees"]:
                callers[(target_mod, name)].append((mod["id"], entry["name"], approx))
    for mod in modules.values():
        for entry in mod["entries"]:
            entry["callers"] = callers.get((mod["id"], entry["name"]), [])[:40]
            entry.pop("calls", None)
            entry.pop("indent", None)
    # packages
    packages = defaultdict(
        lambda: {
            "modules": [],
            "lines": 0,
            "code": 0,
            "functions": 0,
            "classes": 0,
            "cc": 0,
            "maxcc": 0,
            "maxfn": "",
        }
    )
    for mod in modules.values():
        pk = packages[mod["package"]]
        pk["modules"].append(mod["id"])
        pk["lines"] += mod["lines"]
        pk["code"] += mod["code"]
        for entry in mod["entries"]:
            if entry["kind"] == "function":
                pk["functions"] += 1
                pk["cc"] += entry["cc"]
                if entry["cc"] > pk["maxcc"]:
                    pk["maxcc"], pk["maxfn"] = entry["cc"], f"{mod['id']}.{entry['name']}"
            else:
                pk["classes"] += 1
    pkg_edges = Counter()
    for mod in modules.values():
        for dep in mod["deps"]:
            a, b = mod["package"], modules[dep]["package"]
            if a != b:
                pkg_edges[(a, b)] += 1
    for name, pk in packages.items():
        pk["layer"] = layer_of.get(name, 0)
        pk["note"] = profile["notes"].get(name, "")
        pk["ca"] = sum(1 for (a, b) in pkg_edges if b == name)
        pk["ce"] = sum(1 for (a, b) in pkg_edges if a == name)
    mod_edges = [(m["id"], d) for m in modules.values() for d in m["deps"]]
    data = {
        "title": profile["title"],
        "lang": "python" if is_python else "kotlin",
        "layers": [
            {"n": i, "name": name, "members": members}
            for i, (name, members) in enumerate(profile["layers"], 1)
        ],
        "modules": list(modules.values()),
        "packages": [dict(id=k, **v) for k, v in packages.items()],
        "pkg_edges": [{"s": a, "t": b, "n": n} for (a, b), n in pkg_edges.items()],
        "mod_cycles": sccs(list(modules), mod_edges),
        "pkg_cycles": sccs(list(packages), list(pkg_edges)),
        "upward": [
            {"s": a, "t": b, "n": n, "sl": layer_of.get(a, 0), "tl": layer_of.get(b, 0)}
            for (a, b), n in pkg_edges.items()
            if layer_of.get(a, 0) and layer_of.get(b, 0) and layer_of[a] > layer_of[b]
        ],
        "sideways": [
            {"s": a, "t": b, "n": n}
            for (a, b), n in pkg_edges.items()
            if layer_of.get(a)
            and layer_of.get(a) == layer_of.get(b)
            and not is_python
            and a.startswith(":feature")
        ],
    }
    return data


# ---------------------------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------------------------
CSS = """
:root{--bg:#fff;--fg:#1c1e21;--muted:#5f6670;--card:#f5f6f8;--line:#d9dce1;--accent:#0b63ce;--warn:#b45309;--ok:#1a7f37;--bad:#c0392b;--code:#eef0f3;--out:#d9730d;--in:#1c8a4a}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e6e8eb;--muted:#9aa3ad;--card:#1d2026;--line:#323741;--accent:#6aa9ff;--warn:#e3a008;--ok:#4ac26b;--bad:#ff6b5b;--code:#262a31;--out:#f0a050;--in:#5fcf8a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none;word-break:break-word}a:hover{text-decoration:underline}
code{font:13px/1.45 ui-monospace,Consolas,monospace;background:var(--code);border-radius:4px;padding:1px 4px;word-break:break-word}
.muted{color:var(--muted)}.bad{color:var(--bad);font-weight:600}.ok{color:var(--ok)}
"""

PAGE_DETAILS = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ dependency map</title><style>__CSS__
main{max-width:1100px;margin:0 auto;padding:12px 16px 80px}
h1{font-size:1.5rem;margin:.6em 0 .2em}h2{font-size:1.25rem;margin:1.6em 0 .5em;border-bottom:1px solid var(--line);padding-bottom:.2em}h3{font-size:1.05rem;margin:1.2em 0 .3em}h4{font-size:.95rem;margin:.9em 0 .2em}
nav.top{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:6px 16px;z-index:5;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
nav.top input{flex:1 1 200px;min-width:0;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);font:inherit}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}
.card:target,.fn:target{outline:2px solid var(--accent);outline-offset:2px}
.fn{border-left:3px solid var(--line);padding:2px 0 2px 10px;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto}th,td{border:1px solid var(--line);padding:3px 6px;text-align:left;vertical-align:top}th{background:var(--card);cursor:pointer}td.n,th.n{text-align:right}
.layer{border:1px dashed var(--line);border-radius:10px;padding:8px 12px;margin:10px 0}.layer h4{margin:0 0 6px}
.box{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 14px;margin:3px;cursor:pointer;font:inherit;color:inherit}
.cols{columns:2 280px;column-gap:24px}.cols>*{break-inside:avoid}ul.tight{margin:.2em 0;padding-left:1.2em}
.hide{display:none!important}details>summary{cursor:pointer}
</style></head><body>
<nav class="top"><a href="#map"><b>Map</b></a><a href="#layers">Layers</a><a href="#cycles">Cycles</a><a href="#details">Details</a><a href="#index">Index</a><a href="#modules">Modules</a><a href="dependency-graph.html">Graph</a>
<input id="q" placeholder="Filter the index and modules (name, class, function)"></nav>
<main id="app"></main>
<script>const D=__DATA__;
const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const mid=m=>'m-'+m,fid=(m,n)=>'f-'+m+':'+n,byId=Object.fromEntries(D.modules.map(m=>[m.id,m]));
const pk=Object.fromEntries(D.packages.map(p=>[p.id,p]));
const usedBy={};D.modules.forEach(m=>m.deps.forEach(d=>(usedBy[d]=usedBy[d]||[]).push(m.id)));
const nfn=D.modules.reduce((a,m)=>a+m.entries.filter(e=>e.kind==='function').length,0),ncl=D.modules.reduce((a,m)=>a+m.entries.filter(e=>e.kind==='class').length,0);
const ml=m=>`<a href="#${mid(m)}">${esc(m)}</a>`;
let h=`<h1 id="map">${esc(D.title)}: dependency map</h1><p class="muted">Generated by <code>scripts/build_dependencies.py</code> from the sources: ${D.modules.length} ${D.lang==='python'?'Python modules':'Kotlin packages'}, ${ncl} classes, ${nfn} functions. <b>Static approximation</b>: imports are exact; calls and «used by» lists are resolved by name through the imports, so callbacks, dynamic dispatch and calls on objects of unknown type are missing, and entries marked <code>~</code> are matched by name only. CC is McCabe${D.lang==='python'?'':' (approximation from keywords; each <code>when</code> counts 2)'}.</p>`;
h+=`<h2 id="layers">Layers</h2><p class="muted">Target direction: each layer uses only layers below it. Click a box for the notes.</p>`;
D.layers.forEach(l=>{h+=`<div class="layer"><h4>${l.n}. ${esc(l.name)}</h4>`+l.members.map(p=>`<a class="box" href="#t-${esc(p)}">${esc(p)}${pk[p]?` <span class="muted">${pk[p].modules.length} · ${pk[p].code} LOC</span>`:''}</a>`).join('')+'</div>'});
h+=`<h3>Imports against the layer direction</h3>`;
h+=D.upward.length?`<table><tr><th>from</th><th>to</th><th class="n">module imports</th></tr>${D.upward.map(u=>`<tr><td class="bad">${esc(u.s)} (layer ${u.sl})</td><td>${esc(u.t)} (layer ${u.tl})</td><td class="n">${u.n}</td></tr>`).join('')}</table>`:'<p class="ok">None.</p>';
if(D.sideways.length)h+=`<h3>Feature imports another feature</h3><table>${D.sideways.map(u=>`<tr><td class="bad">${esc(u.s)}</td><td>${esc(u.t)}</td><td class="n">${u.n}</td></tr>`).join('')}</table>`;
h+=`<h2 id="cycles">Dependency cycles</h2>`;
const cyc=(t,list)=>list.length?`<h3>${t}</h3>`+list.map(c=>`<div class="card bad">${c.map(esc).join(' ⇄ ')}</div>`).join(''):`<p class="ok">${t}: none.</p>`;
h+=cyc('Between '+(D.lang==='python'?'topic packages':'Gradle modules'),D.pkg_cycles)+cyc('Between '+(D.lang==='python'?'modules':'Kotlin packages'),D.mod_cycles);
h+=`<h2 id="details">Per topic</h2>`;
D.packages.sort((a,b)=>a.layer-b.layer||a.id.localeCompare(b.id)).forEach(p=>{
 const out=D.pkg_edges.filter(e=>e.s===p.id).map(e=>e.t),inn=D.pkg_edges.filter(e=>e.t===p.id).map(e=>e.s);
 const inst=p.ca+p.ce?(p.ce/(p.ca+p.ce)).toFixed(2):'0.00';
 h+=`<section class="card" id="t-${esc(p.id)}"><h3>${esc(p.id)} <span class="muted">layer ${p.layer||'?'}</span></h3><p>${esc(p.note)}</p>
 <p class="muted">${p.modules.length} modules · ${p.code} code lines · ${p.classes} classes · ${p.functions} functions · CC total ${p.cc} · most complex <code>${esc(p.maxfn)}</code> (${p.maxcc}) · Ca ${p.ca} · Ce ${p.ce} · instability ${inst}</p>
 <div class="cols"><div><h4>Uses</h4>${out.length?'<ul class="tight">'+out.map(x=>`<li><a href="#t-${esc(x)}">${esc(x)}</a></li>`).join('')+'</ul>':'<span class="muted">nothing</span>'}</div>
 <div><h4>Used by</h4>${inn.length?'<ul class="tight">'+inn.map(x=>`<li><a href="#t-${esc(x)}">${esc(x)}</a></li>`).join('')+'</ul>':'<span class="muted">nothing</span>'}</div></div>
 <p><b>Modules</b> ${p.modules.map(ml).join(', ')}</p></section>`});
h+=`<h2 id="index">Index</h2><table id="idx"><tr><th>name</th><th>kind</th><th>module</th><th class="n">line</th><th class="n">len</th><th class="n">CC</th><th>summary</th></tr></table>`;
h+=`<h2 id="modules">Module reference</h2><div id="mods"></div>`;
$('#app').innerHTML=h;
const rows=[];D.modules.forEach(m=>m.entries.forEach(e=>rows.push([e,m])));
rows.sort((a,b)=>a[0].name.localeCompare(b[0].name));
$('#idx').insertAdjacentHTML('beforeend',rows.map(([e,m])=>`<tr data-k="${esc((e.name+' '+m.id+' '+e.doc).toLowerCase())}"><td><a href="#${e.kind==='function'?fid(m.id,e.name):mid(m.id)}">${esc(e.name)}</a></td><td>${e.kind}</td><td>${ml(m.id)}</td><td class="n">${e.line}</td><td class="n">${e.length}</td><td class="n ${e.cc>=15?'bad':''}">${e.kind==='function'?e.cc:''}</td><td class="muted">${esc(e.doc)}</td></tr>`).join(''));
const callList=l=>l.map(([m,n,ap])=>`<a href="#${fid(m,n)}">${esc(m)}.${esc(n)}</a>${ap?'<span class="muted">~</span>':''}`).join(', ')||'<span class="muted">none</span>';
$('#mods').innerHTML=D.modules.map(m=>`<section class="card mod" id="${mid(m.id)}" data-k="${esc((m.id+' '+m.entries.map(e=>e.name).join(' ')).toLowerCase())}"><h3>${esc(m.id)} <span class="muted">${esc(m.path)}</span></h3><p>${esc(m.doc)}</p>
<p class="muted">${m.lines} lines (${m.code} code), ${m.entries.filter(e=>e.kind==='class').length} classes, ${m.entries.filter(e=>e.kind==='function').length} functions/methods, layer ${m.layer||'?'}</p>
<div class="cols"><div><h4>Depends on</h4>${m.deps.length?'<ul class="tight">'+m.deps.map(d=>`<li>${ml(d)}</li>`).join('')+'</ul>':'<span class="muted">nothing</span>'}</div>
${(m.type_deps||[]).length?`<p class="muted">Type-only imports (TYPE_CHECKING, no runtime dependency): ${m.type_deps.map(ml).join(', ')}</p>`:''}<div><h4>Used by</h4>${(usedBy[m.id]||[]).length?'<ul class="tight">'+usedBy[m.id].map(d=>`<li>${ml(d)}</li>`).join('')+'</ul>':'<span class="muted">nothing</span>'}</div></div>
${m.entries.filter(e=>e.kind==='function').map(e=>`<div class="fn" id="${fid(m.id,e.name)}"><code>${esc(e.name)}</code> <span class="muted">line ${e.line}, ${e.length} lines, CC ${e.cc}</span><br><code>${esc(e.signature)}</code><br>${esc(e.doc)}<details><summary>Callers ${e.callers.length} / callees ${e.callees.length}</summary><div><b>Called by</b> ${callList(e.callers)}</div><div><b>Calls</b> ${callList(e.callees)}</div></details></div>`).join('')}</section>`).join('');
$('#q').oninput=ev=>{const q=ev.target.value.toLowerCase();document.querySelectorAll('#idx tr[data-k],.mod').forEach(r=>r.classList.toggle('hide',q&&!r.dataset.k.includes(q)))};
$('#idx').querySelectorAll('th').forEach((t,i)=>t.onclick=()=>{const rs=[...document.querySelectorAll('#idx tr[data-k]')];const num=t.classList.contains('n');rs.sort((a,b)=>{const x=a.children[i].textContent,y=b.children[i].textContent;return num?(+y)-(+x):x.localeCompare(y)});rs.forEach(r=>r.parentNode.appendChild(r))});
</script></body></html>"""

PAGE_GRAPH = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ dependency graph</title><style>__CSS__
header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:12px;align-items:center}h1{font-size:17px;margin:0}
.tabs button,input{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:5px 10px}.tabs button.on{border-color:var(--accent);color:var(--accent)}
main{display:grid;grid-template-columns:1fr 340px;min-height:calc(100vh - 56px)}@media(max-width:900px){main{grid-template-columns:1fr}}
#stage{overflow:auto;padding:8px;min-height:60vh}aside{border-left:1px solid var(--line);padding:12px 16px;background:var(--card);overflow:auto;font-size:13px}
aside h2{font-size:15px;margin:0 0 4px}aside ul{margin:4px 0 12px;padding-left:18px}
svg text{fill:var(--fg);font:11px system-ui,sans-serif;pointer-events:none}svg .band{fill:none;stroke:var(--line);stroke-dasharray:4 4}svg .bl{fill:var(--muted);font-size:11px}
svg .node rect{fill:var(--card);stroke:var(--line);stroke-width:1.2}svg .node{cursor:pointer}svg .node:hover rect{stroke:var(--accent)}
svg .node.sel rect{stroke:var(--fg);stroke-width:2.4}svg .node.out rect{stroke:var(--out);stroke-width:2.2}svg .node.in rect{stroke:var(--in);stroke-width:2.2}svg .node.cyc rect{stroke:var(--bad)}svg .node.dim{opacity:.25}
svg path.edge{fill:none;stroke:var(--line);stroke-width:1;opacity:.55}svg path.edge.up{stroke:var(--bad);stroke-dasharray:4 3;opacity:.9}svg path.edge.out{stroke:var(--out);stroke-width:2;opacity:1}svg path.edge.in{stroke:var(--in);stroke-width:2;opacity:1}svg path.edge.hide{display:none}
.legend span{display:inline-block;width:18px;height:3px;vertical-align:middle;margin:0 4px 0 12px}
</style></head><body>
<header><h1>__TITLE__ dependency graph</h1><div class="tabs"><button data-v="p" class="on">__PKG__</button><button data-v="m">Modules</button></div>
<label>Filter <input id="f" placeholder="name" size="16"></label><label><input type="checkbox" id="all"> all edges</label>
<span class="legend muted"><span style="background:var(--out)"></span>imports <span style="background:var(--in)"></span>imported by <span style="background:var(--bad)"></span>against layers / cycle</span>
<a href="dependencies.html" class="muted">&larr; details</a></header>
<main><div id="stage"></div><aside id="side"><p class="muted">Click a node: its imports (orange) and importers (green) are highlighted and listed. Red nodes are in a cycle; red dashed arrows go against the layer direction. Arrows point from the importing node to the imported one.</p></aside></main>
<script>const D=__DATA__;const NS='http://www.w3.org/2000/svg',$=s=>document.querySelector(s);
let view='p',sel=null;
const cycP=new Set(D.pkg_cycles.flat()),cycM=new Set(D.mod_cycles.flat());
function model(){
 if(view==='p'){return{nodes:D.packages.map(p=>({id:p.id,label:p.id.replace(/^:/,''),sub:p.modules.length+' modules · '+p.code+' LOC',layer:p.layer||D.layers.length+1,g:'',cyc:cycP.has(p.id)})),edges:D.pkg_edges.map(e=>[e.s,e.t])}}
 return{nodes:D.modules.map(m=>({id:m.id,label:m.id.split('.').slice(-2).join('.'),sub:m.code+' LOC · '+m.package,layer:m.layer||D.layers.length+1,g:m.package,cyc:cycM.has(m.id)})),edges:D.modules.flatMap(m=>m.deps.map(d=>[m.id,d]))}}
function draw(){
 const {nodes,edges}=model(),W=Math.max($('#stage').clientWidth-16,700),bw=view==='p'?148:150,bh=36,gx=10,gy=10,lw=200,per=Math.max(1,Math.floor((W-lw-20)/(bw+gx)));
 const q=$('#f').value.toLowerCase(),pos={};let y=6;const parts=[];const layers=[...D.layers.map(l=>l.name),'Other'];
 layers.forEach((name,i)=>{const items=nodes.filter(n=>n.layer===i+1).sort((a,b)=>a.g.localeCompare(b.g)||a.id.localeCompare(b.id));if(!items.length)return;
  const rows=Math.ceil(items.length/per),h=rows*(bh+gy)+gy;parts.push(`<rect class="band" x="2" y="${y}" width="${W-4}" height="${h}" rx="10"/><text class="bl" x="12" y="${y+18}">${name}</text>`);
  items.forEach((n,k)=>{pos[n.id]={x:lw+(k%per)*(bw+gx),y:y+gy+Math.floor(k/per)*(bh+gy)}});y+=h+10});
 const idx=Object.fromEntries(nodes.map(n=>[n.id,n])),layerOf=id=>idx[id].layer;
 const showAll=$('#all').checked||view==='p';
 let svg=`<svg xmlns="${NS}" width="${W}" height="${y+6}">`+parts.join('');
 const path=(a,b)=>{const pa=pos[a],pb=pos[b];if(!pa||!pb)return'';const down=pb.y>=pa.y;const x1=pa.x+bw/2,y1=pa.y+(down?bh:0),x2=pb.x+bw/2,y2=pb.y+(down?0:bh),my=(y1+y2)/2;return`M${x1} ${y1}C${x1} ${my} ${x2} ${my} ${x2} ${y2}`};
 edges.forEach(([a,b],i)=>{if(!pos[a]||!pos[b])return;const up=layerOf(a)>layerOf(b)&&layerOf(a)<=D.layers.length&&layerOf(b)<=D.layers.length;svg+=`<path class="edge ${up?'up':''} ${showAll||up?'':'hide'}" data-a="${a}" data-b="${b}" d="${path(a,b)}"/>`});
 nodes.forEach(n=>{const p=pos[n.id];if(!p)return;const m=!q||n.id.toLowerCase().includes(q);svg+=`<g class="node ${n.cyc?'cyc':''} ${m?'':'dim'}" data-id="${n.id}" transform="translate(${p.x},${p.y})"><title>${n.id}</title><rect width="${bw}" height="${bh}" rx="6"/><text x="8" y="15">${n.label.length>24?n.label.slice(0,23)+'…':n.label}</text><text x="8" y="28" style="fill:var(--muted);font-size:10px">${n.sub.length>28?n.sub.slice(0,27)+'…':n.sub}</text></g>`});
 $('#stage').innerHTML=svg+'</svg>';
 $('#stage').querySelectorAll('.node').forEach(g=>g.onclick=()=>{sel=g.dataset.id;mark(edges)});
 if(sel)mark(edges);
}
function mark(edges){
 const outs=new Set(),ins=new Set();edges.forEach(([a,b])=>{if(a===sel)outs.add(b);if(b===sel)ins.add(a)});
 document.querySelectorAll('.node').forEach(g=>{const id=g.dataset.id;g.classList.toggle('sel',id===sel);g.classList.toggle('out',outs.has(id));g.classList.toggle('in',ins.has(id))});
 document.querySelectorAll('path.edge').forEach(p=>{const o=p.dataset.a===sel,i=p.dataset.b===sel;p.classList.toggle('out',o);p.classList.toggle('in',i);if(!$('#all').checked&&view==='m')p.classList.toggle('hide',!(o||i)&&!p.classList.contains('up'))});
 const L=s=>[...s].sort().map(x=>`<li>${x}</li>`).join('')||'<li class="muted">nothing</li>';
 let extra='';if(view==='p'){const p=D.packages.find(x=>x.id===sel);if(p)extra=`<p class="muted">${p.note||''}<br>${p.code} LOC · ${p.classes} classes · ${p.functions} functions · CC ${p.cc} · Ca ${p.ca} · Ce ${p.ce}</p>`}
 else{const m=D.modules.find(x=>x.id===sel);if(m)extra=`<p class="muted">${m.doc||''}<br>${m.code} LOC</p>`}
 $('#side').innerHTML=`<h2>${sel}</h2>${extra}<b style="color:var(--out)">Imports (${outs.size})</b><ul>${L(outs)}</ul><b style="color:var(--in)">Imported by (${ins.size})</b><ul>${L(ins)}</ul>`;
}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{view=b.dataset.v;sel=null;document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x===b));draw()});
$('#f').oninput=draw;$('#all').onchange=draw;addEventListener('resize',draw);draw();
</script></body></html>"""


def main():
    """Write both HTML files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "docs" / "review"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if the files in --out differ from a fresh run",
    )
    args = parser.parse_args()
    out = Path(args.out)
    if not args.check:
        out.mkdir(parents=True, exist_ok=True)
    data = build()
    light = dict(
        data, modules=[{k: v for k, v in m.items() if k != "entries"} for m in data["modules"]]
    )
    blobs = {
        name: json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
        for name, payload in (("dependencies.html", data), ("dependency-graph.html", light))
    }
    pkg_label = "Packages" if data["lang"] == "python" else "Gradle modules"
    pages = {}
    for name, template in (
        ("dependencies.html", PAGE_DETAILS),
        ("dependency-graph.html", PAGE_GRAPH),
    ):
        page = (
            template.replace("__CSS__", CSS)
            .replace("__TITLE__", html.escape(data["title"]))
            .replace("__PKG__", pkg_label)
            .replace("__DATA__", blobs[name])
        )
        pages[name] = page
    if args.check:
        stale = [name for name, page in pages.items() if not _same(out / name, page)]
        if stale:
            print(f"Outdated: {', '.join(stale)}. Run: python scripts/build_dependencies.py")
            sys.exit(1)
        print("Dependency map is up to date.")
        return
    for name, page in pages.items():
        with (out / name).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(page)
    print(f"{len(data['modules'])} modules, {len(data['packages'])} packages -> {out}")


def _same(path, page):
    """Return True if the file holds exactly `page` (line endings ignored)."""
    if not path.exists():
        return False
    return path.read_bytes().replace(b"\r\n", b"\n") == page.encode("utf-8")


if __name__ == "__main__":
    main()
