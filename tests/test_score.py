import numpy as np
import pytest
from napari.layers import Points

from napari_point_proofread._score_widget import (
    create_points_layer_from_pairs,
    greedy_matching,
)


@pytest.fixture
def viewer(make_napari_viewer_proxy):
    return make_napari_viewer_proxy()


@pytest.fixture
def annotation_layer(viewer):
    layer = Points(
        np.array([[0, 0], [1, 1], [11, 11], [111, 111]]), name='test_points'
    )
    viewer.add_layer(layer)
    return layer


@pytest.fixture
def prediction_layer(viewer):
    probabilities_features = np.array(
        [0.3, 0.3, 0.7, 0.9]
    )  # arbitrary probabilities
    layer = Points(
        np.array([[0, 0], [1, 1], [12, 11], [11, 12]]), name='test_points'
    )
    layer.features['probability'] = probabilities_features
    viewer.add_layer(layer)
    return layer


def test_greedy_matching(annotation_layer, prediction_layer):
    """Test that the greedy matching algorithm works correctly."""
    distance_threshold = 2
    tp, fp, fn, distance_pairs, ambiguous = greedy_matching(
        annotation_layer.data,
        prediction_layer.data,
        distance_threshold,
        prediction_layer.features['probability'].to_numpy(),
        return_ambiguous=True,
    )
    assert tp == 3
    assert fp == 1
    assert fn == 1
    assert len(distance_pairs) == 3
    assert len(ambiguous) == 2

    np.testing.assert_array_equal(
        ambiguous,
        [
            0,
            1,
        ],
    )  # indexes of the ambiguous pairs in the predictions
    # assert distance_pairs == [[0, 0, 0.0], [1, 1, 0.0], [3, 2, 1.0]]  # indexes of the matched pairs
    np.testing.assert_array_equal(
        distance_pairs,
        [[0, 0, 0.0], [1, 1, 0.0], [3, 2, 1.0]],
        err_msg='Distance pairs do not match',
    )


def test_create_points_layer_from_pairs(annotation_layer, prediction_layer):
    """Test that the points layer is created correctly from the matched pairs."""
    distance_threshold = 2
    tp, fp, fn, distance_pairs, ambiguous = greedy_matching(
        annotation_layer.data,
        prediction_layer.data,
        distance_threshold,
        prediction_layer.features['probability'].to_numpy(),
        return_ambiguous=True,
    )
    points_layer = create_points_layer_from_pairs(
        annotation_layer.data, prediction_layer.data, distance_pairs, ambiguous
    )

    assert isinstance(points_layer, Points)
    assert points_layer.name == 'Greedy matching'
    np.testing.assert_array_equal(
        points_layer.data, [[0, 0], [1, 1], [11, 12], [12, 11], [111, 111]]
    )  # matched pairs

    # check features
    print(points_layer.features)
    assert 'type' in points_layer.features

    # check that the features are correct
    np.testing.assert_array_equal(
        points_layer.features['type'], ['TP', 'TP', 'TP', 'FP', 'FN']
    )

    print(points_layer.features['distance'].to_numpy())
    # check that the distances are correct
    np.testing.assert_array_equal(
        points_layer.features['distance'].to_numpy(),
        [0.0, 0.0, 1.0, np.nan, np.nan],
        err_msg='Distances do not match',
    )

    # check that the ambiguous feature is correct
    np.testing.assert_array_equal(
        points_layer.features['ambiguous'], [True, True, False, False, False]
    )
