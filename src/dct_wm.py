"""Transform-domain blind watermarking in the 8x8 block DCT.

One watermark bit is hidden in every 8x8 block by quantization index
modulation (QIM) of one mid-frequency DCT coefficient:

    bit 0 -> coefficient moved to the nearest even multiple of delta
    bit 1 -> coefficient moved to the nearest odd  multiple of delta

Extraction is blind (the original image is not needed). To survive attacks,
each bit can be repeated r times in different blocks and decided by majority
vote (a simple repetition code).
"""
import numpy as np
from scipy.fft import dctn, idctn

BLOCK = 8
# coefficient position (row, col) inside the 8x8 DCT block: a mid-frequency one
DEFAULT_POS = (3, 2)


def _to_blocks(img):
    h, w = img.shape
    return (img.reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK)
               .swapaxes(1, 2).reshape(-1, BLOCK, BLOCK))


def _from_blocks(blocks, shape):
    h, w = shape
    return (blocks.reshape(h // BLOCK, w // BLOCK, BLOCK, BLOCK)
                  .swapaxes(1, 2).reshape(h, w))


def n_blocks(shape):
    return (shape[0] // BLOCK) * (shape[1] // BLOCK)


def _block_order(nb, n, key):
    if key is None:
        return np.arange(n)
    return np.random.default_rng(key).permutation(nb)[:n]


def embed_dct(cover, bits, delta=24.0, pos=DEFAULT_POS, repeat=1, key=None):
    """Embed bits into a gray uint8 image. Returns the watermarked uint8 image.

    key=None uses blocks in raster order; otherwise a key-seeded random block
    order spreads the (repeated) bits over the whole image."""
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    nb = n_blocks(cover.shape)
    if len(bits) * repeat > nb:
        raise ValueError("not enough blocks for payload x repeat")
    coded = np.repeat(bits, repeat)
    blocks = _to_blocks(cover.astype(np.float64) - 128.0)
    coef = dctn(blocks, axes=(1, 2), norm="ortho")
    order = _block_order(nb, len(coded), key)
    c = coef[order, pos[0], pos[1]]
    q = np.round(c / delta)
    # force parity of the quantization index to equal the bit
    wrong = (q.astype(np.int64) % 2) != coded
    # move to nearest index with the right parity
    q = np.where(wrong, q + np.where(c / delta >= q, 1, -1), q)
    coef[order, pos[0], pos[1]] = q * delta
    out = idctn(coef, axes=(1, 2), norm="ortho")
    out = _from_blocks(out, cover.shape) + 128.0
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def extract_dct(img, n_bits, delta=24.0, pos=DEFAULT_POS, repeat=1, key=None):
    blocks = _to_blocks(img.astype(np.float64) - 128.0)
    coef = dctn(blocks, axes=(1, 2), norm="ortho")
    total = n_bits * repeat
    order = _block_order(len(coef), total, key)
    c = coef[order, pos[0], pos[1]]
    q = np.round(c / delta).astype(np.int64) % 2
    votes = q.reshape(n_bits, repeat).sum(axis=1)
    return (votes * 2 > repeat).astype(np.uint8)
