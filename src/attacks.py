"""Attacks applied to a watermarked / stego image to test robustness."""
import io
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, median_filter


def jpeg(img, quality):
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=int(quality))
    buf.seek(0)
    return np.array(Image.open(buf))


def gaussian_noise(img, sigma, seed=0):
    rng = np.random.default_rng(seed)
    out = img.astype(np.float64) + rng.normal(0, sigma, img.shape)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def salt_pepper(img, density, seed=0):
    rng = np.random.default_rng(seed)
    out = img.copy()
    r = rng.random(img.shape)
    out[r < density / 2] = 0
    out[r > 1 - density / 2] = 255
    return out


def blur(img, sigma):
    return np.clip(np.round(gaussian_filter(img.astype(np.float64), sigma)), 0, 255).astype(np.uint8)


def median(img, size=3):
    return median_filter(img, size=size)


def crop_fill(img, fraction):
    """Replace the bottom `fraction` of rows with zeros (cropping attack)."""
    out = img.copy()
    rows = int(round(img.shape[0] * fraction))
    if rows > 0:
        out[-rows:, :] = 0
    return out


def scale_roundtrip(img, factor):
    """Downscale then upscale back to the original size."""
    h, w = img.shape
    small = Image.fromarray(img).resize((int(w * factor), int(h * factor)), Image.BILINEAR)
    return np.array(small.resize((w, h), Image.BILINEAR))


def brightness(img, offset):
    return np.clip(img.astype(np.int16) + offset, 0, 255).astype(np.uint8)
