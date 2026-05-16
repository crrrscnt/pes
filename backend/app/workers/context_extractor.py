import logging
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CONTEXT_DIM = 6


def _list_to_array(data: list) -> np.ndarray:
    return np.array(data, dtype=np.float64)


def extract_context(molecule_preset_id: str, db: Session) -> np.ndarray:
    """
    Строит контекстный вектор x (dim=CONTEXT_DIM) для молекулы.
    Использует cached_context из MoleculePreset если доступен.
    Иначе запускает PySCF HF и кэширует результат.
    """
    from ..models import MoleculePreset
    from ..utils.molecule_utils import parse_chemical_formula, get_total_atom_count
    from .worker import build_problem

    preset = db.query(MoleculePreset).filter(
        MoleculePreset.id == molecule_preset_id
    ).first()

    if preset is None:
        raise ValueError(f"MoleculePreset {molecule_preset_id} not found")

    if preset.cached_context is not None:
        logger.info("[context] %s: using cached context", molecule_preset_id)
        return _list_to_array(preset.cached_context)

    distance = preset.reference_distance

    try:
        counts = parse_chemical_formula(molecule_preset_id)

        # ПРОВЕРКА: молекула должна быть диатомной (всего 2 атома)
        total_atoms = get_total_atom_count(molecule_preset_id)
        if total_atoms != 2:
            raise ValueError(f"Only diatomic molecules supported, got {total_atoms} atoms")

        # Разворачиваем формулу в список индивидуальных атомов
        atoms: list[str] = []
        for symbol, count in counts.items():
            atoms.extend([symbol] * count)

        if len(atoms) != 2:
            raise ValueError(f"Expected 2 atoms, got {len(atoms)}: {atoms}")

        atom_a, atom_b = atoms[0], atoms[1]

        problem = build_problem(distance, atom_a, atom_b)

        n_orb = float(problem.num_spatial_orbitals)
        n_alpha = float(problem.num_particles[0])
        n_beta = float(problem.num_particles[1])
        n_total = n_alpha + n_beta
        closed = 1.0 if n_alpha == n_beta else 0.0

        x = np.array([n_orb, n_alpha, n_beta, n_total, closed, 1.0],
                     dtype=np.float64)

        preset.cached_context = x.tolist()
        db.commit()

        logger.info(
            "[context] %s: n_orb=%.0f α=%.0f β=%.0f closed=%s (cached)",
            molecule_preset_id, n_orb, n_alpha, n_beta, bool(closed),
        )
        return x

    except Exception as e:
        logger.warning(
            "[context] PySCF недоступен для %s: %s. Fallback.",
            molecule_preset_id, e
        )
        return _fallback_context(molecule_preset_id)


def _fallback_context(molecule_preset_id: str) -> np.ndarray:
    _KNOWN = {
        "H2":  (2, 1, 1),
        "LiH": (6, 2, 2),
        "BH":  (6, 3, 2),
        "BeH": (5, 2, 2),
        "CH":  (6, 3, 2),
        "NH":  (6, 3, 3),
        "OH":  (6, 4, 3),
        "FH":  (6, 4, 4),
    }
    n_orb, n_alpha, n_beta = _KNOWN.get(molecule_preset_id, (4, 2, 2))
    n_total = float(n_alpha + n_beta)
    closed = 1.0 if n_alpha == n_beta else 0.0
    return np.array([float(n_orb), float(n_alpha), float(n_beta),
                     n_total, closed, 1.0], dtype=np.float64)
