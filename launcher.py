import subprocess
import json
import multiprocessing as mp
import numpy as np
from time import time
import os
import matplotlib.pyplot as plt

# Путь к worker.py
WORKER = os.path.join(os.path.dirname(__file__), "worker.py")

# Параметры скана
step = 0.1

# Возможные варианты (соответствуют строкам в worker)
MOLECULE_PARAMS = {
    "1": ("H2", "H", np.arange(0.4, 1.2, step)),
    "2": ("LiH", "Li", np.arange(1.2, 2.0, step)),
    "3": ("BH", "B", np.arange(1.0, 1.8, step)),
    "4": ("BeH", "Be", np.arange(1.0, 1.8, step)),
    "5": ("CH", "C", np.arange(0.6, 1.4, step)),
    "6": ("NH", "N", np.arange(0.6, 1.4, step)),
    "7": ("OH", "O", np.arange(0.6, 1.4, step)),
    "8": ("FH", "F", np.arange(0.6, 1.4, step)),
}
OPTIMIZERS = {"1": "SLSQP", "2": "COBYLA", "3": "SPSA"}
MAPPERS = {"1": "JordanWigner", "2": "BravyiKitaev", "3": "Parity"}


def choose_option(prompt, options_dict, default_key):
    print(prompt)
    for k, v in options_dict.items():
        print(f"{k}) {v}")
    choice = input(f"Выбор [по умолчанию {default_key}]: ").strip()
    if choice == "":
        choice = default_key
    if choice not in options_dict:
        print(
            f"Неверный выбор, используем по умолчанию: {options_dict[default_key]}")
        choice = default_key
    # return options_dict[choice]
    return choice


# Ввод параметров
molecule_key = choose_option("Выберите молекулу:", {k: v[0] for k, v in MOLECULE_PARAMS.items()}, "1")
molecule_name, atom_name, distances_main = MOLECULE_PARAMS[molecule_key]
optimizer = choose_option("Выберите оптимизатор:", OPTIMIZERS, "1")
mapper = choose_option("Выберите мэппер:", MAPPERS, "3")

# Timeout для каждого subprocess (секунды)
PER_TASK_TIMEOUT = 14400  # настройте по необходимости

# Число параллельных процессов (по умолчанию cpu_count-2)
try:
    default_procs = max(1, mp.cpu_count() - 2)
except Exception:
    default_procs = 1
procs_input = input(f"Число процессов [по умолчанию {default_procs}]: ").strip()
if procs_input == "":
    n_procs = default_procs
else:
    try:
        n_procs = int(procs_input)
        if n_procs < 1:
            n_procs = 1
    except ValueError:
        print("Неверное число, используем по умолчанию")
        n_procs = default_procs


def run_worker(distance, optimizer_arg=None, reps="1", mapper_arg=None, atom_name_arg=None):
    """Запускает worker и возвращает (distance, result_dict)."""
    opt = optimizer_arg if optimizer_arg is not None else optimizer
    # anz = ansatz_arg if ansatz_arg is not None else ansatz
    mapr = mapper_arg if mapper_arg is not None else mapper
    atom = atom_name_arg if atom_name_arg is not None else atom_name
    cmd = ["python", WORKER, f"{distance}", opt, reps, mapr, atom]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=PER_TASK_TIMEOUT)
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            return (distance, {"error": f"returncode {completed.returncode}",
                               "stdout": stdout, "stderr": stderr})
        if not stdout:
            return (distance, {"error": "empty stdout", "stderr": stderr})
        # Ожидаем JSON в stdout (последняя непустая строка)
        try:
            res = json.loads(stdout.splitlines()[-1])
            return (distance, res)
        except json.JSONDecodeError:
            return (distance, {"error": "json decode error", "stdout": stdout,
                               "stderr": stderr})
    except subprocess.TimeoutExpired:
        return (distance, {"error": f"timeout after {PER_TASK_TIMEOUT}s"})
    except Exception as e:
        return (distance, {"error": str(e)})


def worker_wrapper(distance):
    return run_worker(distance)


# --- Функции детекции пиков и пересчёта ---
def detect_peaks(results, threshold_rel=0.005, threshold_abs=0.001):
    """
    Детектирует локальные пики только по VQE-значениям.
    Пик = точка, где vqe выше среднего соседей (up to 2 слева/справа)
    на абсолютную разницу > threshold_abs и относительную > threshold_rel.
    """
    distances = sorted(
        [d for d, r in results.items() if "error" not in r and "vqe" in r])
    vqes = np.array([results[d]["vqe"] for d in distances])
    peaks = []
    n = len(distances)
    for i, d in enumerate(distances):
        neigh_idx = []
        for j in range(max(0, i - 2), min(n, i + 3)):
            if j != i:
                neigh_idx.append(j)
        if not neigh_idx:
            continue
        neigh_mean = vqes[neigh_idx].mean()
        diff_abs = vqes[i] - neigh_mean
        diff_rel = diff_abs / (abs(neigh_mean) + 1e-12)
        if diff_abs > threshold_abs and diff_rel > threshold_rel:
            peaks.append(d)
    return sorted(peaks)


def find_minimum(results):
    """Вспомогательная функция для поиска минимума по VQE."""
    successful = sorted([d for d, r in results.items() if "error" not in r])
    if successful:
        vqe_values = np.array([results[d]["vqe"] for d in successful])
        min_idx = int(np.argmin(vqe_values))
        return successful[min_idx]
    return None


def recompute_point(distance, optimizer, mapper, atom_name, attempts=1,
                    extra_ansatz_reps=False):
    """
    Пересчитывает точку:
      - attempts раз с текущими параметрами (optimizer, ansatz, mapper)
      - если extra_ansatz_reps=True — запускает PUCCSD__REPS2
    Возвращает лучший найденный результат (dict) или None.
    """
    candidates = []
    # обычные повторные попытки
    for _ in range(attempts):
        _, res = run_worker(distance, optimizer_arg=optimizer, reps="1",
                            mapper_arg=mapper, atom_name_arg=atom_name)
        if "error" not in res and "vqe" in res:
            candidates.append(res)
    # анзац с reps=2
    if extra_ansatz_reps:
        _, res = run_worker(distance, optimizer_arg=optimizer, reps="2",
                            mapper_arg=mapper, atom_name_arg=atom_name)
        if "error" not in res and "vqe" in res:
            candidates.append(res)
    if candidates:
        best = min(candidates, key=lambda r: r["vqe"])
        return best
    return None


def peaks_wrapper(args):
    """Wrapper для параллельного пересчёта пиков. args = (p, optimizer, mapper, atom_name)"""
    p, opt, mapr, atom = args
    print(f"Recomputing peak at {p:.3f} Å ...")
    new_res = recompute_point(p, opt, mapr, atom, attempts=1, extra_ansatz_reps=False)
    if new_res:
        if "error" in new_res:
            print(
                f"[{p:.3f}] still ERROR after recompute: {new_res.get('error')}")
        else:
            print(f"[{p:.3f}] Recomputed VQE={new_res['vqe']:.6f}")
    else:
        print(f"[{p:.3f}] Recompute produced no valid result.")
    return p, new_res


if __name__ == "__main__":
    start = time()
    distances = [float(d) for d in distances_main]

    print(f"\n{molecule_name} PES scan" )
    print(
        f"Используем: оптимизатор {OPTIMIZERS[optimizer]}, анзац PUCCSD, мэппер {MAPPERS[mapper]}, процессы - {n_procs}")
    results = {}
    # --- основной скан ---
    with mp.Pool(processes=n_procs) as pool:
        for distance, res in pool.imap_unordered(worker_wrapper, distances):
            results[distance] = res
            if "error" in res:
                print(f"[{distance:.3f}] ERROR: {res.get('error')}")
            else:
                print(
                    f"[{distance:.3f}] VQE={res['vqe']:.6f} NumPy={res['numpy']:.6f}")

    # --- Шаг 1: Первый минимум после основного скана ---
    min_distance = find_minimum(results)
    if min_distance is None:
        print("\nNo successful results from main scan; exiting.")
        with open("results.json", "w") as f:
            json.dump(results, f, indent=2)
        raise SystemExit(1)
    print(f"\nMinimum after main scan at {min_distance:.4f} Å")

    # --- Шаг 2: Детекция и пересчёт пиков ---
    peaks_main = detect_peaks({d: r for d, r in results.items()})
    if peaks_main:
        print(f"\nDetected peaks after scans: {peaks_main}")
        tasks = [(p, optimizer, mapper, atom_name) for p in peaks_main]
        with mp.Pool(processes=n_procs) as pool:
            for p, new_res in pool.imap_unordered(peaks_wrapper, tasks):
                if new_res:
                    results[p] = new_res

    # --- Шаг 3: Обновлённый минимум после пересчёта пиков ---
    min_distance_after_peaks = find_minimum(results)
    if min_distance_after_peaks is not None:
        print(
            f"\nMinimum after peaks recompute at {min_distance_after_peaks:.4f} Å")
        min_distance = min_distance_after_peaks  # Обновляем для refinement

    # --- Шаг 4: Уточнения step/2 вокруг (обновлённого) минимума ---
    refinement_points = set()
    half_step = step / 2.0
    left = round(min_distance - half_step, 12)
    right = round(min_distance + half_step, 12)
    if left > 0:
        refinement_points.add(left)
    if right > 0:
        refinement_points.add(right)

    refinement_to_compute = sorted(
        [d for d in refinement_points if d not in results])

    if refinement_to_compute:
        print(f"\nRefine points (step/2): {refinement_to_compute}")
        with mp.Pool(processes=n_procs) as pool:
            for distance, res in pool.imap_unordered(worker_wrapper,
                                                     refinement_to_compute):
                results[distance] = res
                if "error" in res:
                    print(f"[ref {distance:.3f}] ERROR: {res.get('error')}")
                else:
                    print(
                        f"[ref {distance:.3f}] VQE={res['vqe']:.6f} NumPy={res['numpy']:.6f}")

    # --- Шаг 5: Новые пики после refinement (пересчёт ВСЕХ текущих пиков) ---
    peaks_after_refine = detect_peaks({d: r for d, r in results.items()})
    peaks_to_recompute = peaks_after_refine  # Изменено: все пики, не только новые
    if peaks_to_recompute:
        print(
            f"\nDetected peaks after refine (all to recompute): {peaks_to_recompute}")
        tasks = [(p, optimizer, mapper, atom_name) for p in peaks_to_recompute]
        with mp.Pool(processes=n_procs) as pool:
            for p, new_res in pool.imap_unordered(peaks_wrapper, tasks):
                if new_res:
                    results[p] = new_res

    # --- Шаг 6: Финальный минимум ---
    min_distance_refined = find_minimum(results)
    if min_distance_refined is not None:
        print(f"\nFinal minimum at {min_distance_refined:.4f} Å")
    else:
        min_distance_refined = min_distance  # Fallback

    elapsed = time() - start
    print(f"\nDone in {elapsed:.1f}s. Collected {len(results)} results.")

    # Сохранение результатов в файл
    output_data = {
        "molecule_name": molecule_name,
        "results": results
    }
    with open("results.json", "w") as f:
        json.dump(output_data, f, indent=2)

    # Построение графика для успешно рассчитанных точек
    distances_ok = sorted([d for d, r in results.items() if "error" not in r])
    if distances_ok:
        sorted_distances = np.array(distances_ok)
        sorted_vqe = np.array([results[d]["vqe"] for d in sorted_distances])
        sorted_numpy = np.array([results[d]["numpy"] for d in sorted_distances])

        plt.figure()
        plt.plot(sorted_distances, sorted_vqe, marker='x', label='VQE')
        plt.plot(sorted_distances, sorted_numpy, marker='.', linestyle=':',
                 label='NumPyMinimumEigensolver')
        plt.axvline(min_distance_refined, color='gray', linestyle='--',
                    label=f'min {min_distance_refined:.4f} Å')
        plt.xlabel('Bond length (Å)')
        plt.ylabel('Total Energy (Hartree)')
        plt.grid(True)
        plt.legend()
        if molecule_name == "H2":
            plt.title('H₂ Dissociation Curve (PES Scan)')
        else:
            plt.title(f'{molecule_name} Dissociation Curve (PES Scan)')
        plt.savefig(f"bond_length_vs_energy_{molecule_name}.png", dpi=300,
                    bbox_inches="tight")
        print(f"Plot saved to bond_length_vs_energy_{molecule_name}.png")
    else:
        print("No successful results to plot.")
