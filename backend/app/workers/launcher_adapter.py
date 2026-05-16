import numpy as np
import traceback
import logging
from time import time
from typing import Dict, Any, Callable, Optional, List, Tuple
from .worker import compute_single_point
from ..utils.molecule_utils import parse_chemical_formula

logger = logging.getLogger(__name__)


def worker_wrapper(args: Tuple[float, str, str, str, int]) -> Tuple[
        float, Dict[str, Any]]:
    """
    args: (distance, optimizer, mapper, molecule_preset_id, ansatz_reps)
    """
    distance, optimizer, mapper, molecule_preset_id, ansatz_reps = args
    try:
        counts = parse_chemical_formula(molecule_preset_id)
        # Разворачиваем формулу в список индивидуальных атомов
        atoms: List[str] = []
        for symbol, count in counts.items():
            atoms.extend([symbol] * count)
        
        if len(atoms) != 2:
            raise ValueError(f"Expected diatomic molecule, got {atoms} from formula {molecule_preset_id}")
        atom_a, atom_b = atoms[0], atoms[1]
        result = compute_single_point(distance, optimizer, mapper,
                                      atom_a, atom_b, ansatz_reps)
        return distance, result
    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error("Error computing point at %.3f A: %s\n%s",
                     distance, error_msg, tb)
        return distance, {"error": error_msg, "traceback": tb}


def detect_peaks(results: Dict[float, Dict[str, Any]], threshold_rel=0.005,
                 threshold_abs=0.001) -> List[float]:
    distances = sorted(
        [d for d, r in results.items() if "error" not in r and "vqe" in r])
    if len(distances) < 3:
        return []
    vqes = np.array([results[d]["vqe"] for d in distances])
    peaks = []
    n = len(distances)
    for i, d in enumerate(distances):
        neigh_idx = [j for j in range(max(0, i - 2), min(n, i + 3)) if j != i]
        if not neigh_idx:
            continue
        neigh_mean = vqes[neigh_idx].mean()
        diff_abs = vqes[i] - neigh_mean
        diff_rel = diff_abs / (abs(neigh_mean) + 1e-12)
        if diff_abs > threshold_abs and diff_rel > threshold_rel:
            peaks.append(d)
    return sorted(peaks)


def find_minimum(results: Dict[float, Dict[str, Any]]) -> Optional[float]:
    successful = {d: r for d, r in results.items()
                  if "error" not in r and "vqe" in r}
    if not successful:
        return None
    return min(successful, key=lambda d: successful[d]["vqe"])


def recompute_point(distance: float, optimizer: str, mapper: str,
                    molecule_preset_id: str, attempts: int = 1,
                    extra_ansatz_reps: bool = False) -> Optional[Dict[str, Any]]:
    candidates = []
    for _ in range(attempts):
        _, res = worker_wrapper((distance, optimizer, mapper,
                                 molecule_preset_id, 1))
        if "error" not in res and "vqe" in res:
            candidates.append(res)
    if extra_ansatz_reps:
        _, res = worker_wrapper((distance, optimizer, mapper,
                                 molecule_preset_id, 2))
        if "error" not in res and "vqe" in res:
            candidates.append(res)
    return min(candidates, key=lambda r: r["vqe"]) if candidates else None


def run_scan(
        molecule_preset_id: str,
        optimizer: str,
        mapper: str,
        distance_min: float,
        distance_max: float,
        step: float,
        precision_multiplier: int = 1,
        progress_callback: Optional[
            Callable[[int, str, Optional[Dict]], None]] = None,
) -> Dict[str, Any]:
    """
    Выполняет PES-скан ПОСЛЕДОВАТЕЛЬНО.
    Параметры скана берутся из MoleculePreset (передаются явно).
    """
    start_time = time()
    actual_step = step / precision_multiplier

    logger.info("Sequential PES scan: %s %s/%s step=%.3f range=[%.3f, %.3f]",
                molecule_preset_id, mapper, optimizer,
                actual_step, distance_min, distance_max)

    distances = [float(d) for d in np.arange(distance_min, distance_max, actual_step)]
    if not distances:
        raise ValueError(
            f"Empty distance range for {molecule_preset_id}: "
            f"min={distance_min}, max={distance_max}, step={actual_step}"
        )

    results: Dict[float, Dict[str, Any]] = {}

    if progress_callback:
        progress_callback(5,
                          f"Начало скана {molecule_preset_id} ({mapper}/{optimizer}), "
                          f"{len(distances)} точек")

    total = len(distances)
    for i, d in enumerate(distances):
        distance, result = worker_wrapper((d, optimizer, mapper,
                                           molecule_preset_id, 1))
        results[distance] = result
        if progress_callback:
            pct = 10 + int((i + 1) / total * 35)
            if "error" not in result:
                partial = {
                    "distance": float(distance),
                    "vqe": float(result["vqe"]),
                    "numpy": float(result["numpy"]),
                    "total_points": total,
                    "calculated_points": i + 1,
                }
                progress_callback(pct,
                                  f"Точка {i+1}/{total}: {distance:.3f} A",
                                  partial)
            else:
                progress_callback(pct,
                                  f"Точка {i+1}/{total}: {distance:.3f} A [ОШИБКА]",
                                  None)

    min_distance = find_minimum(results)
    if min_distance is None:
        logger.error("No successful results from main scan.")
        if progress_callback:
            progress_callback(100, "Скан провалился: нет успешных точек.")
        return {"results": results, "min_distance": None, "peaks": [],
                "elapsed_time": time() - start_time, "status": "failed"}

    logger.info("Minimum after main scan: %.4f A", min_distance)
    if progress_callback:
        progress_callback(48,
                          f"Основной скан завершён. Минимум: {min_distance:.4f} A")

    peaks_main = detect_peaks(results)
    if peaks_main:
        if progress_callback:
            progress_callback(50,
                              f"Найдено {len(peaks_main)} пиков. Перерасчёт...")
        for idx, p in enumerate(peaks_main):
            new_res = recompute_point(p, optimizer, mapper, molecule_preset_id)
            if new_res:
                results[p] = new_res
            if progress_callback:
                pct = 50 + int((idx + 1) / len(peaks_main) * 10)
                progress_callback(pct,
                                  f"Пик {idx+1}/{len(peaks_main)}: {p:.3f} A")

    min_distance = find_minimum(results) or min_distance
    if progress_callback:
        progress_callback(65,
                          f"Пики пересчитаны. Минимум: {min_distance:.4f} A")

    half_step = step / 2.0
    refine_points = [
        d for d in [round(min_distance - half_step, 12),
                    round(min_distance + half_step, 12)]
        if d > 0 and d not in results
    ]
    if refine_points:
        if progress_callback:
            progress_callback(70, "Уточнение вокруг минимума (шаг/2)...")
        for idx, d in enumerate(refine_points):
            dist, res = worker_wrapper((d, optimizer, mapper,
                                        molecule_preset_id, 1))
            results[dist] = res
            if progress_callback:
                pct = 70 + int((idx + 1) / len(refine_points) * 10)
                progress_callback(pct,
                                  f"Уточнение {idx+1}/{len(refine_points)}: {d:.3f} A")

    peaks_final = detect_peaks(results)
    if peaks_final:
        if progress_callback:
            progress_callback(85,
                              f"{len(peaks_final)} пиков после уточнения...")
        for idx, p in enumerate(peaks_final):
            new_res = recompute_point(p, optimizer, mapper, molecule_preset_id)
            if new_res:
                results[p] = new_res
            if progress_callback:
                pct = 85 + int((idx + 1) / len(peaks_final) * 10)
                progress_callback(pct,
                                  f"Финальный пик {idx+1}/{len(peaks_final)}: {p:.3f} A")

    min_final = find_minimum(results) or min_distance
    elapsed = time() - start_time
    successful = sum(1 for r in results.values() if "error" not in r)
    scan_status = "completed" if successful > 0 else "failed"

    logger.info("Scan %s: %d/%d ok, min=%.4f A, %.1fs",
                scan_status, successful, len(results), min_final, elapsed)

    if progress_callback:
        progress_callback(
            100,
            f"Готово за {elapsed:.1f}s | "
            f"Минимум: {min_final:.4f} A | "
            f"Успешно: {successful}/{len(results)}"
        )

    return {
        "results": results,
        "min_distance": min_final,
        "peaks": peaks_final,
        "elapsed_time": elapsed,
        "status": scan_status,
    }