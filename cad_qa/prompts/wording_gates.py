"""Prompt wording gates."""

BANNED_PUBLIC_TERMS = {
    "ontology",
    "material_region",
    "void_region",
    "measurement scope",
    "candidate-set trace",
}


def banned_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(term for term in BANNED_PUBLIC_TERMS if term in lowered)
