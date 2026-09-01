from typing import List, Sequence
from sqlalchemy import or_
from sqlalchemy.sql.elements import BinaryExpression


def generate_tr_search_terms(query: str) -> List[str]:
    """
    Generates case-folded and Turkish transliterated variations of search terms.
    Solves SQLite & PostgreSQL UTF-8 case-sensitivity issues with Turkish characters
    (e.g., 'i' <-> 'İ', 'ı' <-> 'I', 'ş' <-> 's', 'ç' <-> 'c', 'ğ' <-> 'g', 'ü' <-> 'u', 'ö' <-> 'o').
    """
    if not query or not query.strip():
        return []

    raw = query.strip()
    variants = set()

    # Base query and individual words
    terms = [raw]
    if " " in raw:
        terms.extend([w for w in raw.split() if w])

    for term in terms:
        variants.add(term)
        variants.add(term.lower())
        variants.add(term.upper())
        variants.add(term.title())

        # 1. Turkish lower and upper
        tl = (
            term.replace("İ", "i")
            .replace("I", "ı")
            .replace("Ğ", "ğ")
            .replace("Ü", "ü")
            .replace("Ö", "ö")
            .replace("Ş", "ş")
            .replace("Ç", "ç")
            .lower()
        )
        tu = (
            term.replace("i", "İ")
            .replace("ı", "I")
            .replace("ğ", "Ğ")
            .replace("ü", "Ü")
            .replace("ö", "Ö")
            .replace("ş", "Ş")
            .replace("ç", "Ç")
            .upper()
        )
        variants.add(tl)
        variants.add(tu)
        variants.add(tl.title())
        variants.add(tu.title())
        variants.add(tl.capitalize())
        variants.add(tu.capitalize())

        # 2. ASCII de-accenting
        tr2ascii = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        ascii_t = term.translate(tr2ascii)
        variants.add(ascii_t)
        variants.add(ascii_t.lower())
        variants.add(ascii_t.upper())
        variants.add(ascii_t.title())

        # 3. Transliterate ASCII -> Turkish (e.g., atasehir -> Ataşehir, dis -> Diş)
        t_tr1 = (
            ascii_t.lower()
            .replace("s", "ş")
            .replace("c", "ç")
            .replace("g", "ğ")
            .replace("o", "ö")
            .replace("u", "ü")
        )
        variants.add(t_tr1)
        variants.add(t_tr1.title())
        variants.add(t_tr1.upper())
        variants.add(t_tr1.capitalize())

        # With dotted/undotted i
        t_tr2 = t_tr1.replace("i", "ı")
        variants.add(t_tr2)
        variants.add(t_tr2.title())
        variants.add(t_tr2.upper())
        variants.add(t_tr2.capitalize())

        # Dotted İ prefix handling for 'istanbul' -> 'İstanbul', 'izmir' -> 'İzmir'
        if ascii_t.lower().startswith("i"):
            variants.add("İ" + t_tr1[1:])
            variants.add("İ" + ascii_t[1:].lower())
            variants.add("I" + t_tr2[1:])

    return [v for v in variants if v]


def build_tr_search_filter(columns: Sequence, query: str):
    """
    Builds a composite SQLAlchemy OR filter across specified columns
    using Turkish case-folded and transliterated variations.
    """
    variants = generate_tr_search_terms(query)
    if not variants:
        return None

    clauses = []
    for var in variants:
        for col in columns:
            clauses.append(col.ilike(f"%{var}%"))

    return or_(*clauses) if clauses else None
