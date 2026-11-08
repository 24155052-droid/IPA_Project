"""Spatial-domain steganography: least-significant-bit (LSB) embedding.

Written from scratch in NumPy. The payload is a flat 0/1 bit array that is
written into the k lowest bit planes of the cover pixels in raster order.
"""
import numpy as np


def text_to_bits(text):
    data = text.encode("utf-8")
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_text(bits):
    bits = np.asarray(bits, dtype=np.uint8)
    n = (len(bits) // 8) * 8
    data = np.packbits(bits[:n]).tobytes()
    return data.decode("utf-8", errors="replace")


def capacity_bits(cover, k=1):
    return cover.size * k


def _positions(total, n, key):
    """Pixel indices used for embedding: raster order, or a key-seeded random order."""
    if key is None:
        return np.arange(n)
    return np.random.default_rng(key).permutation(total)[:n]


def embed_lsb(cover, bits, k=1, key=None):
    """Embed `bits` into the k lowest bit planes of `cover` (uint8 array).

    With key=None pixels are used in raster order; otherwise in a pseudo-random
    order that only someone knowing the key can reproduce."""
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    if len(bits) > capacity_bits(cover, k):
        raise ValueError("payload larger than capacity")
    flat = cover.ravel().copy()
    # pad payload to a multiple of k
    pad = (-len(bits)) % k
    padded = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    groups = padded.reshape(-1, k)
    weights = 1 << np.arange(k - 1, -1, -1)
    values = (groups * weights).sum(axis=1).astype(np.uint8)
    n = len(values)
    mask = np.uint8(0xFF << k & 0xFF)
    idx = _positions(flat.size, n, key)
    flat[idx] = (flat[idx] & mask) | values
    return flat.reshape(cover.shape)


def extract_lsb(stego, n_bits, k=1, key=None):
    flat = stego.ravel()
    n_groups = -(-n_bits // k)
    idx = _positions(flat.size, n_groups, key)
    vals = flat[idx] & np.uint8((1 << k) - 1)
    shifts = np.arange(k - 1, -1, -1)
    bits = ((vals[:, None] >> shifts) & 1).astype(np.uint8).ravel()
    return bits[:n_bits]
