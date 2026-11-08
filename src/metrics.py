"""Quality and extraction metrics used throughout the project."""
import numpy as np
from skimage.metrics import structural_similarity


def mse(a, b):
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    return float(np.mean((a - b) ** 2))


def psnr(a, b):
    m = mse(a, b)
    if m == 0:
        return float("inf")
    return 10.0 * np.log10(255.0 ** 2 / m)


def ssim(a, b):
    """SSIM for gray (H,W) or colour (H,W,3) uint8 images."""
    if a.ndim == 3:
        return float(structural_similarity(a, b, channel_axis=2, data_range=255))
    return float(structural_similarity(a, b, data_range=255))


def ber(bits_a, bits_b):
    """Bit error rate between two equal-length 0/1 arrays."""
    bits_a = np.asarray(bits_a).ravel()
    bits_b = np.asarray(bits_b).ravel()
    return float(np.mean(bits_a != bits_b))


def normalized_correlation(w, w_ext):
    """NC between two binary watermarks (mapped to +/-1)."""
    a = np.asarray(w, dtype=np.float64).ravel() * 2 - 1
    b = np.asarray(w_ext, dtype=np.float64).ravel() * 2 - 1
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def entropy(img):
    hist = np.bincount(img.ravel(), minlength=256).astype(np.float64)
    p = hist / hist.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())
