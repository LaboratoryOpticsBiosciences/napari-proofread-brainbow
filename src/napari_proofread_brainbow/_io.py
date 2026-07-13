"""I/O helpers for napari-proofread-brainbow."""

from __future__ import annotations

import csv
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np


def _has_real_extension(path_obj: Path) -> bool:
    """Return True when the filename appears to include a real extension.

    Pathlib treats any trailing ``.<text>`` as a suffix, even when users type
    dataset names such as ``P2.4_sample`` that are not file extensions.
    """
    suffix = path_obj.suffix
    if suffix == '':
        return False

    ext = suffix[1:]
    return 1 <= len(ext) <= 6 and ext.isalnum()


def _coerce_integer_like(values: np.ndarray) -> np.ndarray:
    """Return int64 when all values are finite integers, otherwise unchanged."""
    if np.issubdtype(values.dtype, np.integer):
        return values.astype(np.int64, copy=False)

    if not np.issubdtype(values.dtype, np.floating):
        return values

    if values.size == 0:
        return values.astype(np.int64)

    if not np.all(np.isfinite(values)):
        return values

    rounded = np.rint(values)
    if np.allclose(values, rounded, atol=0.0):
        return rounded.astype(np.int64)
    return values


def write_points_csv_preserve_types(
    path: str | PathLike[str],
    data: Any,
    meta: dict,
) -> list[str]:
    """Write points CSV while preserving integer-like property columns.

    Napari's built-in points writer concatenates coordinates and properties into
    one NumPy table, which upcasts integer properties to float. This writer
    writes each column separately and preserves integer-like values for
    properties such as ``class``.
    """
    path_obj = Path(path)

    if path_obj.suffix.lower() == '.csv':
        pass
    elif not _has_real_extension(path_obj):
        path_obj = Path(f"{path_obj}.csv")
    else:
        return []  # Return empty list if it fails

    points = np.asarray(data)
    if points.ndim != 2:
        return []
    n_points, n_dims = points.shape
    columns: dict[str, np.ndarray] = {
        'index': np.arange(n_points, dtype=np.int64),
    }

    for axis in range(n_dims):
        columns[f'axis-{axis}'] = points[:, axis]

    properties = meta.get('properties', {}) if isinstance(meta, dict) else {}
    for key, values in properties.items():
        arr = np.asarray(values)
        if arr.ndim > 1:
            arr = np.ravel(arr)
        if arr.shape[0] != n_points:
            return []
        if str(key) == 'class':
            arr = _coerce_integer_like(arr)
        columns[str(key)] = arr

    header = list(columns.keys())
    with path_obj.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for idx in range(n_points):
            writer.writerow([columns[name][idx] for name in header])

    return [str(path_obj)]  # Return the list of written paths
