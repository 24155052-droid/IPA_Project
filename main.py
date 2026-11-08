"""Runs every experiment of the project and writes figures + tables to results/.

    python main.py

Everything is deterministic (fixed seeds), so the numbers in the report are
reproduced exactly.
"""
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from lsb import embed_lsb, extract_lsb, text_to_bits, bits_to_text, capacity_bits
from dct_wm import embed_dct, extract_dct, n_blocks
from metrics import psnr, ssim, ber, normalized_correlation, entropy
import attacks as A
from steganalysis import chi_square_pov

IMG = os.path.join(ROOT, "images")
OUT = os.path.join(ROOT, "results")
os.makedirs(OUT, exist_ok=True)

KEY = 2026            # stego key: seeds the pseudo-random embedding order
DELTA = 24.0          # default QIM step
WM_SIDE = 16          # watermark is a 16x16 binary logo = 256 bits
REPEAT = 4            # repetition factor of the robust DCT scheme
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.25})

results = {}


def load_gray():
    return np.array(Image.open(os.path.join(IMG, "camera.png")).convert("L"))


def load_color():
    return np.array(Image.open(os.path.join(IMG, "astronaut.png")).convert("RGB"))


def make_watermark(side=WM_SIDE):
    """A 16x16 binary logo: the initials 'SD' drawn with a bitmap font."""
    big = Image.new("L", (64, 64), 0)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 32), "SD", fill=255, font=font, anchor="mm")
    small = big.resize((side, side), Image.BILINEAR)
    return (np.array(small) > 90).astype(np.uint8)


def show(ax, img, title, cmap="gray"):
    ax.imshow(img, cmap=cmap, vmin=0, vmax=255 if cmap == "gray" else None)
    ax.set_title(title, fontsize=8)
    ax.axis("off")
    ax.grid(False)


cover = load_gray()
wm = make_watermark()
wm_bits = wm.ravel()
N = len(wm_bits)

# ---------------------------------------------------------------- Part 1: LSB
print("Part 1: LSB capacity and imperceptibility")
rng = np.random.default_rng(0)
rows = []
fig, axs = plt.subplots(2, 5, figsize=(12, 5))
show(axs[0, 0], cover, "Cover")
axs[1, 0].axis("off")
for i, k in enumerate([1, 2, 3, 4]):
    payload = rng.integers(0, 2, capacity_bits(cover, k), dtype=np.uint8)
    stego = embed_lsb(cover, payload, k)
    ok = bool(np.array_equal(extract_lsb(stego, len(payload), k), payload))
    row = dict(k=k, capacity_bytes=capacity_bits(cover, k) // 8,
               bpp=k, psnr=psnr(cover, stego), ssim=ssim(cover, stego), exact=ok)
    rows.append(row)
    show(axs[0, i + 1], stego, f"k={k}  PSNR {row['psnr']:.1f} dB")
    diff = np.abs(stego.astype(int) - cover.astype(int))
    show(axs[1, i + 1], np.clip(diff * (255 // max(diff.max(), 1)), 0, 255), f"|difference| scaled (max {diff.max()})")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig1_lsb_capacity.png"), dpi=150)
plt.close()
results["lsb_capacity"] = rows

# text message demo
msg = "Sayangsu Dawn | CSE-33 | 24155052"
mbits = text_to_bits(msg)
stego_t = embed_lsb(cover, mbits, 1, key=KEY)
back = bits_to_text(extract_lsb(stego_t, len(mbits), 1, key=KEY))
wrong = bits_to_text(extract_lsb(stego_t, len(mbits), 1, key=KEY + 1))
results["text_demo"] = dict(message=msg, bits=int(len(mbits)), recovered=back,
                            wrong_key_recovered=wrong.encode("unicode_escape").decode(),
                            psnr=psnr(cover, stego_t))

# bit-plane figure
fig, axs = plt.subplots(2, 4, figsize=(10, 5.2))
for b in range(8):
    plane = ((cover >> b) & 1) * 255
    show(axs[b // 4, b % 4], plane, f"Bit plane {b}" + (" (LSB)" if b == 0 else " (MSB)" if b == 7 else ""))
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig2_bitplanes.png"), dpi=150)
plt.close()

# ------------------------------------------------- Part 2: DCT-QIM watermark
print("Part 2: DCT-domain watermark")
wm_img = embed_dct(cover, wm_bits, DELTA, repeat=REPEAT, key=KEY)
ext = extract_dct(wm_img, N, DELTA, repeat=REPEAT, key=KEY)
jp50 = A.jpeg(wm_img, 50)
ext50 = extract_dct(jp50, N, DELTA, repeat=REPEAT, key=KEY)
results["dct_default"] = dict(delta=DELTA, repeat=REPEAT, bits=N,
                              psnr=psnr(cover, wm_img), ssim=ssim(cover, wm_img),
                              ber_clean=ber(wm_bits, ext), ber_jpeg50=ber(wm_bits, ext50),
                              nc_jpeg50=normalized_correlation(wm_bits, ext50))
fig, axs = plt.subplots(1, 5, figsize=(13, 3))
show(axs[0], cover, "Original")
show(axs[1], wm_img, f"Watermarked  {results['dct_default']['psnr']:.1f} dB")
d = np.abs(wm_img.astype(int) - cover.astype(int))
show(axs[2], np.clip(d * 20, 0, 255), "|difference| x20")
show(axs[3], wm * 255, "Embedded watermark")
show(axs[4], ext50.reshape(WM_SIDE, WM_SIDE) * 255, f"Extracted after JPEG-50 (BER {results['dct_default']['ber_jpeg50']:.3f})")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig3_dct_watermark.png"), dpi=150)
plt.close()

# ------------------------------------------------------- Part 3: attacks
print("Part 3: robustness to attacks")
attack_list = [
    ("No attack", lambda x: x),
    ("JPEG Q90", lambda x: A.jpeg(x, 90)),
    ("JPEG Q70", lambda x: A.jpeg(x, 70)),
    ("JPEG Q50", lambda x: A.jpeg(x, 50)),
    ("JPEG Q30", lambda x: A.jpeg(x, 30)),
    ("Gaussian noise s=2", lambda x: A.gaussian_noise(x, 2)),
    ("Gaussian noise s=5", lambda x: A.gaussian_noise(x, 5)),
    ("Gaussian noise s=10", lambda x: A.gaussian_noise(x, 10)),
    ("Salt&pepper 1%", lambda x: A.salt_pepper(x, 0.01)),
    ("Salt&pepper 5%", lambda x: A.salt_pepper(x, 0.05)),
    ("Gaussian blur s=0.8", lambda x: A.blur(x, 0.8)),
    ("Gaussian blur s=1.5", lambda x: A.blur(x, 1.5)),
    ("Median 3x3", lambda x: A.median(x, 3)),
    ("Crop 10% rows", lambda x: A.crop_fill(x, 0.10)),
    ("Crop 25% rows", lambda x: A.crop_fill(x, 0.25)),
    ("Rescale 0.75", lambda x: A.scale_roundtrip(x, 0.75)),
    ("Rescale 0.5", lambda x: A.scale_roundtrip(x, 0.5)),
    ("Brightness +20", lambda x: A.brightness(x, 20)),
]
lsb_img = embed_lsb(cover, wm_bits, 1, key=KEY)
dct1_img = embed_dct(cover, wm_bits, DELTA, repeat=1, key=KEY)
dct4_img = wm_img
schemes = {
    "LSB (k=1)": (lsb_img, lambda x: extract_lsb(x, N, 1, key=KEY)),
    "DCT-QIM r=1": (dct1_img, lambda x: extract_dct(x, N, DELTA, repeat=1, key=KEY)),
    "DCT-QIM r=4": (dct4_img, lambda x: extract_dct(x, N, DELTA, repeat=REPEAT, key=KEY)),
}
scheme_quality = {s: dict(psnr=psnr(cover, im), ssim=ssim(cover, im)) for s, (im, _) in schemes.items()}
attack_table = []
for name, fn in attack_list:
    row = {"attack": name}
    for s, (im, ex) in schemes.items():
        row[s] = ber(wm_bits, ex(fn(im)))
    attack_table.append(row)
results["scheme_quality"] = scheme_quality
results["attacks"] = attack_table

fig, ax = plt.subplots(figsize=(11, 4.2))
x = np.arange(len(attack_table))
w = 0.27
cols = ["#c0392b", "#2c7fb8", "#1a9850"]
for j, s in enumerate(schemes):
    ax.bar(x + (j - 1) * w, [r[s] for r in attack_table], w, label=s, color=cols[j])
ax.set_xticks(x)
ax.set_xticklabels([r["attack"] for r in attack_table], rotation=60, ha="right", fontsize=8)
ax.set_ylabel("Bit error rate (lower is better)")
ax.axhline(0.5, color="k", ls=":", lw=1)
ax.text(len(x) - 0.5, 0.51, "0.5 = guessing", ha="right", fontsize=8)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig4_attack_ber.png"), dpi=150)
plt.close()

# ------------------------------------------- Part 4: delta trade-off
print("Part 4: imperceptibility / robustness trade-off")
trade = []
for delta in [8, 12, 16, 24, 32, 48, 64]:
    im = embed_dct(cover, wm_bits, delta, repeat=REPEAT, key=KEY)
    row = dict(delta=delta, psnr=psnr(cover, im), ssim=ssim(cover, im))
    for label, fn in [("jpeg50", lambda x: A.jpeg(x, 50)), ("jpeg30", lambda x: A.jpeg(x, 30)),
                      ("noise5", lambda x: A.gaussian_noise(x, 5))]:
        row["ber_" + label] = ber(wm_bits, extract_dct(fn(im), N, delta, repeat=REPEAT, key=KEY))
    trade.append(row)
results["tradeoff"] = trade
fig, ax1 = plt.subplots(figsize=(6.2, 3.8))
ds = [r["delta"] for r in trade]
ax1.plot(ds, [r["psnr"] for r in trade], "o-", color="#2c7fb8", label="PSNR (dB)")
ax1.set_xlabel("QIM step delta")
ax1.set_ylabel("PSNR (dB)", color="#2c7fb8")
ax2 = ax1.twinx()
ax2.grid(False)
ax2.plot(ds, [r["ber_jpeg50"] for r in trade], "s--", color="#c0392b", label="BER, JPEG Q50")
ax2.plot(ds, [r["ber_jpeg30"] for r in trade], "^--", color="#e67e22", label="BER, JPEG Q30")
ax2.plot(ds, [r["ber_noise5"] for r in trade], "d--", color="#7b3294", label="BER, noise s=5")
ax2.set_ylabel("Bit error rate")
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, fontsize=7, loc="center right")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig5_tradeoff.png"), dpi=150)
plt.close()

# repetition factor study at fixed delta
rep_rows = []
for r in [1, 2, 4]:
    im = embed_dct(cover, wm_bits, DELTA, repeat=r, key=KEY)
    rep_rows.append(dict(repeat=r, psnr=psnr(cover, im),
                         ber_jpeg50=ber(wm_bits, extract_dct(A.jpeg(im, 50), N, DELTA, repeat=r, key=KEY)),
                         ber_jpeg30=ber(wm_bits, extract_dct(A.jpeg(im, 30), N, DELTA, repeat=r, key=KEY)),
                         ber_crop25=ber(wm_bits, extract_dct(A.crop_fill(im, 0.25), N, DELTA, repeat=r, key=KEY))))
results["repetition"] = rep_rows

# ------------------------------------------------ Part 5: steganalysis
print("Part 5: chi-square steganalysis")
rng = np.random.default_rng(5)
steg_rows = []
for rate in [0.0, 0.1, 0.25, 0.5, 1.0]:
    n = int(cover.size * rate)
    if n == 0:
        im = cover
        p = chi_square_pov(cover, 0.1)       # same test window as the 10% case
    else:
        im = embed_lsb(cover, rng.integers(0, 2, n, dtype=np.uint8), 1)
        p = chi_square_pov(im, rate)
    steg_rows.append(dict(rate=rate, p_value=p, psnr=psnr(cover, im)))
p_dct = chi_square_pov(wm_img, 1.0)
p_clean_full = chi_square_pov(cover, 1.0)
results["steganalysis"] = dict(lsb=steg_rows, dct_watermark_p=p_dct, clean_full_p=p_clean_full)
fig, ax = plt.subplots(figsize=(5.6, 3.6))
ax.bar([f"{int(r['rate']*100)}%" for r in steg_rows], [r["p_value"] for r in steg_rows], color="#2c7fb8")
ax.set_xlabel("LSB embedding rate (fraction of pixels)")
ax.set_ylabel("Chi-square p-value")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig6_chisquare.png"), dpi=150)
plt.close()

# ------------------------------------------------ Part 6: colour image
print("Part 6: colour image (luminance watermark)")
rgb = load_color()
ycc = np.array(Image.fromarray(rgb).convert("YCbCr"))
y_wm = embed_dct(ycc[..., 0], wm_bits, DELTA, repeat=REPEAT, key=KEY)
ycc_wm = ycc.copy()
ycc_wm[..., 0] = y_wm
rgb_wm = np.array(Image.fromarray(ycc_wm, "YCbCr").convert("RGB"))
col_rows = []
for name, fn in [("No attack", lambda x: x), ("JPEG Q90", lambda x: A.jpeg(x, 90)),
                 ("JPEG Q70", lambda x: A.jpeg(x, 70)), ("JPEG Q50", lambda x: A.jpeg(x, 50)),
                 ("JPEG Q30", lambda x: A.jpeg(x, 30))]:
    att = fn(rgb_wm)
    y_att = np.array(Image.fromarray(att).convert("YCbCr"))[..., 0]
    e = extract_dct(y_att, N, DELTA, repeat=REPEAT, key=KEY)
    col_rows.append(dict(attack=name, ber=ber(wm_bits, e)))
results["color"] = dict(psnr=psnr(rgb, rgb_wm), ssim=ssim(rgb, rgb_wm), attacks=col_rows)
fig, axs = plt.subplots(1, 3, figsize=(9, 3.2))
show(axs[0], rgb, "Original (colour)", cmap=None)
show(axs[1], rgb_wm, f"Watermarked  {results['color']['psnr']:.1f} dB", cmap=None)
show(axs[2], np.clip(np.abs(rgb_wm.astype(int) - rgb.astype(int)) * 20, 0, 255).astype(np.uint8), "|difference| x20", cmap=None)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig7_color.png"), dpi=150)
plt.close()

# ------------------------------------------------------------- save
with open(os.path.join(OUT, "results.json"), "w") as f:
    json.dump(results, f, indent=2, default=float)

print("\nDone. Figures and results.json written to", OUT)
print(json.dumps(results["scheme_quality"], indent=1))
print(json.dumps(results["dct_default"], indent=1))
