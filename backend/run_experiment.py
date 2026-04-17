#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import random
import json
import os

from pyscf import gto, scf, fci

from qiskit_algorithms.optimizers import COBYLA, SLSQP, SPSA
from qiskit_algorithms import VQE
from qiskit.primitives import StatevectorEstimator

from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import (
    JordanWignerMapper,
    BravyiKitaevMapper,
    ParityMapper
)
from qiskit_nature.second_q.algorithms import GroundStateEigensolver
from qiskit_nature.second_q.circuit.library import UCCSD

# =========================================================
# CONFIG
# =========================================================

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

MAPPERS = {
    "JW": JordanWignerMapper(),
    "BK": BravyiKitaevMapper(),
    "Parity": ParityMapper(),
}

OPTIMIZERS = {
    "COBYLA": COBYLA(maxiter=40),
    "SLSQP": SLSQP(maxiter=40),
    "SPSA": SPSA(maxiter=40),
}

ARMS = [(m, o) for m in MAPPERS for o in OPTIMIZERS]

DISTANCES = np.linspace(0.7, 2.0, 5)

MOLECULES = [
    "NH",
    "HF",
    "B2",
    "C2",
    "N2",
    "F2",
    "BF",
    "CF",
    "BN",
    "CN",
    "CO"
]

ALPHA = 1.0
MAX_ROUNDS = 2
QUALITY_THRESHOLD = 5e-4

# =========================================================
# SAFE MOLECULE BUILDER
# =========================================================

def build_molecule(name, r):

    # --- diatomics ---
    if name == "NH":
        atom = f"N 0 0 0; H 0 0 {r}"
        charge, spin = 0, 0

    elif name == "HF":
        atom = f"H 0 0 0; F 0 0 {r}"
        charge, spin = 0, 0

    elif name == "B2":
        atom = f"B 0 0 0; B 0 0 {r}"
        charge, spin = 0, 0  # approx singlet baseline

    elif name == "C2":
        atom = f"C 0 0 0; C 0 0 {r}"
        charge, spin = 0, 0

    elif name == "N2":
        atom = f"N 0 0 0; N 0 0 {r}"
        charge, spin = 0, 0

    elif name == "F2":
        atom = f"F 0 0 0; F 0 0 {r}"
        charge, spin = 0, 0

    elif name == "BF":
        atom = f"B 0 0 0; F 0 0 {r}"
        charge, spin = 0, 0

    elif name == "CF":
        atom = f"C 0 0 0; F 0 0 {r}"
        charge, spin = 0, 0

    elif name == "BN":
        atom = f"B 0 0 0; N 0 0 {r}"
        charge, spin = 0, 0

    elif name == "CN":
        atom = f"C 0 0 0; N 0 0 {r}"
        charge, spin = 0, 0

    elif name == "CO":
        atom = f"C 0 0 0; O 0 0 {r}"
        charge, spin = 0, 0

    else:
        raise ValueError(name)

    return gto.M(
        atom=atom,
        basis="sto3g",
        charge=charge,
        spin=spin,
        verbose=0
    )

# =========================================================
# FCI (robust)
# =========================================================

def compute_fci(mol):
    try:
        mf = scf.RHF(mol).run()
        cisolver = fci.FCI(mol, mf.mo_coeff)
        e, _ = cisolver.kernel()
        return float(e)
    except:
        return None

# =========================================================
# VQE
# =========================================================

def run_vqe(mol, mapper_name, opt_name):
    try:
        driver = PySCFDriver(
            atom=mol.atom,
            basis="sto3g",
            charge=mol.charge
        )

        problem = driver.run()

        mapper = MAPPERS[mapper_name]
        optimizer = OPTIMIZERS[opt_name]

        ansatz = UCCSD(
            problem.num_spatial_orbitals,
            problem.num_particles,
            mapper
        )

        vqe = VQE(
            estimator=StatevectorEstimator(),
            ansatz=ansatz,
            optimizer=optimizer
        )

        solver = GroundStateEigensolver(mapper, vqe)
        result = solver.solve(problem)

        return float(result.total_energies[0])

    except:
        return None

# =========================================================
# SCAN
# =========================================================

def run_scan(molecule, mapper, optimizer):

    results = {}

    for r in DISTANCES:
        mol = build_molecule(molecule, r)

        e_ref = compute_fci(mol)
        e_vqe = run_vqe(mol, mapper, optimizer)

        if e_ref is None or e_vqe is None:
            results[str(round(r, 2))] = {"error": "failed"}
        else:
            results[str(round(r, 2))] = {
                "vqe": e_vqe,
                "ref": e_ref
            }

    return results

# =========================================================
# STATS
# =========================================================

def avg_error(results):
    vals = [
        abs(v["vqe"] - v["ref"])
        for v in results.values()
        if "error" not in v
    ]
    return np.mean(vals) if vals else None

def reward(err):
    return 1.0 / (1.0 + err * 1000) if err is not None else 0

# =========================================================
# STRATEGY
# =========================================================

class LinUCB:
    def __init__(self, dim=6):
        self.A = {a: np.eye(dim) for a in ARMS}
        self.b = {a: np.zeros(dim) for a in ARMS}

    def select(self, x):
        best, best_score = None, -1e18
        for arm in ARMS:
            Ainv = np.linalg.inv(self.A[arm])
            theta = Ainv @ self.b[arm]
            score = theta @ x + ALPHA * np.sqrt(x @ Ainv @ x)
            if score > best_score:
                best, best_score = arm, score
        return best

    def update(self, arm, x, r):
        self.A[arm] += np.outer(x, x)
        self.b[arm] += r * x


def context_vector(mol):
    return np.array([
        mol.nelectron,
        mol.nao_nr(),
        mol.energy_nuc(),
        1.0, 1.0, 1.0
    ], dtype=float)


def run_strategy(molecule, mode):

    print(f"\n### {mode.upper()} | {molecule}")

    agent = LinUCB()
    best = {}

    for rnd in range(2):

        mol0 = build_molecule(molecule, 1.0)
        x = context_vector(mol0)

        if mode == "linucb":
            mapper, opt = agent.select(x)
        elif mode == "random":
            mapper, opt = random.choice(ARMS)
        else:
            mapper, opt = ("JW", "COBYLA")

        print(f"Round {rnd+1}: {mapper}+{opt}")

        scan = run_scan(molecule, mapper, opt)
        results = scan

        for k, v in results.items():
            if "error" in v:
                continue

            if k not in best:
                best[k] = v
            else:
                old = abs(best[k]["vqe"] - best[k]["ref"])
                new = abs(v["vqe"] - v["ref"])
                if new < old:
                    best[k] = v

        err = avg_error(best)
        r = reward(err)

        print(" avg_error=", err)

        if mode == "linucb":
            agent.update((mapper, opt), x, r)

    return best

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    for mol in MOLECULES:
        for mode in ["linucb", "random", "fixed"]:
            res = run_strategy(mol, mode)

            path = os.path.join(RESULTS_DIR, f"{mol}_{mode}.json")
            with open(path, "w") as f:
                json.dump(res, f, indent=2)

            print("Saved →", path)
