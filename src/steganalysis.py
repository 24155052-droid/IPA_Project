"""Chi-square steganalysis of LSB embedding (Westfeld and Pfitzmann, 2000).

In a natural image the counts of the two values in a "pair of values"
(2i, 2i+1) are usually different. LSB replacement with random data tends to
equalise them. The chi-square statistic measures how close the observed counts
are to the equalised ones; a high p-value therefore suggests hidden data.
"""
import numpy as np
from scipy.stats import chi2


def chi_square_pov(img, fraction=1.0):
    """Return the p-value of the pairs-of-values test on the first `fraction`
    of pixels in raster order (the region where LSB data is written)."""
    flat = img.ravel()
    n = int(len(flat) * fraction)
    hist = np.bincount(flat[:n], minlength=256).astype(np.float64)
    even = hist[0::2]
    odd = hist[1::2]
    expected = (even + odd) / 2.0
    keep = expected >= 5          # standard rule: ignore sparse classes
    stat = np.sum((even[keep] - expected[keep]) ** 2 / expected[keep])
    dof = int(keep.sum()) - 1
    if dof <= 0:
        return 0.0
    return float(1.0 - chi2.cdf(stat, dof))
