"""Difficulty bucket helpers."""

from __future__ import annotations


def difficulty_for_hops(hop_count: int) -> str:
    if hop_count <= 1:
        return "low"
    if hop_count == 2:
        return "bridge"
    if hop_count <= 5:
        return "cad_browsecomp"
    return "hard_cad_browsecomp"
