import pytest
from qutip.settings import use_qutip_qip

try:
    # qutip_qip is installed
    import qutip_qip
    _qutip_qip_installed = True
    del qutip_qip
except ImportError:
    _qutip_qip_installed = False
    pass


@pytest.mark.skipif(not _qutip_qip_installed,
                    reason="The package qutip-qip is not installed.")
def test_qutip_qip_external():
    # Call a class that exists only in qutip_qip
    if use_qutip_qip:
        from qutip.qip.device import SCQubits
