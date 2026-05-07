import re
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional

# Полный список химических символов для проверки.
ELEMENT_SYMBOLS = {
    'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al',
    'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
    'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr',
    'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm',
    'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W',
    'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
    'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
    'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds',
    'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
}

_SYMBOL_PATTERN = re.compile(r"^([A-Za-z]{1,2})(\d*)")


def _normalize_symbol(raw_symbol: str) -> str:
    raw_symbol = raw_symbol.strip()
    if not raw_symbol:
        raise ValueError("Empty element symbol")
    if len(raw_symbol) == 1:
        return raw_symbol.upper()
    if len(raw_symbol) == 2:
        return raw_symbol[0].upper() + raw_symbol[1].lower()
    raise ValueError(f"Invalid element symbol: {raw_symbol}")


def _parse_formula_recursive(formula: str, position: int = 0) -> Optional[List[Tuple[str, int]]]:
    if position == len(formula):
        return []

    best_result: Optional[List[Tuple[str, int]]] = None

    for symbol_length in (1, 2):
        if position + symbol_length > len(formula):
            continue
        raw_symbol = formula[position:position + symbol_length]
        try:
            symbol = _normalize_symbol(raw_symbol)
        except ValueError:
            continue

        if symbol not in ELEMENT_SYMBOLS:
            continue

        next_pos = position + symbol_length
        count_str = ""
        while next_pos < len(formula) and formula[next_pos].isdigit():
            count_str += formula[next_pos]
            next_pos += 1

        count = int(count_str) if count_str else 1
        remainder = _parse_formula_recursive(formula, next_pos)
        if remainder is None:
            continue

        candidate = [(symbol, count)] + remainder
        if best_result is None or len(candidate) > len(best_result):
            best_result = candidate

    return best_result


def parse_chemical_formula(raw: str) -> Dict[str, int]:
    """Parse chemical formula and return element counts.

    Supports case-insensitive input and normalizes symbols to standard casing.
    """
    formula = raw.strip()
    if not formula:
        raise ValueError("Пустая формула молекулы")

    result = _parse_formula_recursive(formula)
    if not result:
        raise ValueError(f"Неверная формула молекулы: {raw}")

    counts: Dict[str, int] = OrderedDict()
    for symbol, count in result:
        counts[symbol] = counts.get(symbol, 0) + count

    return counts


def normalize_formula(raw: str) -> str:
    counts = parse_chemical_formula(raw)
    parts: List[str] = []
    for symbol, count in counts.items():
        if count == 1:
            parts.append(symbol)
        else:
            parts.append(f"{symbol}{count}")
    return "".join(parts)


def get_total_atom_count(raw: str) -> int:
    counts = parse_chemical_formula(raw)
    return sum(counts.values())


def get_primary_atom(raw: str) -> str:
    counts = parse_chemical_formula(raw)
    if not counts:
        raise ValueError(f"Cannot determine primary atom from formula: {raw}")
    return next(iter(counts))


def validate_two_atom_molecule(raw: str) -> str:
    normalized = normalize_formula(raw)
    total_atoms = sum(parse_chemical_formula(normalized).values())
    if total_atoms != 2:
        raise ValueError(
            "Поддерживаются только двухатомные молекулы. Для более крупных молекул это пока в разработке."
        )
    return normalized
