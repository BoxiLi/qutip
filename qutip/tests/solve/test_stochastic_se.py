import pytest
import numpy as np
from numpy.testing import assert_

from qutip import (
    ssesolve, destroy, coherent, mesolve, fock, qeye, parallel_map,
    photocurrent_sesolve, num,
)


def f(t, args):
    return args["a"] * t


@pytest.mark.slow
def test_ssesolve_homodyne_methods():
    "Stochastic: ssesolve: homodyne methods with single jump operator"

    def arccoth(x):
        return 0.5*np.log((1.+x)/(x-1.))

    th = 0.1 # Interaction parameter
    alpha = np.cos(th)
    beta = np.sin(th)
    gamma = 1.

    N = 30                 # number of Fock states
    Id = qeye(N)
    a = destroy(N)
    s = 0.5*((alpha+beta)*a + (alpha-beta)*a.dag())
    x = (a + a.dag()) * 2**-0.5
    H = Id + gamma * a * a.dag()
    sc_op = [s]
    e_op = [x, x*x]
    rho0 = fock(N,0)      # initial vacuum state

    T = 6.                   # final time
    # number of time steps for which we save the expectation values
    N_store = 200
    Nsub = 10
    tlist = np.linspace(0, T, N_store)
    ddt = (tlist[1]-tlist[0])

    #### No analytic solution for ssesolve, taylor15 with 500 substep
    sol = ssesolve(H, rho0, tlist, sc_op, e_op,
                   nsubsteps=1000, method='homodyne', solver='taylor1.5')
    y_an = (sol.expect[1]-sol.expect[0]*sol.expect[0].conj())


    list_methods_tol = [['euler-maruyama', 3e-2],
                        ['pc-euler', 5e-3],
                        ['pc-euler-2', 5e-3],
                        ['platen', 5e-3],
                        ['milstein', 5e-3],
                        ['milstein-imp', 5e-3],
                        ['taylor1.5', 5e-4],
                        ['taylor1.5-imp', 5e-4],
                        ['explicit1.5', 5e-4],
                        ['taylor2.0', 5e-4]]
    for n_method in list_methods_tol:
        # Comparisons of error between sol and sol3 depend on the stochastic
        # noise, thus the seed, fixing the seed remove random fails.
        np.random.seed(1)
        sol = ssesolve(H, rho0, tlist, sc_op, e_op,
                       nsubsteps=Nsub, method='homodyne', solver=n_method[0])
        sol2 = ssesolve(H, rho0, tlist, sc_op, e_op, store_measurement=0,
                       nsubsteps=Nsub, method='homodyne', solver=n_method[0],
                       noise = sol.noise)
        sol3 = ssesolve(H, rho0, tlist, sc_op, e_op,
                        nsubsteps=Nsub*10, method='homodyne',
                        solver=n_method[0], tol=1e-8)
        err = 1/T * np.sum(np.abs(y_an - \
                    (sol.expect[1]-sol.expect[0]*sol.expect[0].conj())))*ddt
        err3 = 1/T * np.sum(np.abs(y_an - \
                    (sol3.expect[1]-sol3.expect[0]*sol3.expect[0].conj())))*ddt
        assert err < n_method[1]
        # 5* more substep should decrease the error
        assert err3 < err
        # just to check that noise is not affected by ssesolve
        assert np.all(sol.noise == sol2.noise)
        assert np.all(sol.expect[0] == sol2.expect[0])

    sol = ssesolve(H, rho0, tlist[:2], sc_op, e_op, noise=10, ntraj=2,
                    nsubsteps=Nsub, method='homodyne', solver='euler',
                    store_measurement=1)
    sol2 = ssesolve(H, rho0, tlist[:2], sc_op, e_op, noise=10, ntraj=2,
                    nsubsteps=Nsub, method='homodyne', solver='euler',
                    store_measurement=0)
    sol3 = ssesolve(H, rho0, tlist[:2], sc_op, e_op, noise=11, ntraj=2,
                    nsubsteps=Nsub, method='homodyne', solver='euler')
    # sol and sol2 have the same seed, sol3 differ.
    assert np.all(sol.noise == sol2.noise)
    assert np.all(sol.noise != sol3.noise)
    assert not np.all(sol.measurement[0] == 0.+0j)
    assert np.all(sol2.measurement[0] == 0.+0j)
    sol = ssesolve(H, rho0, tlist[:2], sc_op, e_op, noise=np.array([1,2]),
                   ntraj=2, nsubsteps=Nsub, method='homodyne', solver='euler')
    sol2 = ssesolve(H, rho0, tlist[:2], sc_op, e_op, noise=np.array([2,1]),
                   ntraj=2, nsubsteps=Nsub, method='homodyne', solver='euler')
    # sol and sol2 have the seed of traj 1 and 2 reversed.
    assert np.all(sol.noise[0,:,:,:] == sol2.noise[1,:,:,:])
    assert np.all(sol.noise[1,:,:,:] == sol2.noise[0,:,:,:])


def test_ssesolve_photocurrent():
    "Stochastic: photocurrent_sesolve"
    tol = 0.01

    N = 4
    gamma = 0.25
    ntraj = 25
    nsubsteps = 100
    a = destroy(N)

    H = [[a.dag() * a,f]]
    psi0 = coherent(N, 0.5)
    sc_ops = [np.sqrt(gamma) * a, np.sqrt(gamma) * a*0.5]
    e_ops = [a.dag() * a, a + a.dag(), (-1j)*(a - a.dag())]

    times = np.linspace(0, 2.5, 50)
    res_ref = mesolve(H, psi0, times, sc_ops, e_ops, args={"a":2})
    res = photocurrent_sesolve(H, psi0, times, sc_ops, e_ops, ntraj=ntraj,
                              nsubsteps=nsubsteps, store_measurement=True,
                              map_func=parallel_map, args={"a":2})

    np.testing.assert_allclose(res.expect, res_ref.expect, atol=tol)
    assert len(res.measurement) == ntraj
    assert all([m.shape == (len(times), len(sc_ops)) for m in res.measurement])


def test_ssesolve_homodyne():
    "Stochastic: ssesolve: homodyne, time-dependent H"
    tol = 0.01

    N = 4
    gamma = 0.25
    ntraj = 25
    nsubsteps = 100
    a = destroy(N)

    H = [[a.dag() * a,f]]
    psi0 = coherent(N, 0.5)
    sc_ops = [np.sqrt(gamma) * a, np.sqrt(gamma) * a*0.5]
    e_ops = [a.dag() * a, a + a.dag(), (-1j)*(a - a.dag())]

    times = np.linspace(0, 2.5, 50)
    res_ref = mesolve(H, psi0, times, sc_ops, e_ops, args={"a":2})
    res = ssesolve(H, psi0, times, sc_ops, e_ops,
                   ntraj=ntraj, nsubsteps=nsubsteps,
                   method='homodyne', store_measurement=True,
                   map_func=parallel_map, args={"a":2})

    np.testing.assert_allclose(res.expect, res_ref.expect, atol=tol)
    assert len(res.measurement) == ntraj
    assert all(m.shape == (len(times), len(sc_ops)) for m in res.measurement)


@pytest.mark.slow
def test_ssesolve_heterodyne():
    "Stochastic: ssesolve: heterodyne, time-dependent H"
    tol = 0.01

    N = 4
    gamma = 0.25
    ntraj = 25
    nsubsteps = 100
    a = destroy(N)

    H = [[a.dag() * a,f]]
    psi0 = coherent(N, 0.5)
    sc_ops = [np.sqrt(gamma) * a, np.sqrt(gamma) * a*0.5]
    e_ops = [a.dag() * a, a + a.dag(), (-1j)*(a - a.dag())]

    times = np.linspace(0, 2.5, 50)
    res_ref = mesolve(H, psi0, times, sc_ops, e_ops, args={"a":2})
    res = ssesolve(H, psi0, times, sc_ops, e_ops,
                   ntraj=ntraj, nsubsteps=nsubsteps,
                   method='heterodyne', store_measurement=True,
                   map_func=parallel_map, args={"a":2})

    np.testing.assert_allclose(res.expect, res_ref.expect, atol=tol)
    assert len(res.measurement) == ntraj
    assert all(m.shape == (len(times), len(sc_ops), 2)
               for m in res.measurement)


def f_dargs(t, args):
    return args["expect_op_3"] - 1


@pytest.mark.xfail(reason="not yet working")
def test_ssesolve_feedback():
    "Stochastic: ssesolve: time-dependent H with feedback"
    tol = 0.01
    N = 4
    ntraj = 10
    nsubsteps = 100
    a = destroy(N)

    H = [num(N)]
    psi0 = coherent(N, 2.5)
    sc_ops = [[a + a.dag(), f_dargs]]
    e_ops = [a.dag() * a, a + a.dag(), (-1j)*(a - a.dag()), qeye(N)]

    times = np.linspace(0, 10, 101)
    res_ref = mesolve(H, psi0, times, sc_ops, e_ops,
                      args={"expect_op_3": qeye(N)})
    res = ssesolve(H, psi0, times, sc_ops, e_ops, solver=None, noise=1,
                   ntraj=ntraj, nsubsteps=nsubsteps, method='homodyne',
                   map_func=parallel_map, args={"expect_op_3": qeye(N)})
    np.testing.assert_allclose(res.expect, res_ref.expect, atol=tol)


def test_ssesolve_bad_e_ops():
    tol = 0.01
    N = 4
    ntraj = 10
    nsubsteps = 100
    a = destroy(N)
    b = destroy(N-1)

    H = [num(N)]
    psi0 = coherent(N, 2.5)
    sc_ops = [a + a.dag()]
    e_ops = [a.dag() * a, a + a.dag(), (-1j)*(b - b.dag()), qeye(N+1)]
    times = np.linspace(0, 10, 101)
    with pytest.raises(TypeError) as exc:
        res = ssesolve(H, psi0, times, sc_ops, e_ops, solver=None, noise=1,
                       ntraj=ntraj, nsubsteps=nsubsteps, method='homodyne',
                       map_func=parallel_map)