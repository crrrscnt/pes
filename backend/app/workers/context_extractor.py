"""
context_extractor.py — Извлечение контекстного вектора для LinUCB.

Запускает только PySCF HF (классический, ~0.01 с), но НЕ VQE.
Возвращает 6-мерный вектор признаков молекулы, который
описывает её квантово-химические свойства для LinUCB.

Контекстный вектор x (dim=6):
  [0] num_spatial_orbitals     — число пространственных орбиталей
  [1] n_alpha                  — число α-электронов
  [2] n_beta                   — число β-электронов
  [3] n_total                  — суммарное число электронов
  [4] closed_shell             — 1.0 если n_alpha==n_beta, иначе 0.0
                                 (Parity mapper с тапперингом работает
                                  лучше для замкнутых оболочек)
  [5] 1.0                      — константный bias-член

Почему эти признаки:
  - num_spatial_orbitals → глубина схемы, число параметров PUCCSD
  - n_alpha, n_beta → определяют сложность Гамильтониана
  - closed_shell → ключевой признак для Parity (тапперинг убирает 2 кубита
    только при Z2-симметрии, которая есть у closed-shell систем)
  - bias → обеспечивает постоянный сдвиг в LinUCB модели
"""

import logging
import numpy as np
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# d — размерность контекстного вектора, используется во всём коде
CONTEXT_DIM = 6

# Средние расстояния для вызова build_problem() (центр диапазона скана)
_EQUIL_DISTANCES = {
    "H2":  0.74,
    "LiH": 1.60,
    "BH":  1.40,
    "BeH": 1.40,
    "CH":  1.10,
    "NH":  1.05,
    "OH":  0.96,
    "FH":  0.92,
}


def extract_context(molecule: str, atom_name: str) -> np.ndarray:
    """
    Строит контекстный вектор x (dim=CONTEXT_DIM) для молекулы.

    Вызывает PySCFDriver.run() (классический HF, <1 с),
    НЕ запускает VQE ни разу.

    Args:
        molecule:  название молекулы ("H2", "LiH", …)
        atom_name: тяжёлый атом ("H", "Li", …)

    Returns:
        np.ndarray shape=(CONTEXT_DIM,), dtype=float64
    """
    distance = _EQUIL_DISTANCES.get(molecule, 1.0)

    try:
        from .worker import build_problem
        problem = build_problem(distance, atom_name)

        n_orb   = float(problem.num_spatial_orbitals)
        n_alpha = float(problem.num_particles[0])
        n_beta  = float(problem.num_particles[1])
        n_total = n_alpha + n_beta
        closed  = 1.0 if n_alpha == n_beta else 0.0

        x = np.array([n_orb, n_alpha, n_beta, n_total, closed, 1.0],
                     dtype=np.float64)

        logger.info(
            "[context] %s: n_orb=%.0f α=%.0f β=%.0f closed=%s",
            molecule, n_orb, n_alpha, n_beta, bool(closed),
        )
        return x

    except Exception as e:
        # Fallback: если PySCF недоступен (например, в тестах),
        # возвращаем нулевой вектор с bias
        logger.warning("[context] PySCF недоступен для %s: %s. Fallback.", molecule, e)
        return _fallback_context(molecule)


def _list_to_array(data: list) -> np.ndarray:
    """Конвертирует список обратно в numpy массив (helper для pes_worker)."""
    return np.array(data, dtype=np.float64)


def _fallback_context(molecule: str) -> np.ndarray:
    """
    Аварийный контекст по справочным данным молекулы
    (без запуска PySCF).  Используется в тестах или при недоступности PySCF.
    """
    # Справочные данные: (n_orb, n_alpha, n_beta)
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
    n_orb, n_alpha, n_beta = _KNOWN.get(molecule, (4, 2, 2))
    n_total = float(n_alpha + n_beta)
    closed  = 1.0 if n_alpha == n_beta else 0.0
    return np.array([float(n_orb), float(n_alpha), float(n_beta),
                     n_total, closed, 1.0], dtype=np.float64)
