"""
Simulation 2 - Channel-reciprocity physical-layer key generation (PLKG)
for the wireless segment (ONU/small-cell <-> user), with a passive
eavesdropper at distance d. Monte Carlo, Rayleigh fading, Jakes correlation.
"""
import os

import numpy as np, json
from scipy.special import j0
from scipy.stats import norm, chi2
from math import erfc, sqrt

rng = np.random.default_rng(2026)
NS = 200_000                      # channel samples per point

def H2(x):
    x = np.clip(x, 1e-12, 0.5)
    return -x*np.log2(x) - (1-x)*np.log2(1-x)

def gray(n):
    return n ^ (n >> 1)

def quantize(x, bits):
    """CDF-based equiprobable quantiser (x ~ N(0,s^2) per real dimension), Gray coded."""
    s = np.std(x)
    u = norm.cdf(x/s)
    lv = np.minimum((u*(2**bits)).astype(int), 2**bits-1)
    g = gray(lv)
    return ((g[:, None] >> np.arange(bits)[::-1]) & 1).astype(np.uint8).ravel()

def cn(n):
    return (rng.standard_normal(n) + 1j*rng.standard_normal(n))/np.sqrt(2)

def simulate(snr_db, d_over_lambda, bits, fd_tau=0.005, n=NS):
    """fd_tau: Doppler x probing delay (non-simultaneous TDD probing)."""
    rho_t = j0(2*np.pi*fd_tau)              # reciprocity decorrelation
    rho_s = j0(2*np.pi*d_over_lambda)       # spatial correlation to Eve
    g = 10**(snr_db/10)
    h = cn(n)
    hB = rho_t*h + np.sqrt(1-rho_t**2)*cn(n)     # reverse-link channel
    hE = rho_s*h + np.sqrt(1-rho_s**2)*cn(n)     # Eve's channel (A->E)
    sig = 1/np.sqrt(g)
    xA = h + sig*cn(n)
    xB = hB + sig*cn(n)
    xE = hE + sig*cn(n)
    kA = np.concatenate([quantize(xA.real, bits), quantize(xA.imag, bits)])
    kB = np.concatenate([quantize(xB.real, bits), quantize(xB.imag, bits)])
    kE = np.concatenate([quantize(xE.real, bits), quantize(xE.imag, bits)])
    kdr_ab = np.mean(kA != kB)
    kdr_ae = np.mean(kA != kE)
    # Gaussian information-theoretic quantities per real dimension
    vA = 0.5*(1+1/g)                       # per real-dimension variance
    cAB = 0.5*rho_t; cAE = 0.5*rho_s; cBE = 0.5*rho_t*rho_s
    S = np.array([[vA, cAB, cAE], [cAB, vA, cBE], [cAE, cBE, vA]])
    det = np.linalg.det
    I_AB = -0.5*np.log2(1-(cAB/vA)**2)
    I_AE = -0.5*np.log2(1-(cAE/vA)**2)
    I_AB_E = 0.5*np.log2(det(S[np.ix_([0,2],[0,2])])*det(S[np.ix_([1,2],[1,2])])
                         /(det(S[np.ix_([2],[2])])*det(S)))
    m = 2*bits                                            # raw bits / complex sample
    practical = max(0.0, m*(1-1.16*H2(kdr_ab)) - 2*I_AE)  # conservative
    return dict(kdr_ab=float(kdr_ab), kdr_ae=float(kdr_ae),
                I_AB=float(2*I_AB), I_AE=float(2*I_AE), Csk=float(2*I_AB_E),
                practical=float(practical), keyA=kA[:20000])

def nist_tests(bits):
    b = bits.astype(int); n = len(b)
    s = np.sum(2*b-1); p_mono = erfc(abs(s)/sqrt(2*n))
    pi = b.mean(); vobs = 1 + np.sum(b[1:] != b[:-1])
    p_runs = erfc(abs(vobs-2*n*pi*(1-pi))/(2*sqrt(2*n)*pi*(1-pi)))
    M = 128; N = n//M; blocks = b[:N*M].reshape(N, M).mean(1)
    p_block = float(chi2.sf(4*M*np.sum((blocks-0.5)**2), N))
    return dict(monobit=float(p_mono), runs=float(p_runs), block=p_block)

if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    snrs = list(range(0, 31, 2))
    res = {"snr": snrs}
    for bits in [1, 2]:
        for fdt in [0.005, 0.02]:
            key = f"b{bits}_fdt{fdt}"
            r = [simulate(s, 2.0, bits, fdt) for s in snrs]
            res[key] = {k: [x[k] for x in r] for k in ["kdr_ab", "kdr_ae", "Csk", "practical", "I_AB"]}
    dl = [0.0, 0.05, 0.1, 0.2, 0.3, 0.383, 0.5, 0.75, 1.0, 1.5, 2.0]
    res["d"] = dl
    rE = [simulate(20, d, 1, 0.005) for d in dl]
    res["eve_d"] = {k: [x[k] for x in rE] for k in ["kdr_ae", "I_AE", "Csk", "practical"]}
    # randomness on a long 1-bit key at 20 dB (before privacy amplification)
    r20 = simulate(20, 2.0, 1, 0.005, n=200_000)
    rnd = nist_tests(r20["keyA"])
    r20b = simulate(20, 2.0, 2, 0.005, n=200_000)
    rnd2 = nist_tests(r20b["keyA"])
    res["nist_1bit"] = rnd; res["nist_2bit"] = rnd2
    json.dump(res, open("results/plkg_results.json", "w"), indent=1)
    i20 = snrs.index(20); i10 = snrs.index(10)
    for k in ["b1_fdt0.005", "b2_fdt0.005", "b1_fdt0.02", "b2_fdt0.02"]:
        print(k, "KDR@10dB", round(res[k]["kdr_ab"][i10], 4), "KDR@20dB", round(res[k]["kdr_ab"][i20], 4),
              "Eve KDR@20", round(res[k]["kdr_ae"][i20], 4), "Csk@20", round(res[k]["Csk"][i20], 3),
              "prac@20", round(res[k]["practical"][i20], 3), "prac@10", round(res[k]["practical"][i10], 3))
    print("eve vs d:", [(d, round(a, 3), round(b, 3), round(c, 3)) for d, a, b, c in
                        zip(dl, res["eve_d"]["kdr_ae"], res["eve_d"]["I_AE"], res["eve_d"]["practical"])])
    print("NIST 1bit", rnd, "2bit", rnd2)
