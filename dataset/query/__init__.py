"""Query resolution."""

from dataset.query.ir import CandidateSetTrace, Clause, QueryProgram, QueryResolution
from dataset.query.resolver import resolve_query, smoke_queries

__all__ = [
    "CandidateSetTrace",
    "Clause",
    "QueryProgram",
    "QueryResolution",
    "resolve_query",
    "smoke_queries",
]
