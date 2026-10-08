"""Sandboxed python execution for the run_code tool — spawned as a subprocess.

Executes one code snippet (read from stdin) with numpy preloaded, a
blocked-imports meta-path hook (no network/files/processes/cadquery),
restricted builtins (no open/eval/exec/compile), numpy file-IO removed, and
stdout/exception capture. Exit 0 on success, exit 1 on exception.

THREAT ASSESSMENT — read before relying on this: this is an ACCIDENTAL-MISUSE guard
for LLM-model-generated snippets inside a training pipeline, NOT a security
boundary. It stops a confused/entangled LLM model from `import os`, `open(...)`,
`import cadquery` (task integrity: cadquery would trivialize the task), or
from hanging via the timeout. A determined attacker can still escape a plain
python subprocess (object introspection, loader abuse) — real isolation needs
kernel namespaces/seccomp, which the Vast unprivileged container cannot
provide. Keep this in mind before ever exposing run_code to untrusted input.
"""
from __future__ import annotations

import builtins
import math
import sys

import numpy as np

# Modules the sandboxed code may never import. numpy/math are preloaded before
# the hook is installed, so their internal imports are unaffected.
FORBIDDEN_MODULES = frozenset({
    "os", "posix", "nt", "java", "sys", "sysconfig", "builtins",
    "subprocess", "socket", "shutil", "pathlib",
    "requests", "urllib", "urllib3", "http", "ftplib", "smtplib", "telnetlib",
    "ssl", "ctypes", "pickle", "marshal", "importlib", "runpy", "pty", "tty",
    "fcntl", "resource", "signal", "multiprocessing", "threading",
    "cadquery", "ocp", "pydantic", "datasets", "torch", "transformers",
})

# Builtins removed from the exec globals (file I/O and code-execution escapes).
RESTRICTED_BUILTIN_NAMES = frozenset({
    "open", "eval", "exec", "compile", "input", "breakpoint", "help",
    "exit", "quit",
})

# numpy file-IO entry points removed from the np handle (secret/file access).
_NP_FILE_IO = frozenset({
    "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt",
    "genfromtxt", "fromfile", "memmap",
})


class _BlockImports:
    """Meta-path finder: raise ImportError for any forbidden module root."""

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in FORBIDDEN_MODULES:
            raise ImportError(f"import '{fullname}' is blocked in the run_code sandbox")
        return None


def _harden_numpy(mod: object) -> None:
    """Strip file-IO + the loader escape handle from the preloaded numpy module."""
    for name in _NP_FILE_IO:
        try:
            delattr(mod, name)
        except AttributeError:
            pass
    try:
        mod.__spec__ = None  # block np.__spec__.loader.load_module(...) abuse
    except Exception:
        pass


_MAX_AUTO_DISPLAY_CHARS = 2000


def _run_with_repl(code: str, globals_dict: dict) -> None:
    """Exec `code`; then auto-display the last expression's value (notebook-like).

    IPython rule: the final expression is captured; if its value is not None it
    is repr'd onto stdout (truncated), so `2*3*4` returns "24" without a
    print(). Explicit print() calls still work and come first.
    """
    import ast

    tree = ast.parse(code)
    last_is_expr = bool(tree.body) and isinstance(tree.body[-1], ast.Expr)
    if last_is_expr:
        node = tree.body[-1]
        assign = ast.Assign(targets=[ast.Name(id="_cadqa_last_expr_", ctx=ast.Store())], value=node.value)
        ast.copy_location(assign, node)
        tree.body[-1] = assign
        ast.fix_missing_locations(tree)
    exec(compile(tree, "<run_code>", "exec"), globals_dict)
    if last_is_expr:
        value = globals_dict.get("_cadqa_last_expr_")
        if value is not None:
            try:
                if isinstance(value, np.floating):
                    text = repr(float(value))   # np.float64(4.0) -> 4.0
                elif isinstance(value, np.integer):
                    text = repr(int(value))     # np.int64(10) -> 10
                else:
                    text = repr(value)
            except Exception:
                text = "<unprintable value>"
            if len(text) > _MAX_AUTO_DISPLAY_CHARS:
                text = text[:_MAX_AUTO_DISPLAY_CHARS] + " ... [truncated]"
            print(text)


def main() -> int:
    code = sys.stdin.read()
    sys.meta_path.insert(0, _BlockImports())
    # numpy (preloaded above) already imported os/sys/etc. — evict them so user
    # `import os` cannot reuse the sys.modules cache and must hit the blocker.
    for mod in FORBIDDEN_MODULES:
        sys.modules.pop(mod, None)
    restricted = {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if name not in RESTRICTED_BUILTIN_NAMES
    }
    _harden_numpy(np)
    globals_dict = {
        "__name__": "__main__",
        "__builtins__": restricted,
        "np": np,
        "math": math,
    }
    try:
        globals_dict["math"].__spec__ = None  # block the builtin-loader escape handle
    except Exception:
        pass
    try:
        _run_with_repl(code, globals_dict)
    except BaseException:  # noqa: BLE001 - report any sandboxed failure to the harness
        import traceback

        traceback.print_exc(file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
