import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lsb import embed_lsb, extract_lsb, text_to_bits, bits_to_text, capacity_bits
from dct_wm import embed_dct, extract_dct, n_blocks
from metrics import psnr, ber, mse, normalized_correlation
from attacks import jpeg, gaussian_noise, crop_fill
from steganalysis import chi_square_pov

RNG = np.random.default_rng(1)
COVER = RNG.integers(0, 256, (64, 64), dtype=np.uint8)


def test_text_bits_roundtrip():
    msg = "Sayangsu Dawn - 24155052"
    assert bits_to_text(text_to_bits(msg)) == msg


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_lsb_roundtrip_exact(k):
    bits = RNG.integers(0, 2, 1000, dtype=np.uint8)
    stego = embed_lsb(COVER, bits, k)
    assert np.array_equal(extract_lsb(stego, len(bits), k), bits)


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_lsb_pixel_change_bounded(k):
    bits = RNG.integers(0, 2, capacity_bits(COVER, k), dtype=np.uint8)
    stego = embed_lsb(COVER, bits, k)
    diff = np.abs(stego.astype(int) - COVER.astype(int))
    assert diff.max() <= (1 << k) - 1


def test_lsb_capacity_error():
    with pytest.raises(ValueError):
        embed_lsb(COVER, np.zeros(COVER.size + 1, dtype=np.uint8), 1)


def test_dct_embed_extract_lossless():
    bits = RNG.integers(0, 2, 40, dtype=np.uint8)
    wm = embed_dct(COVER, bits, delta=24)
    assert np.array_equal(extract_dct(wm, len(bits), delta=24), bits)


def test_dct_repetition_roundtrip():
    bits = RNG.integers(0, 2, 10, dtype=np.uint8)
    wm = embed_dct(COVER, bits, delta=24, repeat=5)
    assert np.array_equal(extract_dct(wm, 10, delta=24, repeat=5), bits)


def test_dct_too_many_bits():
    with pytest.raises(ValueError):
        embed_dct(COVER, np.zeros(n_blocks(COVER.shape) + 1, dtype=np.uint8))


def test_dct_survives_jpeg_better_than_lsb():
    img = (np.add.outer(np.arange(128), np.arange(128)) % 256).astype(np.uint8)
    img = np.clip(img.astype(int) + RNG.integers(-10, 10, img.shape), 0, 255).astype(np.uint8)
    bits = RNG.integers(0, 2, 80, dtype=np.uint8)
    lsb_ext = extract_lsb(jpeg(embed_lsb(img, bits, 1), 70), len(bits), 1)
    dct_ext = extract_dct(jpeg(embed_dct(img, bits, delta=30, repeat=3), 70), len(bits), delta=30, repeat=3)
    assert ber(bits, dct_ext) < ber(bits, lsb_ext)


def test_metrics():
    assert psnr(COVER, COVER) == float("inf")
    assert mse(COVER, COVER) == 0
    assert ber([0, 1, 1, 0], [0, 1, 0, 0]) == 0.25
    assert normalized_correlation([0, 1, 1], [0, 1, 1]) == pytest.approx(1.0)


def test_attacks_keep_shape_and_dtype():
    for out in (jpeg(COVER, 50), gaussian_noise(COVER, 5), crop_fill(COVER, 0.25)):
        assert out.shape == COVER.shape and out.dtype == np.uint8


def test_chi_square_detects_full_lsb_embedding():
    x = np.clip(RNG.normal(128, 40, (256, 256)), 0, 255).astype(np.uint8)
    clean_p = chi_square_pov(x)
    bits = RNG.integers(0, 2, x.size, dtype=np.uint8)
    stego_p = chi_square_pov(embed_lsb(x, bits, 1))
    assert stego_p > clean_p


def test_keyed_embedding_needs_right_key():
    bits = RNG.integers(0, 2, 200, dtype=np.uint8)
    stego = embed_lsb(COVER, bits, 1, key=7)
    assert np.array_equal(extract_lsb(stego, 200, 1, key=7), bits)
    assert ber(bits, extract_lsb(stego, 200, 1, key=8)) > 0.3
    wm = embed_dct(COVER, bits[:30], delta=24, repeat=2, key=7)
    assert np.array_equal(extract_dct(wm, 30, delta=24, repeat=2, key=7), bits[:30])
