"""Scrape a Python package's public API into JSON, as input for tool synthesis.

Usage:
    python3 -I scrape_repo.py <repo_dir> <package_name> [-o out.json]

The public API is the package's ``__all__`` (following ``from .module import
name`` in ``__init__.py``); without ``__all__``, every public module-level
function and class in non-private modules. For each exported function, and
each public method of each exported class, it records the signature (with
annotations and defaults), return annotation, docstring, source location and
size. Static analysis only (``ast``): the package is never imported or run.
"""

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Param:
    name: str
    annotation: str | None
    default: str | None
    kind: str  # positional, keyword_only, var_positional, var_keyword


@dataclass
class Callable:
    qualname: str
    module: str
    kind: str  # function, method, classmethod, staticmethod, property
    params: list[Param]
    returns: str | None
    summary: str
    docstring: str
    file: str
    line: int
    loc: int
    n_overloads: int = 0
    decorators: list[str] = field(default_factory=list)


def unparse(node: ast.AST | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def collect_params(args: ast.arguments, drop_first: bool) -> list[Param]:
    """Flatten an ``ast.arguments`` into Params, dropping ``self``/``cls`` if asked."""
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    params = [Param(a.arg, unparse(a.annotation), unparse(d), "positional")
              for a, d in zip(positional, defaults)]
    if drop_first and params:
        params = params[1:]
    if args.vararg:
        params.append(Param(args.vararg.arg, unparse(args.vararg.annotation), None, "var_positional"))
    params += [Param(a.arg, unparse(a.annotation), unparse(d), "keyword_only")
               for a, d in zip(args.kwonlyargs, args.kw_defaults)]
    if args.kwarg:
        params.append(Param(args.kwarg.arg, unparse(args.kwarg.annotation), None, "var_keyword"))
    return params


def is_overload(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(unparse(d) in ("overload", "typing.overload") for d in fn.decorator_list)


def describe(fn: ast.FunctionDef | ast.AsyncFunctionDef, qualname: str, module: str,
             path: Path, root: Path, in_class: bool, n_overloads: int) -> Callable:
    decorators = [unparse(d) or "" for d in fn.decorator_list]
    if not in_class:
        kind = "function"
    elif "property" in decorators or any(d.endswith(".setter") for d in decorators):
        kind = "property"
    elif "classmethod" in decorators:
        kind = "classmethod"
    elif "staticmethod" in decorators:
        kind = "staticmethod"
    else:
        kind = "method"
    doc = ast.get_docstring(fn) or ""
    return Callable(
        qualname=qualname,
        module=module,
        kind=kind,
        params=collect_params(fn.args, drop_first=kind in ("method", "classmethod", "property")),
        returns=unparse(fn.returns),
        summary=doc.strip().split("\n\n")[0].replace("\n", " ") if doc else "",
        docstring=doc,
        file=str(path.relative_to(root)),
        line=fn.lineno,
        loc=(fn.end_lineno or fn.lineno) - fn.lineno + 1,
        n_overloads=n_overloads,
        decorators=decorators,
    )


def functions_in(body: list[ast.stmt]) -> dict[str, tuple[ast.FunctionDef | ast.AsyncFunctionDef, int]]:
    """Map name -> (implementation def, number of @overload stubs) for a module or class body."""
    found: dict[str, tuple[ast.FunctionDef | ast.AsyncFunctionDef, int]] = {}
    overloads: dict[str, int] = {}
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_overload(node):
                overloads[node.name] = overloads.get(node.name, 0) + 1
            elif node.name not in found:  # keep the getter, not a later @x.setter
                found[node.name] = (node, 0)
    return {name: (fn, overloads.get(name, 0)) for name, (fn, _) in found.items()}


def public(name: str) -> bool:
    return not name.startswith("_")


def scrape_module(path: Path, module: str, root: Path, names: set[str] | None) -> list[Callable]:
    """Public functions and public class methods of one module, optionally limited to ``names``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[Callable] = []
    for name, (fn, n_over) in functions_in(tree.body).items():
        if (names is None and public(name)) or (names is not None and name in names):
            out.append(describe(fn, name, module, path, root, in_class=False, n_overloads=n_over))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if (names is None and not public(node.name)) or (names is not None and node.name not in names):
            continue
        for name, (fn, n_over) in functions_in(node.body).items():
            if public(name):
                out.append(describe(fn, f"{node.name}.{name}", module, path, root,
                                    in_class=True, n_overloads=n_over))
    return out


def exported_names(init: Path) -> tuple[list[str] | None, dict[str, str]]:
    """Return ``__all__`` (or None) and a map name -> relative module from ``from .x import name``."""
    tree = ast.parse(init.read_text(encoding="utf-8"))
    all_names: list[str] | None = None
    origin: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            all_names = [ast.literal_eval(e) for e in node.value.elts]  # type: ignore[attr-defined]
        elif isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                origin[alias.asname or alias.name] = node.module
    return all_names, origin


def scrape_package(repo: Path, package: str) -> tuple[list[Callable], list[str]]:
    """Scrape the package's public API; also return exported names that are not callables."""
    pkg = repo / package
    all_names, origin = exported_names(pkg / "__init__.py")
    if all_names is None:
        callables = []
        for path in sorted(pkg.rglob("*.py")):
            rel = path.relative_to(pkg).with_suffix("")
            # an __init__.py is the module of its own package
            parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
            if any(part.startswith("_") or part in ("tests", "test") for part in parts):
                continue
            callables += scrape_module(path, ".".join((package, *parts)), repo, names=None)
        return callables, []
    by_module: dict[str, set[str]] = {}
    for name in all_names:
        if name in origin:
            by_module.setdefault(origin[name], set()).add(name)
    callables = []
    for mod, names in sorted(by_module.items()):
        callables += scrape_module(pkg / f"{mod.replace('.', '/')}.py", f"{package}.{mod}", repo, names)
    found = {c.qualname.split(".")[0] for c in callables}
    return callables, [n for n in all_names if n not in found]


def constructors(repo: Path, callables: list[Callable]) -> dict[str, dict]:
    """How to build each class that has exported methods: its __init__ parameters, if it has one."""
    found: dict[str, dict] = {}
    for c in callables:
        if "." not in c.qualname or c.qualname.split(".")[0] in found:
            continue
        name = c.qualname.split(".")[0]
        tree = ast.parse((repo / c.file).read_text(encoding="utf-8"))
        node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name), None)
        init = functions_in(node.body).get("__init__") if node else None
        found[name] = {
            "module": c.module,
            "params": [asdict(p) for p in collect_params(init[0].args, drop_first=True)] if init else None,
            "summary": (ast.get_docstring(node) or "").split("\n\n")[0].replace("\n", " ") if node else "",
        }
    return found


def git_commit(repo: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True)
    return result.stdout.strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("repo", type=Path)
    parser.add_argument("package")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    callables, other_exports = scrape_package(args.repo, args.package)
    result = {
        "repo": str(args.repo),
        "package": args.package,
        "commit": git_commit(args.repo),
        "n_callables": len(callables),
        "other_exports": other_exports,
        "callables": [asdict(c) for c in callables],
        "classes": constructors(args.repo, callables),
    }
    if args.output:
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    kinds: dict[str, int] = {}
    for c in callables:
        kinds[c.kind] = kinds.get(c.kind, 0) + 1
    print(f"{args.package} @ {result['commit']}: {len(callables)} public callables {kinds}",
          file=sys.stderr)
    print(f"other exports (constants, exceptions, ...): {', '.join(other_exports) or 'none'}",
          file=sys.stderr)
    for c in callables:
        sig = ", ".join(p.name + (f": {p.annotation}" if p.annotation else "") for p in c.params)
        over = f" [{c.n_overloads} overloads]" if c.n_overloads else ""
        print(f"  {c.kind:12} {c.qualname}({sig}) -> {c.returns}{over}  | {c.summary[:70]}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
