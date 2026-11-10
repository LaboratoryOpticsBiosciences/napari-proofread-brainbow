import numpy as np
import pytest

from napari_point_proofread._proofread_widget import ProofreadWidget


@pytest.fixture
def viewer(make_napari_viewer_proxy):
    return make_napari_viewer_proxy()


def test_class_annotation(viewer):
    """Test that the class annotation functionality works as expected."""
    # Add a points layer
    points_layer = viewer.add_points(np.array([[0, 0], [1, 1], [2, 2]]))
    widget = ProofreadWidget()
    viewer.window.add_dock_widget(widget)
    # Select a class
    widget.point_class_widget._on_toggle(True)
    # Check that the points have the correct class 0 by default
    assert points_layer.features['class'].tolist() == [0, 0, 0]

    # select second points and assign class 1
    points_layer.selected_data = [1]  # select the second point
    widget.point_class_widget._class_spin.value = 1
    widget.point_class_widget._on_assign(True)
    assert points_layer.features['class'].tolist() == [0, 1, 0]
