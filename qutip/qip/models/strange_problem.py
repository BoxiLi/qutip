
from qutip.operators import qeye  # no problem with this
from qutip.control.pulseoptim import optimize_pulse_unitary  # here the error
class Dummy():
    def __init__(self):
        pass