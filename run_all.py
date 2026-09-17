"""Reproduce every result, table value, and figure in the HQ-KEY paper."""
import subprocess, sys, time

steps = [
    ("QKD layer (decoy-state BB84 in a PON)", "sim_qkd.py"),
    ("Wireless layer (physical-layer key generation, Monte Carlo)", "sim_plkg.py"),
    ("Figures and end-to-end key budget", "make_figs.py"),
]
for name, script in steps:
    print(f"\n=== {name}: {script} ===", flush=True)
    t0 = time.time()
    subprocess.run([sys.executable, script], check=True)
    print(f"--- done in {time.time() - t0:.1f} s", flush=True)
print("\nAll results are in results/ and all figures are in figures/.")
