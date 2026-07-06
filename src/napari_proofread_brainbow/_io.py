"""I/O helpers for napari-proofread-brainbow."""

from __future__ import annotations

import csv
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np


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
) -> str | None:
    """Write points CSV while preserving integer-like property columns.

    Napari's built-in points writer concatenates coordinates and properties into
    one NumPy table, which upcasts integer properties to float. This writer
    writes each column separately and preserves integer-like values for
    properties such as ``class``.
    """
    path_obj = Path(path)
    if path_obj.suffix == '':
        path_obj = path_obj.with_suffix('.csv')
    elif path_obj.suffix.lower() != '.csv':
        return None

    points = np.asarray(data)
    if points.ndim != 2:
        return None

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
            return None
        if str(key) == 'class':
            arr = _coerce_integer_like(arr)
        columns[str(key)] = arr

    header = list(columns.keys())
    with path_obj.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for idx in range(n_points):
            writer.writerow([columns[name][idx] for name in header])

    return str(path_obj)
