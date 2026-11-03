#!/usr/bin/env python3
"""Generate the code documentation of this repository as one self-contained HTML page.

Usage: python scripts/build_code_doku.py [--out docs/code-doku] [--check]

The page follows the code documentation standard (Holzbedarf style): an explorer
(project, namespace, type, method) with metrics, the doc comment and the source text of
every type, plus a dependency map between namespaces and types. The language is detected
from the repository: Kotlin (Gradle modules) or Python (a Home Assistant custom integration).
Metrics are approximations of a source scanner, not a compiler analysis. The output is
deterministic: the same sources always give the same file. With `--check` nothing is written;
the exit code is 1 when the committed page is outdated.
"""

import argparse
import ast
from bisect import bisect_right
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dependencies import PROFILES, ROOT, py_cc

TEMPLATE = Path(__file__).resolve().parent / "code_doku_template.html"
MAX_DOC = 700
MAX_SIG = 240
LAYER_COLORS = [
    ("#17878c", "#4cc3c8"),
    ("#b8741a", "#e0a24d"),
    ("#2c6fa3", "#6aa8de"),
    ("#8553ad", "#b690dc"),
    ("#1d774d", "#4fbf89"),
    ("#6f777d", "#9aa3a9"),
]
NO_RANK = 99
PY_KW = [
    "def",
    "class",
    "import",
    "from",
    "async",
    "await",
    "return",
    "if",
    "elif",
    "else",
    "for",
    "while",
    "try",
    "except",
    "finally",
    "with",
    "as",
    "lambda",
    "None",
    "True",
    "False",
    "pass",
    "yield",
    "raise",
    "in",
    "not",
    "and",
    "or",
    "is",
    "global",
    "nonlocal",
    "del",
    "assert",
    "match",
    "case",
]
KT_KW = [
    "fun",
    "val",
    "var",
    "when",
    "object",
    "companion",
    "data",
    "sealed",
    "override",
    "suspend",
    "internal",
    "open",
    "inline",
    "enum",
    "interface",
    "typealias",
    "by",
    "init",
    "constructor",
    "where",
    "out",
    "reified",
]


# ---------------------------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------------------------
def blank(text):
    """Return text with every character except newlines replaced by a space."""
    return re.sub(r"[^\n]", " ", text)


def collapse(text, limit):
    """Join all whitespace to single spaces and cut the text at limit characters."""
    return re.sub(r"\s+", " ", text).strip()[:limit]


def mi_of(loc, cc):
    """Maintainability index (0 to 100) from lines of code and complexity."""
    raw = 171 - 5.2 * math.log(max(1, loc * 8)) - 0.23 * cc - 16.2 * math.log(max(1, loc))
    return round(max(0, raw * 100 / 171))


def count_code(lines):
    """Count lines that are not blank and not a pure comment."""
    return sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))


def finish_types(types, test_tokens):
    """Fill the derived fields (metrics, Ca, Ce, instability, tested) of all types."""
    users = defaultdict(set)
    for t in types:
        for dep in t["deps"]:
            users[dep].add(t["id"])
    for t in types:
        t["cc"] = max(1, sum(m["cc"] for m in t["meths"]))
        t["mi"] = mi_of(t["loc"], t["cc"])
        t["ce"] = len(t["deps"])
        t["ca"] = len(users[t["id"]])
        total = t["ce"] + t["ca"]
        t["instab"] = round(t["ce"] / total, 2) if total else 0.0
        words = {t["name"], *(m["n"] for m in t["meths"])}
        t["tested"] = bool(words & test_tokens)
        t["meths"].sort(key=lambda m: m["l"])
    types.sort(key=lambda t: t["id"])


def tokens_of(paths):
    """Return the set of all words in the given files."""
    found = set()
    for path in paths:
        found.update(re.findall(r"\w+", path.read_text(encoding="utf-8", errors="replace")))
    return found


# ---------------------------------------------------------------------------------------------
# Python (Home Assistant integration)
# ---------------------------------------------------------------------------------------------
def py_doc(node):
    """Return the first paragraph of the docstring of a node, on one line."""
    text = ast.get_docstring(node) or ""
    return collapse(text.split("\n\n")[0], MAX_DOC)


def py_sig(node):
    """Return the one-line signature of a function node."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    sig = f"{prefix} {node.name}({ast.unparse(node.args)})"
    if node.returns is not None:
        sig += f" -> {ast.unparse(node.returns)}"
    return collapse(sig, MAX_SIG)


def py_method(node, lines):
    """Return the method entry of one function node."""
    end = node.end_lineno
    vis = "private" if node.name.startswith("_") and not node.name.startswith("__") else "public"
    cc = py_cc(node)
    return {
        "n": node.name,
        "l": node.lineno,
        "e": end,
        "loc": count_code(lines[node.lineno - 1 : end]),
        "cc": cc,
        "sig": py_sig(node),
        "doc": py_doc(node),
        "vis": vis,
    }


def py_imports(tree, here, pkg):
    """Return {local name: (module, original name or None)} for the imports of one file."""
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            anchor = here[: len(here) - (node.level - 1)] if node.level > 1 else here
            module = ".".join([*anchor, *(node.module.split(".") if node.module else [])])
        else:
            module = (node.module or "").removeprefix(f"custom_components.{pkg}").lstrip(".")
        for alias in node.names:
            found[alias.asname or alias.name] = (module, alias.name)
    return found


def py_used(nodes):
    """Return the names and the (name, attribute) pairs used inside the nodes."""
    names, pairs = set(), set()
    for top in nodes:
        for sub in ast.walk(top):
            if isinstance(sub, ast.Name):
                names.add(sub.id)
            elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                pairs.add((sub.value.id, sub.attr))
    return names, pairs


def py_module_info(path, base, pkg):
    """Return the parsed facts about one Python file."""
    rel = path.relative_to(base)
    parts = list(rel.parts)
    here = parts[:-1]
    stem = parts[-1][:-3]
    mod = ".".join(here) if stem == "__init__" and here else ".".join([*here, stem])
    mod = "(root)" if not mod or (mod == "__init__" and not here) else mod
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    return {
        "mod": mod,
        "project": parts[0] if here else "(root)",
        "file": path.relative_to(ROOT).as_posix(),
        "leaf": parts[-1],
        "source": source,
        "lines": source.splitlines(),
        "tree": tree,
        "imports": py_imports(tree, here, pkg),
    }


def py_types_of(info):
    """Return the type entries of one file: its classes and one entry for its functions."""
    tree, lines, mod = info["tree"], info["lines"], info["mod"]
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            funcs = [n for n in node.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
            out.append(
                {
                    "id": f"{mod}|{node.name}",
                    "name": node.name,
                    "kind": "class",
                    "l": node.lineno,
                    "e": node.end_lineno,
                    "dl": node.lineno,
                    "doc": py_doc(node),
                    "bases": [ast.unparse(b) for b in node.bases],
                    "meths": [py_method(f, lines) for f in funcs],
                    "nodes": [node],
                }
            )
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    if funcs or not out:
        rest = [n for n in tree.body if not isinstance(n, ast.ClassDef)]
        out.append(
            {
                "id": f"{mod}|{info['leaf']}",
                "name": info["leaf"],
                "kind": "module",
                "l": 1,
                "e": max(1, len(lines)),
                "dl": 1,
                "doc": py_doc(tree),
                "bases": [],
                "meths": [py_method(f, lines) for f in funcs],
                "nodes": rest,
            }
        )
    for t in out:
        t.update(
            {
                "project": info["project"],
                "ns": mod,
                "file": info["file"],
                "loc": count_code(lines[t["l"] - 1 : t["e"]]),
                "info": info,
            }
        )
    return out


def py_link(types, infos):
    """Resolve the names used by every type to other types (the dependencies)."""
    by_mod = defaultdict(dict)
    module_type = {}
    for t in types:
        by_mod[t["ns"]][t["name"]] = t["id"]
        if t["kind"] == "module":
            module_type[t["ns"]] = t["id"]
            for m in t["meths"]:
                by_mod[t["ns"]][m["n"]] = t["id"]
    for t in types:
        names, pairs = py_used(t["nodes"])
        imports = t["info"]["imports"]
        deps = set()
        for name in names:
            deps.add(by_mod[t["ns"]].get(name))
            if name in imports:
                mod, orig = imports[name]
                deps.add(by_mod.get(mod, {}).get(orig))
        for name, attr in pairs:
            if name in imports:
                mod, orig = imports[name]
                deps.add(by_mod.get(f"{mod}.{orig}" if mod else orig, {}).get(attr))
        deps.discard(None)
        deps.discard(t["id"])
        t["deps"] = sorted(deps)
    return module_type


def analyse_python():
    """Return (types, files, test tokens, version) of the integration under custom_components."""
    base = next((ROOT / "custom_components").glob("*"))
    infos = [py_module_info(p, base, base.name) for p in sorted(base.rglob("*.py"))]
    types = [t for info in infos for t in py_types_of(info)]
    py_link(types, infos)
    for t in types:
        del t["nodes"], t["info"]
    files = {info["file"]: info["source"] for info in infos}
    tests = tokens_of(sorted((ROOT / "tests").rglob("*.py")))
    version = json.loads((base / "manifest.json").read_text(encoding="utf-8"))["version"]
    return types, files, tests, version


# ---------------------------------------------------------------------------------------------
# Kotlin
# ---------------------------------------------------------------------------------------------
KT_MODS = (
    "public|private|internal|protected|override|suspend|data|sealed|abstract|open|inline|"
    "operator|infix|tailrec|inner|enum|annotation|value|const|lateinit|companion|expect|"
    "actual|external|vararg|noinline|crossinline"
)
KT_DECL = re.compile(
    rf"^(?P<ind>[ \t]*)(?:@[\w.]+(?:\([^)]*\))?[ \t]+)*(?P<mods>(?:(?:{KT_MODS})[ \t]+)*)"
    r"(?P<kind>class|interface|object|fun)\b(?P<rest>.*)$",
    re.M,
)
KT_FUN_NAME = re.compile(r"\s*(?:<.*?>\s+)?(?:[\w.<>?,\s]+\.)?`?(\w+)`?\s*\(")
KT_TYPE_NAME = re.compile(r"\s*(\w+)")
KT_BRANCH = re.compile(r"\b(?:if|for|while|catch)\b|&&|\|\||\?:")
KT_WHEN = re.compile(r"\bwhen\b")


def kt_mask(src):
    """Return the source with comments and string contents blanked; layout is unchanged."""
    out, i, n = [], 0, len(src)
    while i < n:
        two = src[i : i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(blank(src[i:j]))
        elif two == "/*":
            j, depth = i + 2, 1
            while j < n and depth:
                step = src[j : j + 2]
                depth += (step == "/*") - (step == "*/")
                j += 2 if step in ("/*", "*/") else 1
            out.append(blank(src[i:j]))
        elif src.startswith('"""', i):
            j = src.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append('"""' + blank(src[i + 3 : j - 3]) + '"""')
        elif src[i] in "\"'":
            j = kt_quote_end(src, i)
            out.append(src[i] + blank(src[i + 1 : j - 1]) + src[j - 1])
        else:
            out.append(src[i])
            j = i + 1
        i = j
    return "".join(out)


def kt_quote_end(src, i):
    """Return the index after the closing quote of the string or char literal at i."""
    quote, j, n = src[i], i + 1, len(src)
    while j < n and src[j] != quote and src[j] != "\n":
        j += 2 if src[j] == "\\" else 1
    return min(n, j + 1)


def kt_match(masked, i):
    """Return the index of the brace that closes the brace at i."""
    depth = 0
    for j in range(i, len(masked)):
        depth += (masked[j] == "{") - (masked[j] == "}")
        if depth == 0:
            return j
    return len(masked) - 1


def kt_line_indent(masked, pos):
    """Return the indentation and the first character of the next non-blank line after pos."""
    nxt = re.compile(r"\n([ \t]*)(\S)").search(masked, pos)
    return (len(nxt.group(1)), nxt.group(2)) if nxt else (-1, "")


def kt_expr_end(masked, pos, indent):
    """Return the end index of an expression body that starts at pos."""
    depth = 0
    for j in range(pos, len(masked)):
        c = masked[j]
        depth += (c in "([{") - (c in ")]}")
        if c == "\n" and depth <= 0:
            nxt_indent, first = kt_line_indent(masked, j - 1)
            if nxt_indent <= indent and first not in ".&|?+-*/":
                return j
    return len(masked)


def kt_extent(masked, pos, kind, indent):
    """Return (header end, end index) of the declaration that starts at pos."""
    depth, n = 0, len(masked)
    for i in range(pos, n):
        c = masked[i]
        depth += (c in "([") - (c in ")]")
        if depth > 0:
            continue
        if c == "{":
            return i, kt_match(masked, i)
        if c == "=" and kind == "fun" and masked[i - 1] not in "!<>=" and masked[i + 1] != "=":
            return i, kt_expr_end(masked, i + 1, indent)
        if c == "\n":
            before = masked[pos:i].rstrip()
            _, first = kt_line_indent(masked, i - 1)
            if not before.endswith((":", ",", "=", "(")) and first not in ":{,":
                return i, i
    return n, n


def kt_doc(lines, start):
    """Return the one-line KDoc of the declaration that starts at the 0-based line start."""
    j = start - 1
    while j >= 0 and lines[j].strip().startswith("@"):
        j -= 1
    if j < 0 or not lines[j].strip().endswith("*/"):
        return ""
    k = j
    while k > 0 and "/**" not in lines[k]:
        k -= 1
    if "/**" not in lines[k]:
        return ""
    body = []
    for line in lines[k : j + 1]:
        text = re.sub(r"^\s*(/\*\*|\*/|\*)?", "", line)
        text = text.replace("*/", "").strip()
        if not text.startswith("@"):
            body.append(text)
    return collapse(" ".join(body), MAX_DOC)


def kt_cc(masked_range):
    """Return the cyclomatic complexity of a piece of masked Kotlin code."""
    total = 1 + len(KT_BRANCH.findall(masked_range))
    for match in KT_WHEN.finditer(masked_range):
        brace = masked_range.find("{", match.end())
        if brace < 0:
            continue
        inner = masked_range[brace : kt_match(masked_range, brace) + 1]
        depth, arrows = 0, 0
        for k, c in enumerate(inner):
            depth += (c in "{([") - (c in "})]")
            if depth == 1 and inner.startswith("->", k):
                arrows += 1
        total += arrows
    return total


def kt_supertypes(header):
    """Return the supertype names of a class header (the part behind the colon)."""
    depth = 0
    for i, c in enumerate(header):
        depth += (c in "(<[") - (c in ")>]")
        if c == ":" and depth == 0:
            text, parts, level, cur = header[i + 1 :], [], 0, ""
            for ch in text:
                level += (ch in "(<[") - (ch in ")>]")
                if ch == "," and level == 0:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += ch
            parts.append(cur)
            names = (re.match(r"\s*([A-Za-z_][\w.]*)", p) for p in parts)
            return [m.group(1).split(".")[-1] for m in names if m]
    return []


def kt_decls(src, masked):
    """Return the declarations (types, funs, companions) of one file in source order."""
    starts = [0]
    starts += [m.end() for m in re.finditer(r"\n", masked)]
    out = []
    for m in KT_DECL.finditer(masked):
        kind, rest, mods = m.group("kind"), m.group("rest"), m.group("mods")
        if kind == "fun" and rest.strip().startswith("interface"):
            kind, rest = "interface", rest.strip()[len("interface") :]
        name_re = KT_FUN_NAME if kind == "fun" else KT_TYPE_NAME
        name = name_re.match(rest)
        companion = kind == "object" and "companion" in mods
        if not name and not companion:
            continue
        if kind == "object" and not companion and re.match(r"\s*:", rest):
            continue
        pos = m.start("kind")
        head_end, end = kt_extent(masked, pos, kind, len(m.group("ind").expandtabs(4)))
        sl = bisect_right(starts, pos) - 1
        out.append(
            {
                "kind": "enum" if "enum" in mods and kind == "class" else kind,
                "companion": companion,
                "name": name.group(1) if name else "Companion",
                "indent": len(m.group("ind")),
                "pos": pos,
                "sl": sl,
                "el": bisect_right(starts, end) - 1,
                "header": masked[pos:head_end],
                "private": "private" in mods,
                "protected": "protected" in mods,
                "end": end,
            }
        )
    return out


def kt_file_types(path, masked, src, pkg):
    """Return the type entries of one Kotlin file (classes, objects and a pseudo type)."""
    lines, rel = src.splitlines(), path.relative_to(ROOT).as_posix()
    project = kt_project_of(path)
    stack, types, top_funs, order = [], [], [], 0
    file_name = path.stem + "Kt"
    for d in kt_decls(src, masked):
        while stack and stack[-1]["el"] < d["sl"]:
            stack.pop()
        if stack and stack[-1]["kind"] == "fun":
            continue
        owner = next((s for s in reversed(stack) if s.get("entry")), None)
        if d["kind"] == "fun":
            meth = kt_method(d, masked, src, lines)
            (owner["entry"]["meths"] if owner else top_funs).append(meth)
        elif not d["companion"]:
            chain = [s["entry"]["name"] for s in stack if s.get("entry")]
            d["entry"] = kt_type(d, masked, lines, [*chain, d["name"]], pkg, rel, project)
            types.append(d["entry"])
        order += 1
        stack.append(d)
    if top_funs or not types:
        types.append(kt_file_type(file_name, masked, lines, top_funs, pkg, rel, project))
    return types


def kt_project_of(path):
    """Return the Gradle module of a source path."""
    parts = path.relative_to(ROOT).parts
    if parts[0] in ("core", "feature"):
        return f":{parts[0]}:{parts[1]}"
    return ":app" if parts[0] == "app" else parts[0]


def kt_method(d, masked, src, lines):
    """Return the method entry of one fun declaration."""
    body = masked[d["pos"] : d["end"] + 1]
    loc = sum(1 for ln in body.split("\n") if ln.strip())
    sig = collapse(d["header"], MAX_SIG)
    vis = "private" if d["private"] else "protected" if d["protected"] else "public"
    return {
        "n": d["name"],
        "l": d["sl"] + 1,
        "e": d["el"] + 1,
        "loc": loc,
        "cc": kt_cc(body),
        "sig": sig,
        "doc": kt_doc(lines, d["sl"]),
        "vis": vis,
    }


def kt_type(d, masked, lines, chain, pkg, rel, project):
    """Return the type entry of one class, interface, object or enum declaration."""
    body = masked[d["pos"] : d["end"] + 1]
    return {
        "id": f"{pkg}|{'.'.join(chain)}",
        "name": d["name"],
        "project": project,
        "ns": pkg,
        "kind": d["kind"],
        "file": rel,
        "loc": sum(1 for ln in body.split("\n") if ln.strip()),
        "l": d["sl"] + 1,
        "e": d["el"] + 1,
        "dl": d["sl"] + 1,
        "doc": kt_doc(lines, d["sl"]),
        "bases": kt_supertypes(d["header"]),
        "meths": [],
        "body": body,
        "chain": ".".join(chain),
    }


def kt_file_type(name, masked, lines, funs, pkg, rel, project):
    """Return the pseudo type that holds the top-level functions of a file."""
    return {
        "id": f"{pkg}|{name}",
        "name": name,
        "project": project,
        "ns": pkg,
        "kind": "file",
        "file": rel,
        "loc": sum(
            1
            for ln in masked.split("\n")
            if ln.strip() and not ln.startswith(("import ", "package "))
        ),
        "l": 1,
        "e": max(1, len(lines)),
        "dl": 1,
        "doc": "",
        "bases": [],
        "meths": funs,
        "body": masked,
        "chain": name,
    }


def kt_link(types, ctx):
    """Resolve the identifiers of every type to other types (the dependencies)."""
    fq = {}
    by_pkg = defaultdict(dict)
    top_funs = defaultdict(dict)
    for t in types:
        fq[f"{t['ns']}.{t['chain']}"] = t["id"]
        by_pkg[t["ns"]].setdefault(t["chain"], t["id"])
        by_pkg[t["ns"]].setdefault(t["name"], t["id"])
        if t["kind"] == "file":
            for m in t["meths"]:
                top_funs[t["ns"]][m["n"]] = t["id"]
    for t in types:
        imports, wild = ctx[t["file"]]
        words = set(re.findall(r"\b[A-Za-z_]\w*\b", t["body"]))
        calls = set(re.findall(r"\b([a-z_]\w*)\s*[({]|::(\w+)", t["body"]))
        calls = {c for pair in calls for c in pair if c}
        deps = set()
        for word in words:
            deps.add(kt_resolve(word, t["ns"], imports, wild, fq, by_pkg))
        for call in calls:
            deps.add(top_funs[t["ns"]].get(call))
            full = imports.get(call)
            if full:
                deps.add(top_funs[full.rsplit(".", 1)[0]].get(call))
        deps.discard(None)
        deps.discard(t["id"])
        t["deps"] = sorted(deps)


def kt_resolve(word, pkg, imports, wild, fq, by_pkg):
    """Return the id of the type that the simple name word means in a file, or None."""
    if word in imports:
        return fq.get(imports[word])
    if not word[0].isupper():
        return None
    if word in by_pkg[pkg]:
        return by_pkg[pkg][word]
    return next((by_pkg[w][word] for w in wild if word in by_pkg[w]), None)


def shorten_ids(types, prefix):
    """Remove the common package prefix from namespaces, ids and dependencies."""

    def short(text):
        return text.removeprefix(prefix)

    for t in types:
        t["ns"], t["id"] = short(t["ns"]), short(t["id"])
        t["deps"] = [short(d) for d in t["deps"]]


def analyse_kotlin():
    """Return (types, files, test tokens, version) of the Kotlin sources."""
    types, files, ctx, tests = [], {}, {}, []
    for path in sorted(ROOT.rglob("*.kt")):
        rel = path.relative_to(ROOT).as_posix()
        if any(p in ("build", ".git", ".gradle") for p in path.relative_to(ROOT).parts):
            continue
        if "/src/test/" in rel or "/src/androidTest/" in rel:
            tests.append(path)
            continue
        if "/src/main/" not in rel:
            continue
        src = path.read_text(encoding="utf-8")
        pkg = re.search(r"^package\s+([\w.]+)", src, re.M)
        if not pkg:
            continue
        imports = {m.split(".")[-1]: m for m in re.findall(r"^import\s+([\w.]+)\s*$", src, re.M)}
        wild = re.findall(r"^import\s+([\w.]+)\.\*\s*$", src, re.M)
        ctx[rel] = (imports, wild)
        files[rel] = src
        types += kt_file_types(path, kt_mask(src), src, pkg.group(1))
    kt_link(types, ctx)
    for t in types:
        del t["body"], t["chain"]
    shorten_ids(types, "com.stacknoise.haac.")
    app = (ROOT / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    version = re.search(r'val appVersion = "([^"]+)"', app).group(1)
    return types, files, tokens_of(tests), version


# ---------------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------------
def layer_numbers(profile):
    """Return {project: layer number} from the repository profile (1 is the top layer)."""
    return {m: n for n, (_, members) in enumerate(profile["layers"], 1) for m in members}


def project_data(types, profile):
    """Return projects ordered by layer, their ranks and the CSS colours of the layers."""
    layers = layer_numbers(profile)
    names = sorted({t["project"] for t in types}, key=lambda p: (layers.get(p, NO_RANK), p))
    rank = {p: layers.get(p, NO_RANK) for p in names}
    projects = [{"name": p, "rank": rank[p]} for p in names]
    light, dark = [], []
    for p in names:
        num = rank[p]
        pair = LAYER_COLORS[min(num, len(LAYER_COLORS)) - 1 if num != NO_RANK else -1]
        slug = re.sub(r"\W+", "_", p)
        light.append(f"--l-{slug}:{pair[0]};")
        dark.append(f"--l-{slug}:{pair[1]};")
    return projects, rank, " ".join(light), " ".join(dark)


def start_type(types):
    """Return the id of the type the explorer opens first (the largest one)."""
    return max(
        (t for t in types if t["kind"] not in ("file", "module")), key=lambda t: (t["loc"], t["id"])
    )["id"]


def json_text(value):
    """Return compact JSON that is safe inside a script element."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/").replace("<!--", "<\\!--")


def render(profile, command):
    """Return the complete page for this repository."""
    is_python = (ROOT / "custom_components").exists()
    types, files, tests, version = analyse_python() if is_python else analyse_kotlin()
    finish_types(types, tests)
    projects, rank, light, dark = project_data(types, profile)
    data = {
        "types": types,
        "projects": projects,
        "bands": [p["name"] for p in projects],
        "rank": rank,
        "notes": profile["notes"],
        "start": start_type(types),
        "version": version,
        "kw": PY_KW if is_python else KT_KW,
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, value in (
        ("{{TITLE}}", f"{profile['title']} Code-Dokumentation"),
        ("{{BRAND}}", profile["title"]),
        ("{{CMD}}", command),
        ("{{LAYERS_LIGHT}}", light),
        ("{{LAYERS_DARK}}", dark),
        ("{{DATA}}", json_text(data)),
        ("{{FILES}}", json_text(dict(sorted(files.items())))),
    ):
        page = page.replace(key, value)
    return page


def main():
    """Write docs/code-doku/index.html, or with --check compare it to the committed one."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="docs/code-doku")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    profile = PROFILES["bridge" if (ROOT / "custom_components").exists() else "android"]
    target = ROOT / args.out / "index.html"
    page = render(profile, "python3 scripts/build_code_doku.py")
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != page:
            print(f"{target.relative_to(ROOT)} is outdated: run python3 scripts/build_code_doku.py")
            return 1
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({len(page) // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
