import numpy as np
import pytest
from napari.layers import Points

from napari_point_proofread._postprocess_widget import (
    post_process_filters,
)


@pytest.fixture
def viewer(make_napari_viewer_proxy):
    return make_napari_viewer_proxy()


@pytest.fixture
def points_layer(viewer):
    # World coordinates with scale [2, 3]: (0, 0) and (4, 3) -> distance 5
    probabilities_features = np.array([0.3, 0.7])  # arbitrary probabilities
    layer = Points(np.array([[0, 0], [1, 1]]), name="test_points")
    layer.features["probability"] = probabilities_features
    viewer.add_layer(layer)
    return layer


@pytest.fixture
def filter_widget(viewer, points_layer):
    widget = post_process_filters()
    viewer.window.add_dock_widget(widget)  # lets magicgui inject `viewer`
    widget.point_layer.value = points_layer
    widget.probability_threshold.value = 0.0  # no filtering by probability
    widget.distance_threshold.value = 2.5  # in world coordinates
    return widget


def test_filter_by_distance_use_transform(filter_widget, points_layer):
    """Test that the distance threshold is applied in world coordinates."""
    # Identity scale: world distance ~2.24 < 2.5, so one point is removed
    filtered_layer = filter_widget()
    assert filtered_layer is not None
    assert len(filtered_layer.data) == 1

    # Scaled: world distance 5 > 2.5, so both points are kept
    points_layer.scale = np.array([2, 3])
    filtered_layer = filter_widget()
    assert filtered_layer is not None
    assert len(filtered_layer.data) == 2

    # points_layer.scale = np.array([1, 1])


def test_filter_by_distance_keep_higher_probability(filter_widget, points_layer):
    """Test that the higher-probability point is kept when points are too close."""
    # Add probability metadata to the points layer
    filter_widget.probability_threshold.value = 0.0  # no filtering by probability
    filtered_layer = filter_widget()
    assert filtered_layer is not None
    assert len(filtered_layer.data) == 1
    # The remaining point should be the one with higher probability (index 1)
    assert np.array_equal(filtered_layer.data[0], points_layer.data[1])

def test_filter_by_probability(filter_widget, points_layer):
    """Test that points below the probability threshold are filtered out."""
    filter_widget.probability_threshold.value = 0.5  # filter out points < 0.5

    filtered_layer = filter_widget()
    assert filtered_layer is not None
    assert len(filtered_layer.data) == 1
    # The remaining point should be the one with higher probability (index 1)
    assert np.array_equal(filtered_layer.data[0], points_layer.data[1])

def test_filter_keeps_features(filter_widget, points_layer):
    """Test that the filtered layer preserves source IDs and class annotations."""
    # Add source ID and class metadata to the points layer
    points_layer.features["source_id"] = np.array([101, 102])
    points_layer.features["class"] = np.array(["A", "B"])

    filter_widget.probability_threshold.value = 0.5  # filter out points < 0.5
    filtered_layer = filter_widget()
    assert filtered_layer is not None
    assert len(filtered_layer.data) == 1

    # Check that the remaining point has the correct source ID and class
    assert filtered_layer.features["source_id"][0] == 102
    assert filtered_layer.features["class"][0] == "B"