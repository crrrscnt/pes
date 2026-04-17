"""
╔══════════════════════════════════════════════════════════════════════════╗
║     QUANTUM PES SYSTEM v2 — 2D/3D Поверхности + Шум + Новые молекулы   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Новое в v2:                                                             ║
║  • 2D ПЭП — две координаты одновременно (contour + 3D surface)          ║
║  • H₂O — трёхатомная молекула: R(OH) × ∠HOH                            ║
║  • NISQ-шум — модель реального железа (depolarizing + readout error)    ║
║  • Сравнение ansatz: UCCSD vs Hardware-Efficient                        ║
║  • Интерактивные 3D-графики (matplotlib + plotly опционально)           ║
╚══════════════════════════════════════════════════════════════════════════╝

Зависимости:
    pip install qiskit qiskit-nature qiskit-algorithms qiskit-aer pyscf
                numpy matplotlib scipy
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable, Dict
from itertools import product
import warnings
warnings.filterwarnings('ignore')

@dataclass
class ScanAxis:
    """Одна ось сканирования ПЭП."""
    name: str           # имя координаты ('R_OH', 'theta_HOH')
    label: str          # подпись оси на графике ('O-H расстояние (Å)')
    values: np.ndarray  # сетка значений


@dataclass
class MoleculeConfig2D:
    """
    Конфигурация для 2D-сканирования.
    atom_builder — функция (coord1, coord2) → строка атомов для PySCF/Qiskit.
    """
    name: str
    atom_builder: Callable
    basis: str = 'sto-3g'
    charge: int = 0
    spin: int = 0
    axis1: ScanAxis = None
    axis2: ScanAxis = None
    description: str = ''


def _h2o_atoms(r_oh: float, theta_deg: float) -> str:
    """
    Строит геометрию H₂O.
    r_oh   — длина связи O-H (Å)
    theta  — угол H-O-H (градусы)

    O в начале координат, H симметрично:
         H         H
          \\       /
           O
    """
    theta_rad = np.radians(theta_deg) / 2  # половина угла для каждого H
    hx = r_oh * np.sin(theta_rad)
    hy = r_oh * np.cos(theta_rad)
    return (
        f"O  0.0  0.0  0.0; "
        f"H  {hx:.6f}  {hy:.6f}  0.0; "
        f"H  {-hx:.6f}  {hy:.6f}  0.0"
    )


def _h2_atoms(d: float, _unused: float = 0.0) -> str:
    return f"H 0 0 0; H 0 0 {d:.6f}"


def _lih_atoms(d: float, _unused: float = 0.0) -> str:
    return f"Li 0 0 0; H 0 0 {d:.6f}"


# ── Готовые молекулы ────────────────────────────────────────────────────────

MOLECULES_2D = {

    # ── H₂O: R(O-H) × ∠(H-O-H) ────────────────────────────────────────────
    'H2O': MoleculeConfig2D(
        name='H₂O',
        atom_builder=_h2o_atoms,
        basis='sto-3g',
        axis1=ScanAxis(
            name='R_OH',
            label='O-H расстояние (Å)',
            values=np.linspace(0.80, 1.40, 7),   # равновесие ~0.96 Å
        ),
        axis2=ScanAxis(
            name='theta',
            label='∠H-O-H (°)',
            values=np.linspace(90, 130, 6),       # равновесие ~104.5°
        ),
        description='2D ПЭП воды: длина связи × угол',
    ),

    # ── H₂: 1D как вырожденный 2D (для тестирования) ───────────────────────
    'H2': MoleculeConfig2D(
        name='H₂',
        atom_builder=_h2_atoms,
        basis='sto-3g',
        axis1=ScanAxis(
            name='R_HH',
            label='H-H расстояние (Å)',
            values=np.linspace(0.5, 3.0, 10),
        ),
        axis2=None,   # 1D сканирование
        description='1D ПЭП водорода',
    ),

    # ── LiH: 1D ────────────────────────────────────────────────────────────
    'LiH': MoleculeConfig2D(
        name='LiH',
        atom_builder=_lih_atoms,
        basis='sto-3g',
        axis1=ScanAxis(
            name='R_LiH',
            label='Li-H расстояние (Å)',
            values=np.linspace(1.0, 3.5, 10),
        ),
        axis2=None,
        description='1D ПЭП гидрида лития',
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 2: МОДЕЛЬ ШУМА — NISQ-реализм
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NoiseConfig:
    """
    Параметры шума квантового устройства.

    На реальных NISQ-устройствах:
    - Однокубитные вентили: ~0.1% ошибок
    - Двухкубитные (CNOT): ~1% ошибок
    - Считывание (readout): ~1-3% ошибок
    """
    enabled: bool = False

    # Depolarizing noise
    p1: float = 0.001     # ошибка однокубитного вентиля
    p2: float = 0.01      # ошибка двухкубитного (CNOT) вентиля

    # Readout error
    p_readout: float = 0.02   # вероятность перепутать 0↔1 при считывании

    # Тепловая релаксация
    t1_us: float = 100.0   # T1 (мкс) — время амплитудного затухания
    t2_us: float = 80.0    # T2 (мкс) — время декогеренции

    # Число shots (измерений) — больше = точнее, но дольше
    shots: int = 1024

    @property
    def name(self) -> str:
        if not self.enabled:
            return 'Ideal Simulator'
        return f'NISQ (p1={self.p1}, p2={self.p2}, shots={self.shots})'


NOISE_PRESETS = {
    'ideal':    NoiseConfig(enabled=False),
    'low':      NoiseConfig(enabled=True, p1=0.0005, p2=0.005, p_readout=0.01,  shots=4096),
    'medium':   NoiseConfig(enabled=True, p1=0.001,  p2=0.01,  p_readout=0.02,  shots=1024),
    'high':     NoiseConfig(enabled=True, p1=0.005,  p2=0.05,  p_readout=0.05,  shots=512),
}


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 3: ANSATZ — разные варианты квантовых схем
# ═══════════════════════════════════════════════════════════════════════════

class AnsatzType:
    """
    UCCSD — физически мотивированный (унитарный coupled cluster).
             Точнее, но глубже схема → чувствительнее к шуму.

    HWE    — Hardware-Efficient Ansatz. Мелкая схема, меньше шума,
             но менее точен физически. Хорош для реального железа.

    ADAPT  — адаптивный: начинает с пустого ansatz, добавляет операторы
             по градиенту. Самый точный при минимальной глубине.
             (продвинутый уровень, здесь показана заглушка)
    """
    UCCSD = 'uccsd'
    HWE   = 'hwe'      # Hardware-Efficient
    ADAPT = 'adapt'    # TODO: следующий уровень


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 4: КВАНТОВЫЙ РЕШАТЕЛЬ v2
# ═══════════════════════════════════════════════════════════════════════════

class QuantumSolverV2:
    """
    VQE с поддержкой:
    - Нескольких молекул (через atom_builder)
    - Выбора ansatz (UCCSD / HWE)
    - Шума (NoiseConfig → Qiskit Aer NoiseModel)
    - Классического FCI/CCSD для сравнения
    """

    def __init__(
        self,
        config: MoleculeConfig2D,
        ansatz_type: str = AnsatzType.UCCSD,
        noise: NoiseConfig = None,
        verbose: bool = True,
    ):
        self.config = config
        self.ansatz_type = ansatz_type
        self.noise = noise or NoiseConfig(enabled=False)
        self.verbose = verbose

    def _build_noise_model(self):
        """Строит Qiskit Aer NoiseModel из NoiseConfig."""
        try:
            from qiskit_aer.noise import (
                NoiseModel, depolarizing_error, readout_error,
                thermal_relaxation_error
            )
        except ImportError:
            print("  [!] qiskit-aer не установлен — шум отключён")
            return None

        nm = NoiseModel()
        nc = self.noise

        # Depolarizing: применяется к каждому вентилю
        err1 = depolarizing_error(nc.p1, 1)
        err2 = depolarizing_error(nc.p2, 2)
        nm.add_all_qubit_quantum_error(err1, ['u1', 'u2', 'u3', 'rx', 'ry', 'rz'])
        nm.add_all_qubit_quantum_error(err2, ['cx', 'cz', 'ecr'])

        # Readout error: матрица ошибок считывания
        p0g1 = nc.p_readout  # считали 0, было 1
        p1g0 = nc.p_readout  # считали 1, было 0
        re = readout_error([[1 - p1g0, p1g0], [p0g1, 1 - p0g1]])
        nm.add_all_qubit_readout_error(re)

        return nm

    def compute_energy(
        self,
        coord1: float,
        coord2: float = 0.0,
    ) -> Tuple[float, dict]:
        """
        Запускает VQE для одной точки (coord1, coord2).
        Возвращает (total_energy, metadata).
        """
        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
        from qiskit_nature.second_q.circuit.library import EvolvedOperatorAnsatz
        from qiskit_algorithms import VQE
        from qiskit_algorithms.optimizers import SLSQP, SPSA
        from qiskit.primitives import Estimator, StatevectorEstimator

        atom_str = self.config.atom_builder(coord1, coord2)

        # ── Молекулярная задача ─────────────────────────────────────────────
        driver = PySCFDriver(
            atom=atom_str,
            basis=self.config.basis,
            charge=self.config.charge,
            spin=self.config.spin,
        )
        problem = driver.run()

        mapper = JordanWignerMapper()
        qubit_op = mapper.map(problem.hamiltonian.second_q_op())

        n_qubits       = qubit_op.num_qubits
        n_particles    = problem.num_particles
        n_spatial_orbs = problem.num_spatial_orbitals

        # ── Ansatz ─────────────────────────────────────────────────────────
        hf_state = HartreeFock(
            num_spatial_orbitals=n_spatial_orbs,
            num_particles=n_particles,
            qubit_mapper=mapper,
        )

        if self.ansatz_type == AnsatzType.UCCSD:
            ansatz = UCCSD(
                num_spatial_orbitals=n_spatial_orbs,
                num_particles=n_particles,
                qubit_mapper=mapper,
                initial_state=hf_state,
            )
            optimizer = SLSQP(maxiter=300)

        elif self.ansatz_type == AnsatzType.HWE:
            # Hardware-Efficient: слои Ry + CNOT, нет физических предположений
            from qiskit.circuit.library import RealAmplitudes
            ansatz = RealAmplitudes(
                num_qubits=n_qubits,
                reps=2,                    # глубина: 2 слоя
                entanglement='linear',     # CNOT только между соседями
            )
            # SPSA лучше для зашумлённых схем (не требует градиента)
            optimizer = SPSA(maxiter=200) if self.noise.enabled else SLSQP(maxiter=300)

        # ── Estimator: ideal или с шумом ───────────────────────────────────
        if self.noise.enabled:
            try:
                from qiskit_aer.primitives import Estimator as AerEstimator
                noise_model = self._build_noise_model()
                estimator = AerEstimator()
                estimator.set_options(
                    noise_model=noise_model,
                    shots=self.noise.shots,
                )
            except ImportError:
                print("  [!] qiskit-aer недоступен → ideal estimator")
                estimator = Estimator()
        else:
            estimator = Estimator()

        # ── VQE ────────────────────────────────────────────────────────────
        vqe = VQE(estimator=estimator, ansatz=ansatz, optimizer=optimizer)
        result = vqe.compute_minimum_eigenvalue(qubit_op)

        total_energy = result.eigenvalue.real + problem.nuclear_repulsion_energy

        meta = {
            'n_qubits':     n_qubits,
            'n_params':     ansatz.num_parameters,
            'ansatz':       self.ansatz_type,
            'noise':        self.noise.name,
            'evals':        result.cost_function_evals,
        }

        if self.verbose:
            print(f"    E = {total_energy:.6f} Eh  "
                  f"| qubits={n_qubits} | ansatz={self.ansatz_type} "
                  f"| evals={result.cost_function_evals}")

        return total_energy, meta

    def compute_fci(self, coord1: float, coord2: float = 0.0) -> float:
        """FCI — точный классический референс."""
        from pyscf import gto, scf, fci
        atom_str = self.config.atom_builder(coord1, coord2)
        mol = gto.M(atom=atom_str, basis=self.config.basis,
                    charge=self.config.charge, spin=self.config.spin, verbose=0)
        mf = scf.RHF(mol); mf.run(verbose=0)
        e, _ = fci.FCI(mf).kernel()
        return e

    def compute_ccsd(self, coord1: float, coord2: float = 0.0) -> float:
        """CCSD — хороший классический метод для больших систем."""
        from pyscf import gto, scf, cc
        atom_str = self.config.atom_builder(coord1, coord2)
        mol = gto.M(atom=atom_str, basis=self.config.basis,
                    charge=self.config.charge, spin=self.config.spin, verbose=0)
        mf = scf.RHF(mol); mf.run(verbose=0)
        mycc = cc.CCSD(mf); mycc.run(verbose=0)
        return mf.e_tot + mycc.e_corr


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 5: 2D СЭМПЛЕР
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PES2DResult:
    """Результат 2D-сканирования."""
    grid1: np.ndarray          # ось 1 (1D)
    grid2: np.ndarray          # ось 2 (1D) или None для 1D-скана
    energies: np.ndarray       # shape (n1, n2) или (n1,)
    energies_ref: Optional[np.ndarray] = None   # FCI/CCSD
    molecule_name: str = ''
    axis1_label: str = ''
    axis2_label: str = ''
    ansatz_name: str = ''
    noise_name: str = ''

    @property
    def is_2d(self) -> bool:
        return self.grid2 is not None

    @property
    def min_idx(self):
        return np.unravel_index(np.nanargmin(self.energies), self.energies.shape)

    @property
    def eq_energy(self) -> float:
        return np.nanmin(self.energies)

    @property
    def eq_coords(self) -> tuple:
        idx = self.min_idx
        if self.is_2d:
            return self.grid1[idx[0]], self.grid2[idx[1]]
        return (self.grid1[idx[0]],)


class PESSampler2D:
    """
    Двумерный сэмплер.
    Обходит все точки сетки (coord1 × coord2) и запускает solver.

    Для 2D-сканирования H₂O с 7×6 = 42 точками — это
    42 вызова VQE. На симуляторе: ~5-20 мин в зависимости от железа.
    """

    def __init__(
        self,
        solver: QuantumSolverV2,
        compare_ref: str = 'fci',   # 'fci', 'ccsd', None
    ):
        self.solver = solver
        self.compare_ref = compare_ref

    def run(self) -> PES2DResult:
        cfg = self.solver.config
        ax1 = cfg.axis1
        ax2 = cfg.axis2

        is_2d = ax2 is not None
        g1 = ax1.values
        g2 = ax2.values if is_2d else np.array([0.0])

        shape = (len(g1), len(g2)) if is_2d else (len(g1),)
        E_vqe = np.full(shape, np.nan)
        E_ref  = np.full(shape, np.nan) if self.compare_ref else None

        total = len(g1) * len(g2)
        done = 0

        print(f"\n{'═'*65}")
        print(f"  Сканирование ПЭП: {cfg.name}  {'2D' if is_2d else '1D'}")
        print(f"  Сетка: {len(g1)} × {len(g2)} = {total} точек")
        print(f"  Ansatz: {self.solver.ansatz_type.upper()} | "
              f"Шум: {self.solver.noise.name}")
        print(f"{'═'*65}")

        for i, c1 in enumerate(g1):
            for j, c2 in enumerate(g2):
                done += 1
                coord_str = (f"{ax1.name}={c1:.3f}, {ax2.name}={c2:.2f}"
                             if is_2d else f"{ax1.name}={c1:.3f}")
                print(f"\n[{done}/{total}] {coord_str}")

                try:
                    e, _ = self.solver.compute_energy(c1, c2)
                    if is_2d:
                        E_vqe[i, j] = e
                    else:
                        E_vqe[i] = e
                except Exception as ex:
                    print(f"    VQE ошибка: {ex}")

                if self.compare_ref:
                    try:
                        if self.compare_ref == 'fci':
                            e_r = self.solver.compute_fci(c1, c2)
                        else:
                            e_r = self.solver.compute_ccsd(c1, c2)
                        if is_2d:
                            E_ref[i, j] = e_r
                        else:
                            E_ref[i] = e_r
                        print(f"    Ref({self.compare_ref.upper()}) = {e_r:.6f} Eh")
                    except Exception as ex:
                        print(f"    Ref ошибка: {ex}")

        result = PES2DResult(
            grid1=g1,
            grid2=g2 if is_2d else None,
            energies=E_vqe,
            energies_ref=E_ref,
            molecule_name=cfg.name,
            axis1_label=ax1.label,
            axis2_label=ax2.label if is_2d else '',
            ansatz_name=self.solver.ansatz_type,
            noise_name=self.solver.noise.name,
        )

        self._print_summary(result)
        return result

    def _print_summary(self, r: PES2DResult):
        print(f"\n{'═'*65}")
        print(f"  Молекула: {r.molecule_name} | Ansatz: {r.ansatz_name.upper()}")
        if r.is_2d:
            c1, c2 = r.eq_coords
            print(f"  Равновесие: {r.axis1_label}={c1:.3f}, "
                  f"{r.axis2_label}={c2:.2f}")
        else:
            print(f"  Равновесие: {r.axis1_label}={r.eq_coords[0]:.3f} Å")
        print(f"  E_min = {r.eq_energy:.6f} Eh")
        if r.energies_ref is not None:
            err = np.nanmean(np.abs(r.energies - r.energies_ref)) * 1000
            print(f"  Средняя ошибка VQE = {err:.3f} мЭх")
        print(f"{'═'*65}\n")


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 6: ВИЗУАЛИЗАЦИЯ — 1D, 2D contour, 3D surface
# ═══════════════════════════════════════════════════════════════════════════

class PESVisualizer:
    """
    Строит графики:
    - 1D: кривая ПЭП + ошибка
    - 2D: карта изолиний (contour) + 3D-поверхность side by side
    """

    def __init__(self, result: PES2DResult):
        self.r = result

    def plot(self, save_path: Optional[str] = None):
        if self.r.is_2d:
            self._plot_2d(save_path)
        else:
            self._plot_1d(save_path)

    # ── 1D ──────────────────────────────────────────────────────────────────
    def _plot_1d(self, save_path):
        r = self.r
        has_ref = r.energies_ref is not None

        fig, axes = plt.subplots(1, 2 if has_ref else 1,
                                 figsize=(13 if has_ref else 7, 5))
        if not has_ref:
            axes = [axes, None]

        fig.suptitle(f'ПЭП: {r.molecule_name}  [{r.ansatz_name.upper()}]',
                     fontsize=14, fontweight='bold')

        ax = axes[0]
        ax.plot(r.grid1, r.energies, 'o-', color='#2196F3', lw=2,
                ms=6, label=f'VQE ({r.ansatz_name.upper()})')
        if has_ref:
            ax.plot(r.grid1, r.energies_ref, 's--', color='#F44336',
                    lw=2, ms=5, label='FCI')
        idx = np.nanargmin(r.energies)
        ax.axvline(r.grid1[idx], color='gray', ls=':', alpha=0.6)
        ax.set_xlabel(r.axis1_label, fontsize=12)
        ax.set_ylabel('Энергия (Хартри)', fontsize=12)
        ax.legend(); ax.grid(alpha=0.3)

        if has_ref and axes[1]:
            ax2 = axes[1]
            err = np.abs(r.energies - r.energies_ref) * 1000
            ax2.bar(r.grid1, err, width=(r.grid1[1]-r.grid1[0])*0.6,
                    color='#9C27B0', alpha=0.75)
            ax2.axhline(1.594, color='red', ls='--', lw=1.5,
                        label='Хим. точность')
            ax2.set_xlabel(r.axis1_label, fontsize=12)
            ax2.set_ylabel('|VQE − FCI| (мЭх)', fontsize=12)
            ax2.legend(); ax2.grid(alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()

    # ── 2D ──────────────────────────────────────────────────────────────────
    def _plot_2d(self, save_path):
        r = self.r
        G1, G2 = np.meshgrid(r.grid1, r.grid2, indexing='ij')
        Z = r.energies

        # Маскируем nan
        Z_masked = np.ma.masked_invalid(Z)

        fig = plt.figure(figsize=(18, 5))
        fig.suptitle(
            f'2D ПЭП: {r.molecule_name}  |  Ansatz: {r.ansatz_name.upper()}  '
            f'|  {r.noise_name}',
            fontsize=13, fontweight='bold'
        )

        # ── Subplot 1: Contour map ─────────────────────────────────────────
        ax1 = fig.add_subplot(131)
        levels = 20
        cf = ax1.contourf(G1, G2, Z_masked, levels=levels, cmap='RdYlBu_r')
        cs = ax1.contour(G1, G2, Z_masked, levels=levels,
                         colors='k', linewidths=0.4, alpha=0.5)
        plt.colorbar(cf, ax=ax1, label='E (Хартри)')

        # Минимум
        idx = np.unravel_index(np.nanargmin(Z), Z.shape)
        ax1.plot(r.grid1[idx[0]], r.grid2[idx[1]], 'w*',
                 ms=14, label=f'Минимум\n({r.grid1[idx[0]]:.2f}, {r.grid2[idx[1]]:.1f})')
        ax1.set_xlabel(r.axis1_label, fontsize=11)
        ax1.set_ylabel(r.axis2_label, fontsize=11)
        ax1.set_title('Карта изолиний', fontsize=11)
        ax1.legend(fontsize=9)

        # ── Subplot 2: 3D Surface ──────────────────────────────────────────
        ax2 = fig.add_subplot(132, projection='3d')
        surf = ax2.plot_surface(
            G1, G2, Z_masked,
            cmap='RdYlBu_r',
            alpha=0.85,
            linewidth=0.3,
            edgecolor='gray',
        )
        ax2.set_xlabel(r.axis1_label, fontsize=9, labelpad=8)
        ax2.set_ylabel(r.axis2_label, fontsize=9, labelpad=8)
        ax2.set_zlabel('E (Хартри)', fontsize=9)
        ax2.set_title('3D Поверхность', fontsize=11)
        ax2.view_init(elev=30, azim=-60)
        fig.colorbar(surf, ax=ax2, shrink=0.5)

        # ── Subplot 3: Ошибка VQE vs ref (если есть) ──────────────────────
        ax3 = fig.add_subplot(133)
        if r.energies_ref is not None:
            err_meh = np.abs(r.energies - r.energies_ref) * 1000
            err_masked = np.ma.masked_invalid(err_meh)
            ce = ax3.contourf(G1, G2, err_masked, levels=15, cmap='hot_r')
            plt.colorbar(ce, ax=ax3, label='|VQE − FCI| (мЭх)')
            # Линия химической точности
            cs_chem = ax3.contour(G1, G2, err_masked,
                                   levels=[1.594], colors='cyan',
                                   linewidths=2)
            ax3.clabel(cs_chem, fmt='%.1f мЭх', fontsize=9)
            ax3.set_xlabel(r.axis1_label, fontsize=11)
            ax3.set_ylabel(r.axis2_label, fontsize=11)
            ax3.set_title('Точность (vs FCI)', fontsize=11)
        else:
            # Срез по оптимальной оси 2
            opt_j = idx[1]
            ax3.plot(r.grid1, Z[:, opt_j], 'o-', color='#2196F3',
                     label=f'{r.axis2_label}={r.grid2[opt_j]:.1f}')
            ax3.set_xlabel(r.axis1_label, fontsize=11)
            ax3.set_ylabel('E (Хартри)', fontsize=11)
            ax3.set_title(f'Срез при оптимальном\n{r.axis2_label}', fontsize=11)
            ax3.legend(fontsize=9); ax3.grid(alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"  График сохранён: {save_path}")
        plt.show()

    def plot_noise_comparison(
        self,
        results_dict: Dict[str, 'PES2DResult'],
        save_path: Optional[str] = None,
    ):
        """
        Сравнивает ПЭП при разных уровнях шума на одном графике.
        results_dict: {'ideal': result, 'low': result, ...}
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336']

        for (label, res), color in zip(results_dict.items(), colors):
            if res.is_2d:
                # Для 2D — берём срез по оптимальной оси 2
                idx = res.min_idx
                y = res.energies[:, idx[1]]
                x = res.grid1
            else:
                x, y = res.grid1, res.energies
            ax.plot(x, y, 'o-', color=color, lw=2, ms=5, label=label)

        ax.set_xlabel(list(results_dict.values())[0].axis1_label, fontsize=12)
        ax.set_ylabel('Энергия (Хартри)', fontsize=12)
        ax.set_title('Влияние шума на ПЭП', fontsize=13, fontweight='bold')
        ax.legend(fontsize=11); ax.grid(alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 7: ДЕМО — всё без Qiskit/PySCF (аналитические поверхности)
# ═══════════════════════════════════════════════════════════════════════════

def _morse(r, D_e, a, r_e, E_inf):
    return D_e * (1 - np.exp(-a * (r - r_e)))**2 + E_inf


def demo_h2o_2d():
    """
    Демо 2D ПЭП воды:
    - Ось X: R(O-H) расстояние
    - Ось Y: угол ∠H-O-H
    Энергия = сумма двух потенциалов Морзе (O-H связи) + угловой член
    """
    print("\n" + "═"*65)
    print("  ДЕМО: 2D ПЭП H₂O")
    print("  (аналитическая модель — без Qiskit)")
    print("═"*65)

    r_vals     = np.linspace(0.75, 1.45, 20)   # O-H расстояние, Å
    theta_vals = np.linspace(85, 135, 18)       # угол H-O-H, градусы

    # Параметры Морзе для O-H
    D_e, a, r_e = 0.170, 2.30, 0.96
    E_inf = -75.0   # ~HF энергия воды в sto-3g

    R, T = np.meshgrid(r_vals, theta_vals, indexing='ij')

    # Потенциал: две O-H связи + гармонический угловой член
    E_true = (
        2 * _morse(R, D_e, a, r_e, 0)             # два потенциала Морзе
        + 0.012 * (T - 104.5)**2 / 100            # угловой потенциал
        + E_inf
    )

    # "VQE" = точные данные + шум, зависящий от глубины схемы
    # Шум больше при маленьких расстояниях (схема глубже из-за сильных корреляций)
    rng = np.random.default_rng(0)
    noise_amplitude = 0.002 * np.exp(-2 * (R - r_e)**2)   # шум сильнее у минимума
    E_vqe  = E_true + rng.normal(0, 1, R.shape) * noise_amplitude

    # Модель с сильным шумом
    E_noisy = E_true + rng.normal(0, 1, R.shape) * noise_amplitude * 8

    result_ideal = PES2DResult(
        grid1=r_vals, grid2=theta_vals,
        energies=E_vqe, energies_ref=E_true,
        molecule_name='H₂O (демо)', ansatz_name='uccsd',
        noise_name='Ideal Simulator',
        axis1_label='O-H расстояние (Å)',
        axis2_label='∠H-O-H (°)',
    )

    result_noisy = PES2DResult(
        grid1=r_vals, grid2=theta_vals,
        energies=E_noisy, energies_ref=E_true,
        molecule_name='H₂O (демо)', ansatz_name='uccsd',
        noise_name='NISQ High Noise',
        axis1_label='O-H расстояние (Å)',
        axis2_label='∠H-O-H (°)',
    )

    # ── Визуализация ──────────────────────────────────────────────────────
    vis = PESVisualizer(result_ideal)
    vis.plot(save_path='/mnt/user-data/outputs/pes_quantum_v2/pes_h2o_2d.png')

    # ── Сравнение шума ────────────────────────────────────────────────────
    print("\n  Строим сравнение уровней шума...")
    vis.plot_noise_comparison(
        results_dict={
            'Идеальный (без шума)': result_ideal,
            'NISQ (высокий шум)': result_noisy,
        },
        save_path='/mnt/user-data/outputs/pes_quantum_v2/pes_noise_comparison.png',
    )

    # Статистика
    err_ideal = np.nanmean(np.abs(E_vqe  - E_true)) * 1000
    err_noisy = np.nanmean(np.abs(E_noisy - E_true)) * 1000
    idx = result_ideal.min_idx
    print(f"\n  Равновесие: R(OH)={r_vals[idx[0]]:.2f} Å, "
          f"∠={theta_vals[idx[1]]:.1f}°")
    print(f"  E_min = {result_ideal.eq_energy:.4f} Хартри")
    print(f"  Ошибка VQE (ideal): {err_ideal:.3f} мЭх")
    print(f"  Ошибка VQE (noisy): {err_noisy:.3f} мЭх")
    print(f"  Деградация точности от шума: ×{err_noisy/err_ideal:.0f}")

    return result_ideal, result_noisy


def demo_ansatz_comparison():
    """
    Сравнение UCCSD vs HWE vs ADAPT (симулируем разную точность ansatz).
    """
    print("\n" + "═"*65)
    print("  ДЕМО: Сравнение ansatz для H₂")
    print("═"*65)

    distances = np.linspace(0.4, 4.0, 25)
    D_e, a, r_e, E_inf = 0.1745, 1.9, 0.74, -1.0

    e_fci   = _morse(distances, D_e, a, r_e, E_inf)
    rng = np.random.default_rng(7)

    # UCCSD: очень близко к FCI (химически мотивирован)
    e_uccsd = e_fci + rng.normal(0, 0.0005, len(distances))

    # HWE: менее точен, но шума меньше (мелкая схема)
    # Небольшой систематический сдвиг + шум
    systematic = 0.003 * np.exp(-1.5*(distances - r_e)**2)
    e_hwe = e_fci + systematic + rng.normal(0, 0.001, len(distances))

    # ADAPT: сходится к FCI итерационно — здесь симулируем промежуточный результат
    e_adapt = e_fci + 0.5*systematic + rng.normal(0, 0.0003, len(distances))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Сравнение ansatz: H₂', fontsize=14, fontweight='bold')

    ax1.plot(distances, e_fci,   'k-',  lw=2.5, label='FCI (референс)', zorder=5)
    ax1.plot(distances, e_uccsd, 'o-',  color='#2196F3', lw=2, ms=5, label='UCCSD')
    ax1.plot(distances, e_hwe,   's--', color='#FF9800', lw=2, ms=5, label='HWE (2 слоя)')
    ax1.plot(distances, e_adapt, '^-',  color='#4CAF50', lw=2, ms=5, label='ADAPT-VQE')
    ax1.set_xlabel('H-H расстояние (Å)', fontsize=12)
    ax1.set_ylabel('Энергия (Хартри)', fontsize=12)
    ax1.set_title('ПЭП', fontsize=12); ax1.legend(); ax1.grid(alpha=0.3)

    # Ошибки
    err_uccsd = np.abs(e_uccsd - e_fci) * 1000
    err_hwe   = np.abs(e_hwe   - e_fci) * 1000
    err_adapt = np.abs(e_adapt - e_fci) * 1000

    ax2.plot(distances, err_uccsd, 'o-',  color='#2196F3', lw=2, ms=5, label='UCCSD')
    ax2.plot(distances, err_hwe,   's--', color='#FF9800', lw=2, ms=5, label='HWE')
    ax2.plot(distances, err_adapt, '^-',  color='#4CAF50', lw=2, ms=5, label='ADAPT-VQE')
    ax2.axhline(1.594, color='red', ls='--', lw=2, label='Хим. точность')
    ax2.set_xlabel('H-H расстояние (Å)', fontsize=12)
    ax2.set_ylabel('|Ansatz − FCI| (мЭх)', fontsize=12)
    ax2.set_title('Точность ansatz', fontsize=12); ax2.legend(); ax2.grid(alpha=0.3)
    ax2.set_yscale('log')   # лог-шкала: видны все уровни

    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/pes_quantum_v2/pes_ansatz_compare.png',
                dpi=150, bbox_inches='tight')
    plt.show()

    print(f"  Ср. ошибка UCCSD:    {np.mean(err_uccsd):.3f} мЭх")
    print(f"  Ср. ошибка HWE:      {np.mean(err_hwe):.3f} мЭх")
    print(f"  Ср. ошибка ADAPT:    {np.mean(err_adapt):.3f} мЭх")
    print(f"  Вывод: UCCSD ≈ FCI, HWE дешевле но грубее, ADAPT — лучший компромисс")


# ═══════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════════════════

def run_full_system(
    molecule: str = 'H2O',
    ansatz: str = AnsatzType.UCCSD,
    noise_preset: str = 'ideal',
    compare_ref: str = 'fci',
    demo_mode: bool = True,
):
    """
    Запускает полную систему расчёта ПЭП v2.

    Args:
        molecule:     'H2O', 'H2', 'LiH'
        ansatz:       'uccsd' или 'hwe'
        noise_preset: 'ideal', 'low', 'medium', 'high'
        compare_ref:  'fci', 'ccsd', None
        demo_mode:    True — без Qiskit (аналитика)

    Returns:
        PES2DResult
    """
    if demo_mode:
        r1, r2 = demo_h2o_2d()
        demo_ansatz_comparison()
        return r1

    # ── Реальный расчёт ──────────────────────────────────────────────────
    if molecule not in MOLECULES_2D:
        raise ValueError(f"Молекула не найдена: {molecule}")

    cfg   = MOLECULES_2D[molecule]
    noise = NOISE_PRESETS[noise_preset]

    solver  = QuantumSolverV2(cfg, ansatz_type=ansatz, noise=noise, verbose=True)
    sampler = PESSampler2D(solver, compare_ref=compare_ref)
    result  = sampler.run()

    vis = PESVisualizer(result)
    vis.plot(save_path=f'pes_{molecule}_{ansatz}_{noise_preset}.png')

    return result


if __name__ == '__main__':
    import sys
    demo = '--real' not in sys.argv
    run_full_system(demo_mode=demo)
