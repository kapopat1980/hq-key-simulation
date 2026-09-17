import os
os.makedirs("figures", exist_ok=True); os.makedirs("results", exist_ok=True)
import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6,
                     "lines.linewidth": 1.1, "legend.fontsize": 6.5, "legend.frameon": False,
                     "xtick.major.width": 0.5, "ytick.major.width": 0.5})
W = 4.8  # inches ~ 12.2 cm LNCS text width

q = json.load(open("results/qkd_results.json")); p = json.load(open("results/plkg_results.json"))
L = np.array(q["curves"]["L"])

# ---------------- Fig 1: architecture ----------------
fig = plt.figure(figsize=(W, 2.7)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 56); ax.axis("off")
def box(x, y, w, h, t, fc="#ffffff", fs=5.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.0", fc=fc, ec="black", lw=0.6))
    ax.text(x+w/2, y+h/2, t, ha="center", va="center", fontsize=fs, linespacing=1.15)
def arr(x1, y1, x2, y2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=6, lw=0.6, ls=ls, color="black"))
box(1, 33, 21, 17, "OLT / Central office\nQKD Tx (decoy BB84)\nKey mgmt. system\nPQC KEM (ML-KEM)", "#e8eef7")
box(1, 5, 21, 17, "SDN security\ncontroller\npolicy engine,\nQBER & KDR monitor", "#f3f3f3")
ax.plot([11.5, 11.5], [22.6, 32.4], color="black", lw=0.6, ls=(0, (2, 1.2)))
ax.plot([22.6, 38], [41.5, 41.5], color="black", lw=1.8)
ax.text(30.3, 44, "feeder fiber (WDM)", ha="center", fontsize=5.0)
ax.text(30.3, 36.2, "O-band quantum\n+ C/L-band data", ha="center", fontsize=4.7, style="italic")
box(38.5, 36.5, 7, 10, "1:N\nsplit")
ys = [46, 33.5, 21]; names = ["ONU 1", "ONU 2", "ONU N"]
for yy, nm in zip(ys, names):
    ax.plot([46.1, 52], [41.5, yy+4], color="black", lw=0.9)
    box(52, yy, 17, 8, nm + " + small cell\nQKD Rx  |  PLKG", "#e9f5ea", fs=4.9)
    ax.plot([69.6, 79], [yy+4, yy+6.3], color="#555555", lw=0.6, ls=(0, (2, 1.2)))
    ax.plot([69.6, 79], [yy+4, yy+1.7], color="#555555", lw=0.6, ls=(0, (2, 1.2)))
    box(79, yy, 20, 8, "wireless users\nCSI probing, KDR check", "#fdf3e3", fs=4.9)
ax.text(74.3, 31.2, "radio link", fontsize=4.5, style="italic", ha="center")
box(30, 3, 48, 11, "Hybrid key combiner:  $K_s$ = HKDF($K_{QKD}\\,\\|\\,K_{PLK}\\,\\|\\,K_{PQC}$ , ctx)\nAES-256-GCM session keys with adaptive re-key interval", "#fff7d6", fs=5.0)
arr(22.6, 11, 29.4, 9.5); arr(60.5, 20.4, 57, 14.6)
ax.text(99, 0.6, "Adversary: fiber tap, rogue ONU, nearby radio eavesdropper, jammer", fontsize=4.6, color="#b22222", ha="right")
fig.savefig("figures/fig1_arch.png", dpi=400); plt.close(fig)

# ---------------- Fig 2: QKD ----------------
fig, axs = plt.subplots(1, 2, figsize=(W, 1.95))
sty = ["-", "--", "-.", ":"]
for i, N in enumerate([1, 8, 16, 32]):
    y = np.array(q["curves"][f"split_{N}"]); y[y <= 0] = np.nan
    axs[0].semilogy(L, y, sty[i], color="k", label=f"1:{N}" if N > 1 else "P2P")
axs[0].set_xlabel("Feeder length (km)"); axs[0].set_ylabel("Secret key rate (b/s)")
axs[0].set_title("(a) split ratio, dark fiber", fontsize=7); axs[0].legend(); axs[0].set_ylim(1e1, 2e6)
for i, Pd in enumerate(["None", "10", "15", "20"]):
    y = np.array(q["curves"][f"coex16_{Pd}"]); y[y <= 0] = np.nan
    axs[1].semilogy(L, y, sty[i], color="k", label="no classical" if Pd == "None" else f"{Pd} dBm")
axs[1].set_xlabel("Feeder length (km)"); axs[1].set_title("(b) 1:16, total classical launch power", fontsize=7)
axs[1].legend(); axs[1].set_ylim(1e1, 2e6)
for a in axs: a.grid(alpha=0.25, lw=0.4)
fig.tight_layout(pad=0.2); fig.savefig("figures/fig2_qkd.png", dpi=400); plt.close(fig)

# ---------------- Fig 3: PLKG ----------------
fig, axs = plt.subplots(1, 2, figsize=(W, 1.95))
s = p["snr"]
for key, ls, lab in [("b1_fdt0.005", "-", "1-bit, $f_D\\tau$=0.005"), ("b2_fdt0.005", "--", "2-bit, $f_D\\tau$=0.005"),
                     ("b1_fdt0.02", "-.", "1-bit, $f_D\\tau$=0.02"), ("b2_fdt0.02", ":", "2-bit, $f_D\\tau$=0.02")]:
    axs[0].semilogy(s, p[key]["kdr_ab"], ls, color="k", label=lab)
axs[0].semilogy(s, p["b1_fdt0.005"]["kdr_ae"], "s-", color="#b22222", ms=2, label="Eve ($d=2\\lambda$)")
axs[0].set_xlabel("SNR (dB)"); axs[0].set_ylabel("Key disagreement rate"); axs[0].set_ylim(1.5e-3, 1); axs[0].legend(loc="lower left", fontsize=5.6, ncol=1)
axs[0].set_title("(a) Alice–Bob vs. Eve KDR", fontsize=7)
d = np.array(p["d"]); ke = np.array(p["eve_d"]["kdr_ae"]); ke_eff = np.minimum(ke, 1-ke)
axs[1].plot(d, ke_eff, "o-", color="k", ms=2.5, label="Eve effective KDR")
axs[1].set_xlabel("Eve distance $d/\\lambda$"); axs[1].set_ylabel("Eve KDR")
ax2 = axs[1].twinx(); ax2.plot(d, p["eve_d"]["I_AE"], "s--", color="#b22222", ms=2.5, label="$I(A;E)$")
ax2.plot(d, p["eve_d"]["practical"], "^:", color="#1f4e9a", ms=2.5, label="secure bits/sample")
ax2.set_ylabel("bits per sample")
h1, l1 = axs[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
axs[1].legend(h1+h2, l1+l2, loc="center right"); axs[1].set_title("(b) spatial decorrelation (20 dB)", fontsize=7)
for a in axs: a.grid(alpha=0.25, lw=0.4)
fig.tight_layout(pad=0.2); fig.savefig("figures/fig3_plkg.png", dpi=400); plt.close(fig)

# ---------------- Key budget ----------------
N_onu = 16
R_q = {"10dBm": q["summary"]["coex16_10"]["R_at_20km"], "20dBm": q["summary"]["coex16_20"]["R_at_20km"]}
samples_per_s = 20*16          # 2 f_D temporal x 16 decorrelated sub-bands (assumption)
i20 = p["snr"].index(20); i10 = p["snr"].index(10)
R_p = {"20dB": p["b2_fdt0.005"]["practical"][i20]*samples_per_s,
       "10dB": p["b2_fdt0.005"]["practical"][i10]*samples_per_s}
Ms = np.array([4, 8, 16, 32, 64])
budget = {}
for qk, Rq in R_q.items():
    per_onu = Rq/N_onu
    budget[f"qkd_only_{qk}"] = (256*(1+Ms)/per_onu).tolist()
    budget[f"hyb_backhaul_{qk}"] = 256/per_onu
for pk, Rp in R_p.items():
    budget[f"hyb_access_{pk}"] = 256/Rp
budget["R_q"] = R_q; budget["R_p"] = R_p; budget["Ms"] = Ms.tolist()
json.dump(budget, open("results/budget.json", "w"), indent=1)
print(json.dumps(budget, indent=1))

fig, ax = plt.subplots(figsize=(W*0.62, 1.8))
ax.semilogy(Ms, budget["qkd_only_10dBm"], "o-", color="k", ms=3, label="QKD-only, 10 dBm")
ax.semilogy(Ms, budget["qkd_only_20dBm"], "s--", color="k", ms=3, label="QKD-only, 20 dBm")
hyb20 = max(budget["hyb_backhaul_10dBm"], budget["hyb_access_20dB"])
hyb10 = max(budget["hyb_backhaul_20dBm"], budget["hyb_access_10dB"])
budget["hyb_best"] = hyb20; budget["hyb_worst"] = hyb10
json.dump(budget, open("results/budget.json", "w"), indent=1)
ax.semilogy(Ms, [hyb20]*len(Ms), "^-", color="#1f4e9a", ms=3, label="Hybrid (10 dBm, 20 dB)")
ax.semilogy(Ms, [hyb10]*len(Ms), "v:", color="#1f4e9a", ms=3, label="Hybrid (20 dBm, 10 dB)")
ax.set_xscale("log", base=2); ax.set_xticks(Ms); ax.set_xticklabels([str(m) for m in Ms])
ax.set_xlabel("Wireless users per ONU"); ax.set_ylabel("Min. re-key interval (s)")
ax.grid(alpha=0.25, lw=0.4); ax.set_ylim(0.2, 1500); ax.legend(loc="upper left", fontsize=5.4, ncol=2, columnspacing=0.8, handlelength=1.8)
fig.tight_layout(pad=0.2); fig.savefig("figures/fig4_budget.png", dpi=400); plt.close(fig)
