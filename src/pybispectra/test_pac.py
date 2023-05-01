import numpy as np
from pybispectra.cfc import PAC, PPC
from pybispectra.tde import TDE
from pybispectra.utils import compute_fft

if __name__ == "__main__":
    rand = np.random.RandomState(44)
    data = rand.rand(10, 3, 200)
    sfreq = 100.0
    n_jobs = 1

    data = rand.rand(2, 2, 220)
    data[:, 1, 20:] = data[:, 0, :200].copy()
    data = data[:, :, :200]

    fft, freqs = compute_fft(
        data=data,
        sfreq=sfreq,
        n_points=2 * data.shape[2] + 1,
        window="hamming",
        return_neg_freqs=True,
        n_jobs=n_jobs,
    )

    # ppc = PPC(fft, freqs)
    # ppc.compute(n_jobs=n_jobs)
    # ppc_results = ppc.results
    # pac = PAC(fft, freqs)
    # pac.compute(symmetrise="none", normalise="none", n_jobs=n_jobs)
    # pac_results = pac.results
    # pac_results[0].plot()

    tde = TDE(fft, freqs, sfreq)
    tde.compute(
        symmetrise="none",
        n_jobs=n_jobs,
        indices=(np.array([0, 1]), np.array([1, 0])),
    )
    tde.results[0].plot()

    print("jeff")
