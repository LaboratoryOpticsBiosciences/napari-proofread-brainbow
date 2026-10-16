"""I/O helpers for napari-proofread-brainbow."""

from __future__ import annotations

import csv
from os import PathLike
import os
from pathlib import Path
from typing import Any
from napari_builtins.io import write_csv
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
        path: str,
        data: Any,
        meta: dict
    ) -> list[str]:
    """Write points CSV while preserving integer-like property columns.

    Napari's built-in points writer concatenates coordinates and properties into
    one NumPy table, which upcasts integer properties to float. This writer
    writes each column separately and preserves integer-like values.
    """
    path_obj = Path(path)

    if path_obj.suffix.lower() == '.csv':
        pass
    elif not _has_real_extension(path_obj):
        path_obj = Path(f"{path_obj}.csv")
    else:
        return []  # Return empty list if it fails

    properties = meta.get('properties', {})

    # Construct columns without merging their dtypes
    column_names = ['index']
    columns = [
        np.arange(data.shape[0], dtype=int)
    ]

    # Coordinate columns
    for n in range(data.shape[1]):
        column_names.append(f'axis-{n!s}')
        columns.append(data[:, n])

    # Feature columns
    for name, values in properties.items():
        column_names.append(name)
        columns.append(values)

    # Build rows while preserving individual column values
    table = zip(*columns)

    write_csv(path_obj, table, column_names)

    return [str(path_obj)]
