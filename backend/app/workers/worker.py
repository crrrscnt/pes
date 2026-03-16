import sys
import json
import traceback
from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_algorithms import NumPyMinimumEigensolver, VQE
from qiskit_algorithms.optimizers import SLSQP, COBYLA, SPSA
from qiskit.primitives import StatevectorEstimator
from qiskit_nature.second_q.mappers import JordanWignerMapper, \
    BravyiKitaevMapper, ParityMapper
from qiskit_nature.second_q.circuit.library import HartreeFock, PUCCSD

MAPPERS = {"JordanWigner": JordanWignerMapper,
           "BravyiKitaev": BravyiKitaevMapper, "Parity": ParityMapper}
OPTIMIZERS = {"SLSQP": SLSQP, "COBYLA": COBYLA, "SPSA": SPSA}


def build_problem(distance, atom_name, basis="sto3g"):
    """Создает квантовую задачу с автоматической коррекцией спина."""
    spin_values = [0, 1, 3]  # Попробуем эти значения спина по порядку
    last_error = None

    for spin in spin_values:
        try:
            driver = PySCFDriver(
                atom=f"{atom_name} 0 0 0; H 0 0 {distance}",
                basis=basis,
                charge=0,
                spin=spin,
                unit=DistanceUnit.ANGSTROM
            )
            problem = driver.run()
            if spin != 0:
                print(f"Note: Using spin={spin} for {atom_name}H system",
                      file=sys.stderr)
            return problem
        except Exception as e:
            last_error = e
            # Проверяем цепочку исключений на ошибку спина
            is_spin_error = False
            current_exception = e

            # Проходим по цепочке __cause__
            while current_exception is not None:
                error_msg = str(current_exception).lower()
                if "spin" in error_msg and "not consistent" in error_msg:
                    is_spin_error = True
                    break
                current_exception = getattr(current_exception, '__cause__',
                                            None)

            if is_spin_error:
                if spin == spin_values[-1]:
                    # Если это последняя попытка, выбрасываем ошибку
                    raise
                else:
                    # Иначе пробуем следующее значение спина
                    print(f"Spin {spin} failed, trying next value...",
                          file=sys.stderr)
                    continue
            else:
                # Если это другая ошибка, сразу выбрасываем
                raise

    # На случай, если цикл завершился без возврата
    if last_error:
        raise last_error
    raise RuntimeError("Failed to build problem with any spin value")


def create_vqe_local(mapper, num_spatial_orbitals, num_particles,
                     optimizer_name, ansatz_reps):
    estimator = StatevectorEstimator()
    optimizer_cls = OPTIMIZERS.get(optimizer_name, SLSQP)
    if optimizer_cls is SLSQP:
        optimizer = SLSQP(maxiter=100)  # ftol = 1e-8 … 1e-6, tol = 1e-6 … 1e-7
    elif optimizer_cls is COBYLA:
        optimizer = COBYLA(maxiter=150)
    else:
        optimizer = SPSA(maxiter=50)

    print(
        f"Debug: Creating VQE components with: num_spatial_orbitals={num_spatial_orbitals}, "
        f"num_particles={num_particles}, mapper={mapper.__class__.__name__}",
        file=sys.stderr)

    initial_state = HartreeFock(
        num_spatial_orbitals=num_spatial_orbitals,
        num_particles=num_particles,
        qubit_mapper=mapper
    )
    ansatz = PUCCSD(
        num_spatial_orbitals=num_spatial_orbitals,
        num_particles=num_particles,
        qubit_mapper=mapper,
        reps=ansatz_reps,
        initial_state=initial_state
    )

    return VQE(estimator, ansatz, optimizer)


def compute_single_point(distance, optimizer_name, mapper_name, atom_name,
                         ansatz_reps=1):
    """Compute a single PES point"""
    try:
        ansatz_reps = int(ansatz_reps)
    except ValueError:
        ansatz_reps = 1

    print(
        f"Debug: Computing point at {distance:.3f} Å with {optimizer_name} optimizer, "
        f"{mapper_name} mapper", file=sys.stderr)
    problem = build_problem(distance, atom_name)
    print(
        f"Debug: Problem built with {problem.num_spatial_orbitals} spatial orbitals, "
        f"{problem.num_particles} particles", file=sys.stderr)
    fermionic_op = problem.hamiltonian.second_q_op()

    mapper_cls = MAPPERS.get(mapper_name, JordanWignerMapper)
    if mapper_cls is ParityMapper:
        mapper = ParityMapper(num_particles=problem.num_particles)
        mapper = problem.get_tapered_mapper(mapper)
    else:
        mapper = mapper_cls()

    qubit_op = mapper.map(fermionic_op)

    vqe = create_vqe_local(mapper, problem.num_spatial_orbitals,
                           problem.num_particles, optimizer_name,
                           ansatz_reps)

    np_solver = NumPyMinimumEigensolver()

    vqe_result = vqe.compute_minimum_eigenvalue(qubit_op)
    vqe_energy = float(
        vqe_result.eigenvalue.real + problem.hamiltonian.nuclear_repulsion_energy)

    np_result = np_solver.compute_minimum_eigenvalue(qubit_op)
    np_energy = float(
        np_result.eigenvalue.real + problem.hamiltonian.nuclear_repulsion_energy)

    return {
        "distance": distance,
        "vqe": vqe_energy,
        "numpy": np_energy,
        "num_spatial_orbitals": problem.num_spatial_orbitals,
        "num_particles": problem.num_particles
    }
