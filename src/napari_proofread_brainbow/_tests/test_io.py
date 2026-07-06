import csv

import numpy as np

from napari_proofread_brainbow._io import write_points_csv_preserve_types


def _read_csv_rows(path):
    with open(path, newline='') as f:
        return list(csv.reader(f))


def test_write_points_csv_preserves_integer_class_values(tmp_path):
    out = tmp_path / 'points.csv'
    data = np.array([[1.25, 2.5], [3.0, 4.125]], dtype=float)
    meta = {
        'properties': {
            'class': np.array([1, 2], dtype=np.int64),
            'probability': np.array([0.9, 0.7], dtype=float),
        }
    }

    path = write_points_csv_preserve_types(out, data, meta)

    assert path == str(out)
    rows = _read_csv_rows(out)
    assert rows[0] == ['index', 'axis-0', 'axis-1', 'class', 'probability']
    assert rows[1][3] == '1'
    assert rows[2][3] == '2'


def test_write_points_csv_coerces_integer_like_float_class_values(tmp_path):
    out = tmp_path / 'points.csv'
    data = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float)
    meta = {
        'properties': {
            'class': np.array([1.0, 2.0], dtype=float),
        }
    }

    write_points_csv_preserve_types(out, data, meta)
    rows = _read_csv_rows(out)
    assert rows[1][3] == '1'
    assert rows[2][3] == '2'
