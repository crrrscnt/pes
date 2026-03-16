"""
linucb.py — LinUCB (Linear Upper Confidence Bound) для выбора
маппера и оптимизатора VQE.

Теория:
  Контекстный бандит с d-мерным вектором признаков x.
  Для каждой из K=9 «рук» (комбинаций mapper×optimizer) хранятся:

    A_a ∈ R^{d×d}  — матрица ковариации (инициализируется как I_d)
    b_a ∈ R^d      — вектор наград (инициализируется как 0)

  Прогноз для руки a при контексте x:
    θ_a  = A_a^{-1} b_a           (оценка параметров линейной модели)
    score = θ_a^T x + α √(x^T A_a^{-1} x)
             ─────────   ──────────────────
            «эксплуатация»    «исследование»

  Обновление после получения награды r:
    A_a ← A_a + x x^T
    b_a ← b_a + r x

Награда:
  r = 1 / (1 + error_meh)    ∈ (0, 1]
  Чем ближе VQE к NumPy (error_meh→0), тем r→1.
  Чем хуже (error_meh→∞), тем r→0.

Параметры:
  α (alpha) — параметр исследования.
    Малый α → «жадный» (быстро сходится на известно хорошем методе).
    Большой α → больше исследует неизвестные руки.
    Рекомендация: 1.0 на старте, можно понижать до 0.3 после ~50 запусков.

Хранение:
  Таблица linucb_arms в PostgreSQL (9 строк, по 1 на каждую руку).
  A_matrix и b_vector хранятся как JSONB (список списков / список чисел).
  Атомарные обновления через SELECT … FOR UPDATE.
"""

import logging
import numpy as np
from typing import Tuple, Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ── Константы ─────────────────────────────────────────────────────────────
CONTEXT_DIM = 6    # совпадает с context_extractor.CONTEXT_DIM
ALPHA       = 1.0  # параметр исследования LinUCB

ALL_MAPPERS    = ["JordanWigner", "BravyiKitaev", "Parity"]
ALL_OPTIMIZERS = ["SLSQP", "COBYLA", "SPSA"]

# Все 9 рук: (mapper, optimizer)
ARMS: List[Tuple[str, str]] = [
    (m, o) for m in ALL_MAPPERS for o in ALL_OPTIMIZERS
]

def arm_id(mapper: str, optimizer: str) -> str:
    """Канонический строковый идентификатор руки."""
    return f"{mapper}_{optimizer}"


# ── Вспомогательные функции ────────────────────────────────────────────────

def _matrix_to_list(A: np.ndarray) -> List[List[float]]:
    return A.tolist()

def _list_to_matrix(data: List[List[float]]) -> np.ndarray:
    return np.array(data, dtype=np.float64)

def _vector_to_list(b: np.ndarray) -> List[float]:
    return b.tolist()

def _list_to_vector(data: List[float]) -> np.ndarray:
    return np.array(data, dtype=np.float64)

def _identity() -> List[List[float]]:
    return np.eye(CONTEXT_DIM).tolist()

def _zeros() -> List[float]:
    return np.zeros(CONTEXT_DIM).tolist()

def compute_reward(vqe_energy: float, numpy_energy: float) -> float:
    """
    Вычисляет награду из результатов VQE.

    r = 1 / (1 + |VQE - NumPy| * 1000)   ∈ (0, 1]

    Формула нормирует ошибку в мЭх: при ошибке 0 мЭх → r=1.0,
    при 1 мЭх → r≈0.5, при 10 мЭх → r≈0.09.
    """
    error_meh = abs(vqe_energy - numpy_energy) * 1000.0
    reward = 1.0 / (1.0 + error_meh)
    return float(reward)


# ── Основные операции с БД ─────────────────────────────────────────────────

def _get_or_create_arm(db, arm_id_str: str, mapper: str, optimizer: str):
    """
    Возвращает строку LinUCBArm из БД, создаёт если не существует.
    Использует SELECT FOR UPDATE для атомарности.
    """
    from ..models import LinUCBArm

    arm = (db.query(LinUCBArm)
             .filter(LinUCBArm.arm_id == arm_id_str)
             .with_for_update()
             .first())

    if arm is None:
        arm = LinUCBArm(
            arm_id=arm_id_str,
            mapper=mapper,
            optimizer=optimizer,
            n_pulls=0,
            a_matrix=_identity(),
            b_vector=_zeros(),
            total_reward=0.0,
        )
        db.add(arm)
        db.flush()  # получаем ID, не коммитим

    return arm


def select_arm(x: np.ndarray, db) -> Tuple[str, str, str]:
    """
    Выбирает лучшую «руку» (mapper, optimizer) для контекста x.

    Использует формулу LinUCB:
        score = θ^T x + α √(x^T A^{-1} x)

    Args:
        x:  контекстный вектор shape=(CONTEXT_DIM,)
        db: SQLAlchemy Session

    Returns:
        (mapper, optimizer, arm_id_str)
    """
    from ..models import LinUCBArm

    best_score  = -np.inf
    best_mapper = "Parity"
    best_optim  = "SLSQP"
    best_arm_id = arm_id("Parity", "SLSQP")

    for mapper, optimizer in ARMS:
        a_id = arm_id(mapper, optimizer)
        arm  = (db.query(LinUCBArm)
                  .filter(LinUCBArm.arm_id == a_id)
                  .first())

        if arm is None:
            # Не было ни одного запуска — очень высокий UCB (исследуем)
            score = np.inf
        else:
            A = _list_to_matrix(arm.a_matrix)
            b = _list_to_vector(arm.b_vector)

            try:
                A_inv = np.linalg.inv(A)
            except np.linalg.LinAlgError:
                A_inv = np.linalg.pinv(A)

            theta    = A_inv @ b
            exploit  = float(theta @ x)
            explore  = float(ALPHA * np.sqrt(x @ A_inv @ x))
            score    = exploit + explore

        logger.debug("[LinUCB] arm=%s score=%.4f", a_id, score)

        if score > best_score:
            best_score  = score
            best_mapper = mapper
            best_optim  = optimizer
            best_arm_id = a_id

    logger.info("[LinUCB] selected: %s (score=%.4f)", best_arm_id, best_score)
    return best_mapper, best_optim, best_arm_id


def update(arm_id_str: str, mapper: str, optimizer: str,
           x: np.ndarray, reward: float, db) -> None:
    """
    Обновляет параметры руки после получения награды.

    A ← A + x x^T
    b ← b + r x

    Args:
        arm_id_str: идентификатор руки
        mapper, optimizer: для создания строки если её нет
        x:      контекстный вектор
        reward: полученная награда ∈ (0, 1]
        db:     SQLAlchemy Session (должен быть внутри транзакции)
    """
    arm = _get_or_create_arm(db, arm_id_str, mapper, optimizer)

    A = _list_to_matrix(arm.a_matrix)
    b = _list_to_vector(arm.b_vector)

    # LinUCB update
    A += np.outer(x, x)
    b += reward * x

    arm.a_matrix    = _matrix_to_list(A)
    arm.b_vector    = _vector_to_list(b)
    arm.n_pulls    += 1
    arm.total_reward += reward

    logger.info(
        "[LinUCB] update arm=%s | reward=%.4f | n_pulls=%d | avg_reward=%.4f",
        arm_id_str, reward, arm.n_pulls,
        arm.total_reward / arm.n_pulls,
    )
    # Коммит делает вызывающий код


def get_arm_stats(db) -> List[Dict[str, Any]]:
    """
    Возвращает статистику всех рук для отображения в UI / Admin.
    """
    from ..models import LinUCBArm

    stats = []
    for mapper, optimizer in ARMS:
        a_id = arm_id(mapper, optimizer)
        arm  = db.query(LinUCBArm).filter(LinUCBArm.arm_id == a_id).first()

        if arm is None:
            stats.append({
                "arm_id":       a_id,
                "mapper":       mapper,
                "optimizer":    optimizer,
                "n_pulls":      0,
                "avg_reward":   None,
                "total_reward": 0.0,
            })
        else:
            avg = arm.total_reward / arm.n_pulls if arm.n_pulls > 0 else None
            stats.append({
                "arm_id":       a_id,
                "mapper":       mapper,
                "optimizer":    optimizer,
                "n_pulls":      arm.n_pulls,
                "avg_reward":   round(avg, 4) if avg is not None else None,
                "total_reward": round(arm.total_reward, 4),
            })

    # Сортируем по среднему reward (у кого нет данных — в конец)
    stats.sort(key=lambda s: s["avg_reward"] or -1, reverse=True)
    return stats
