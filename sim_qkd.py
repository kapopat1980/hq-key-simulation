"""
Simulation 1 - Decoy-state BB84 (vacuum + weak decoy, asymptotic) over a
QKD-integrated PON feeder with co-propagating classical downstream traffic.
All parameters are modelling assumptions stated in Table 2 of the paper.
"""
import os

import numpy as np, json

h, c = 6.626e-34, 3e8

P = dict(
    f_rep=1e8,          # source repetition rate [Hz]
    mu=0.5, nu=0.1,     # signal / decoy mean photon number
    eta_d=0.20,         # detector efficiency
    p_dark=1e-6,        # dark count probability per gate
    e_det=0.015,        # optical misalignment error
    f_ec=1.16,          # error-correction inefficiency
    q=0.5,              # basis sifting factor
    alpha_q=0.33,       # O-band fibre loss [dB/km] (quantum channel 1310 nm)
    alpha_c=0.20,       # C/L-band fibre loss [dB/km] (classical downstream)
    IL_rx=2.0,          # receiver insertion loss (WDM filter, etc.) [dB]
    split_excess=1.0,   # excess loss of splitter [dB]
    rho=2.0e-12,        # effective Raman coeff. C-band pump -> O-band QKD [1/(km nm)]
    dlam=0.6,           # receiver filter bandwidth [nm]
    t_gate=1e-9,        # detector gate width [s]
    lam_q=1310e-9,
)

def H2(x):
    x = np.clip(x, 1e-12, 0.5)
    return -x*np.log2(x) - (1-x)*np.log2(1-x)

def raman_noise_prob(L, P_dBm, N_split=1, p=P):
    """Co-propagating spontaneous Raman noise photons per detector gate at one ONU.
    Raman light is generated in the feeder and then passes the 1:N splitter and the
    receiver, so it experiences the same splitter and receiver losses as the signal."""
    if P_dBm is None:
        return 0.0
    Pin = 1e-3*10**(P_dBm/10)
    a_c = p['alpha_c']*np.log(10)/10
    a_q = p['alpha_q']*np.log(10)/10
    # co-propagating: P_R = Pin*rho*dlam*(exp(-a_c L)-exp(-a_q L))/(a_q-a_c)
    PR = Pin*p['rho']*p['dlam']*(np.exp(-a_c*L)-np.exp(-a_q*L))/(a_q-a_c)
    nph = PR/(h*c/p['lam_q'])*p['t_gate']
    split_dB = 10*np.log10(N_split) + p['split_excess']*(N_split > 1)
    return nph*p['eta_d']*10**(-(split_dB + p['IL_rx'])/10)

def key_rate(L, N_split, P_dBm=None, p=P):
    loss_dB = p['alpha_q']*L + 10*np.log10(N_split) + p['split_excess']*(N_split>1) + p['IL_rx']
    eta = 10**(-loss_dB/10)*p['eta_d']
    Y0 = p['p_dark'] + raman_noise_prob(L, P_dBm, N_split, p)
    mu, nu, e0 = p['mu'], p['nu'], 0.5
    Qm = Y0 + 1 - np.exp(-eta*mu)
    Qn = Y0 + 1 - np.exp(-eta*nu)
    Em = (e0*Y0 + p['e_det']*(1-np.exp(-eta*mu)))/Qm
    En = (e0*Y0 + p['e_det']*(1-np.exp(-eta*nu)))/Qn
    Y1 = mu/(mu*nu-nu**2)*(Qn*np.exp(nu) - Qm*np.exp(mu)*nu**2/mu**2 - (mu**2-nu**2)/mu**2*Y0)
    Y1 = np.maximum(Y1, 1e-30)
    e1 = np.clip((En*Qn*np.exp(nu) - e0*Y0)/(Y1*nu), 0, 0.5)
    Q1 = Y1*mu*np.exp(-mu)
    R = p['q']*(-Qm*p['f_ec']*H2(Em) + Q1*(1-H2(e1)))
    return max(R, 0.0)*p['f_rep'], Em

def qber_intercept_resend(L, N, frac):
    """QBER when an intercept-resend attacker acts on a fraction 'frac' of pulses."""
    _, Em = key_rate(L, N)
    return Em + frac*0.25*(1-2*Em)

if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    out = {}
    Ls = np.arange(0, 121, 1)
    # (a) split ratio sweep, no classical coexistence
    for N in [1, 8, 16, 32]:
        out[f"split_{N}"] = [key_rate(L, N)[0] for L in Ls]
    # (b) coexistence power sweep, 1:16 split
    for Pd in [None, 10, 15, 20]:
        out[f"coex16_{Pd}"] = [key_rate(L, 16, Pd)[0] for L in Ls]
    out["L"] = Ls.tolist()

    def reach(arr, thr=1.0):
        arr = np.array(arr); idx = np.where(arr > thr)[0]
        return int(Ls[idx[-1]]) if len(idx) else 0

    summary = {}
    for k in out:
        if k != "L":
            summary[k] = dict(reach_km=reach(out[k]),
                              R_at_20km=out[k][20], R_at_10km=out[k][10])
    # intercept-resend detection threshold (QBER abort at 11%)
    fr = np.linspace(0, 1, 1001)
    q = np.array([qber_intercept_resend(20, 16, f) for f in fr])
    summary["ir_abort_fraction_20km_1x16"] = float(fr[np.argmax(q > 0.11)])
    summary["baseline_qber_20km_1x16"] = float(qber_intercept_resend(20, 16, 0))
    summary["raman_noise_20km_10dBm_1x16"] = float(raman_noise_prob(20, 10, 16))
    json.dump(dict(curves=out, summary=summary), open("results/qkd_results.json", "w"), indent=1)
    for k, v in summary.items():
        print(k, v)
