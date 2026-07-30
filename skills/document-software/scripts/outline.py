"""Outline of Python code for writing a reference: constants, classes, attributes and functions.

Usage: python outline.py <file or directory> [...] [-o outfile]

Directories are searched recursively for *.py (without __pycache__ and virtual environments).
Per module it prints its docstring summary, module constants with their value, classes with
class attributes, instance attributes set in methods (self.x = ...) and every function or
method with signature, line number and the first paragraph of its docstring.
The line numbers help to navigate while writing; the reference itself names symbols instead.
"""
import argparse
import ast
import sys
from pathlib import Path

SKIPPED_DIRS = {"__pycache__", ".venv", "venv", ".git", "node_modules", "site-packages"}
VALUE_CHARS = 70


def short(node: ast.AST, limit: int = VALUE_CHARS) -> str:
    """Source of a node on one line, cut to ``limit`` characters."""
    text = " ".join(ast.unparse(node).split())
    return text if len(text) <= limit else text[:limit] + "…"


def summary(node: ast.AST) -> str:
    """First paragraph of a docstring on one line, or an empty string."""
    doc = ast.get_docstring(node)
    return " ".join(doc.strip().split("\n\n")[0].split()) if doc else ""


def signature(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Parameters with annotations and defaults, without self/cls, plus the return annotation."""
    def parameters(pairs) -> list[str]:
        texts = []
        for arg, default in pairs:
            if arg.arg in ("self", "cls"):
                continue
            text = arg.arg + (f": {ast.unparse(arg.annotation)}" if arg.annotation else "")
            texts.append(text + (f" = {short(default, 25)}" if default is not None else ""))
        return texts

    args = fn.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    parts = parameters(zip(positional, defaults))
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    parts += parameters(zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    returns = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
    return f"{fn.name}({', '.join(parts)}){returns}"


def assignment(node: ast.Assign | ast.AnnAssign) -> str | None:
    """'name: type = value' of a module or class level assignment."""
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names = ", ".join(short(t, 40) for t in targets)
    annotation = f": {ast.unparse(node.annotation)}" if isinstance(node, ast.AnnAssign) else ""
    value = f" = {short(node.value)}" if node.value is not None else ""
    return f"{names}{annotation}{value}"


def instance_attributes(cls: ast.ClassDef) -> list[str]:
    """Names of the attributes the methods of a class set on self, in order of appearance."""
    names = []
    for node in ast.walk(cls):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] \
            if isinstance(node, ast.AnnAssign) else []
        flat = [elt for t in targets for elt in (t.elts if isinstance(t, ast.Tuple) else [t])]
        for target in flat:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                    and target.value.id == "self" and target.attr not in names:
                names.append(target.attr)
    return names


def outline(path: Path, out) -> None:
    """Print the outline of one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    print(f"## {path.as_posix()}  # {summary(tree)}", file=out)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            print(f"  {node.lineno}: {assignment(node)}", file=out)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print(f"  {node.lineno}: def {signature(node)}  # {summary(node)}", file=out)
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            decorators = " ".join("@" + short(d, 30) for d in node.decorator_list)
            print(f"  {node.lineno}: {decorators} class {node.name}({bases})  # {summary(node)}".replace(
                ":  class", ": class"), file=out)
            for item in node.body:
                if isinstance(item, (ast.Assign, ast.AnnAssign)):
                    print(f"    {item.lineno}: {assignment(item)}", file=out)
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = "".join("@" + short(d, 30) + " " for d in item.decorator_list)
                    print(f"    {item.lineno}: {decorators}{signature(item)}  # {summary(item)}", file=out)
            attributes = instance_attributes(node)
            if attributes:
                print(f"    self: {', '.join(attributes)}", file=out)
    print(file=out)


def python_files(paths: list[Path]) -> list[Path]:
    """The given files and every *.py below the given directories, sorted."""
    files = []
    for path in paths:
        if path.is_dir():
            files += [p for p in path.rglob("*.py") if not SKIPPED_DIRS & set(p.parts)]
        else:
            files.append(path)
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="Python files or directories")
    parser.add_argument("-o", "--output", type=Path, help="write the outline to this file (UTF-8)")
    args = parser.parse_args()
    out = args.output.open("w", encoding="utf-8") if args.output else sys.stdout
    if out is sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    for path in python_files(args.paths):
        try:
            outline(path, out)
        except SyntaxError as error:
            print(f"## {path.as_posix()}  # not parsed: {error}", file=out)
    if out is not sys.stdout:
        out.close()


if __name__ == "__main__":
    main()
