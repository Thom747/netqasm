import importlib
import random

import numpy as np
import pytest
from netsquid.qubits import qubitapi

from netqasm.examples.apps.blind_grover.app_client import main as blind_grover_client
from netqasm.examples.apps.blind_grover.app_server import main as blind_grover_server
from netqasm.examples.apps.blind_rotation.app_client import (
    main as blind_rotation_client,
)
from netqasm.examples.apps.blind_rotation.app_server import (
    main as blind_rotation_server,
)
from netqasm.logging.glob import get_netqasm_logger
from netqasm.runtime.application import default_app_instance
from netqasm.runtime.settings import Simulator, get_simulator
from netqasm.sdk.external import simulate_application

logger = get_netqasm_logger()


def fidelity_ok(qubit, dm, threshold=0.999):
    fidelity = qubitapi.fidelity(qubit, dm)
    return fidelity > threshold


def run_blind_rotation():
    ns = importlib.import_module("netsquid")
    num_iter = 4
    num_qubits = num_iter + 1
    phi = [random.uniform(0, 2 * np.pi) for _ in range(num_iter)]
    theta = [random.uniform(0, 2 * np.pi) for _ in range(num_qubits)]
    r = [random.randint(0, 1) for _ in range(num_iter)]

    alice_app_inputs = {"num_iter": num_iter, "theta": theta, "phi": phi, "r": r}

    bob_app_inputs = {"num_iter": num_iter}

    app_instance = default_app_instance(
        [
            ("client", blind_rotation_client),
            ("server", blind_rotation_server),
        ]
    )
    app_instance.program_inputs["client"] = alice_app_inputs
    app_instance.program_inputs["server"] = bob_app_inputs

    results = simulate_application(app_instance, enable_logging=False)[0]

    output_state = results["app_server"]["output_state"]
    s = results["app_client"]["s"]
    m = results["app_client"]["m"]
    r = results["app_client"]["r"]
    theta = results["app_client"]["theta"]

    s.extend([0, 0])
    m.extend([0, 0])
    r.extend([0, 0])

    # output should be (n = num_iter):
    # Rz(theta[n]) Z^m[n] X^{s[n-1]^r[n-1]} Z^{s[n-2]^r[n-2]} H Rz(phi[n-1]) H Rz(phi[n-2] ... |+>
    ref = ns.qubits.create_qubits(1)[0]
    ns.qubits.operate(ref, ns.H)
    for i in range(num_iter):
        ns.qubits.operate(ref, ns.qubits.create_rotation_op(phi[i], (0, 0, 1)))
        ns.qubits.operate(ref, ns.H)
    if m[num_iter] == 1:
        ns.qubits.operate(ref, ns.Z)
    if (s[num_iter - 1] ^ r[num_iter - 1]) == 1:
        ns.qubits.operate(ref, ns.X)
    if (s[num_iter - 2] ^ r[num_iter - 2]) == 1:
        ns.qubits.operate(ref, ns.Z)
    ns.qubits.operate(ref, ns.qubits.create_rotation_op(theta[num_iter], (0, 0, 1)))

    assert fidelity_ok(ref, np.array(output_state))


@pytest.mark.skipif(
    get_simulator() != Simulator.NETSQUID,
    reason="Can only run blind rotation tests using netsquid for now",
)
def test_blind_rotation():
    num = 3
    for _ in range(num):
        run_blind_rotation()


def run_blind_grover():
    b0 = random.randint(0, 1)
    b1 = random.randint(0, 1)

    r1 = random.randint(0, 1)
    r2 = random.randint(0, 1)

    theta1 = random.uniform(0, 2 * np.pi)
    theta2 = random.uniform(0, 2 * np.pi)

    alice_app_inputs = {
        "b0": b0,
        "b1": b1,
        "r1": r1,
        "r2": r2,
        "theta1": theta1,
        "theta2": theta2,
    }

    bob_app_inputs = {}

    app_instance = default_app_instance(
        [
            ("client", blind_grover_client),
            ("server", blind_grover_server),
        ]
    )
    app_instance.program_inputs["client"] = alice_app_inputs
    app_instance.program_inputs["server"] = bob_app_inputs

    # results = run_applications(applications)
    results = simulate_application(app_instance, enable_logging=False)[0]

    m0 = results["app_client"]["result0"]
    m1 = results["app_client"]["result1"]

    assert b0 == m0
    assert b1 == m1


def test_blind_grover():
    num = 3
    for _ in range(num):
        run_blind_grover()


if __name__ == "__main__":
    run_blind_rotation()
    run_blind_grover()
