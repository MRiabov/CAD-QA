"""Python worker for the CAD-QA dataset generator.

The Go entry point starts this package as a child process and passes it typed
Parquet paths and a small JSON request. One module lands per pipeline stage; see
``docs/dataset/implementation/file-trees.md``.
"""
