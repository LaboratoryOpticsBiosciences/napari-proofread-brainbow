
import numpy as np
from napari.layers import Points
from napari.viewer import Viewer
from magicgui import magic_factory
from magicgui.widgets import Container
from napari.viewer import Viewer
from qtpy.QtWidgets import QMessageBox
from scipy.spatial import cKDTree

from ._utils import setup_layout, _make_titled_panel


def _get_feature(layer: Points, name: str, default=None) -> np.ndarray:
    """Return a point feature as a NumPy array."""
    features = layer.features

    if name in features:
        return np.asarray(features[name])

    if default is None:
        return np.arange(len(layer.data))

    return np.full(len(layer.data), default)


def _filter_by_distance(
    coordinates: np.ndarray,
    probabilities: np.ndarray,
    min_distance: float,
) -> np.ndarray:
    """Greedy non-maximum suppression, prioritizing higher probabilities."""
    n_points = len(coordinates)

    if min_distance <= 0 or n_points < 2:
        return np.ones(n_points, dtype=bool)

    tree = cKDTree(coordinates)
    order = np.argsort(-probabilities, kind="stable")
    keep = np.zeros(n_points, dtype=bool)
    suppressed = np.zeros(n_points, dtype=bool)

    for index in order:
        if suppressed[index]:
            continue

        keep[index] = True

        neighbors = tree.query_ball_point(
            coordinates[index],
            r=min_distance,
        )

        for neighbor in neighbors:
            if neighbor != index:
                # Keep points exactly at the minimum distance.
                distance = np.linalg.norm(
                    coordinates[neighbor] - coordinates[index]
                )
                if distance < min_distance:
                    suppressed[neighbor] = True

    return keep


@magic_factory(
    probability_threshold={
        "widget_type": "FloatSlider",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "value": 0.5,
    },
    distance_threshold={
        "widget_type": "FloatSlider",
        "min": 0.0,
        "max": 100.0,
        "step": 1.0,
        "value": 10.0,
    },
    auto_call=False,
    call_button="Threshold probability (CSV)",
)
def post_process_filters(
    viewer: Viewer,
    point_layer: Points,
    probability_threshold: float = 0.5,
    distance_threshold: float = 10.0,
) -> Points | None:
    """Filter points by probability and minimum spatial separation.

    Points without probability metadata are assigned probability 1.0
    because they are assumed to be manually proofread. Points without class
    metadata are treated as unclassified. The filtered points are returned
    as a new points layer, which is added to the viewer. If a thresholded
    layer already exists, it is updated in placepost_process_filters. The new layer preserves the
    source IDs and optional class annotations of the original points. The
    thresholded layer is named "{original_layer_name}_thresholded". If no points
    remain after filtering, a warning is displayed and no layer is created.

    The distance threshold is measured in world coordinates.
    Higher-probability points are prioritized when points are too close.
    """
    if point_layer is None:
        return None

    coordinates = np.asarray(point_layer.data)

    if len(coordinates) == 0:
        QMessageBox.warning(
            None,
            "No points",
            "The selected points layer is empty.",
        )
        return None

    probabilities = _get_feature(
        point_layer, "probability", default=1.0
    ).astype(float)

    if not np.all(np.isfinite(probabilities)):
        raise ValueError("Point probabilities must be finite.")

    # Convert coordinates to world space using the public layer API.
    world_coordinates = np.asarray(
        [point_layer.data_to_world(point) for point in coordinates]
    )

    probability_mask = probabilities >= probability_threshold

    distance_mask = _filter_by_distance(
        world_coordinates,
        probabilities,
        distance_threshold,
    )

    keep = probability_mask & distance_mask

    if not np.any(keep):
        QMessageBox.warning(
            None,
            "No points remaining",
            "No points remain after filtering by probability and distance.",
        )
        return None

    features = point_layer.features.iloc[np.flatnonzero(keep)].copy()

    name = f"{point_layer.name}_thresholded"

    # Update an existing thresholded layer if available.
    existing = next(
        (layer for layer in viewer.layers if layer.name == name),
        None,
    )

    if existing is not None:
        if not isinstance(existing, Points):
            raise TypeError(
                f"A non-Points layer already uses the name {name!r}."
            )

        existing.data = coordinates[keep].copy()
        existing.features = features
        return existing

    # Create and register the thresholded layer.
    points = Points(
        data=coordinates[keep].copy(),
        name=name,
        border_color="red",
        features=features,
        scale=point_layer.scale,
        translate=point_layer.translate,
        rotate=point_layer.rotate,
        shear=point_layer.shear,
        affine=point_layer.affine,
        axis_labels=point_layer.axis_labels,
        units=point_layer.units,
        size=point_layer.size[keep],
    )

    viewer.add_layer(points)
    return points


class PostProcessWidget(Container):
    """Compact panel for proofreading prediction CSV points."""

    def __init__(self, layout="vertical"):
        prediction_widget = post_process_filters()

        prediction_widget.label = ""
        prediction_widget.point_layer.label = "Point layer"
        prediction_widget.probability_threshold.label = "Min probability"
        prediction_widget.distance_threshold.label = "Min distance"

        prediction_widget.call_button.tooltip = (
            "Filter points by minimum probability and spatial separation, "
            "then create or update the thresholded points layer."
        )

        setup_layout(prediction_widget)

        prediction_tools = _make_titled_panel(
            "Prediction Tools",
            [prediction_widget],
        )

        super().__init__(
            layout=layout,
            widgets=[prediction_tools],
            labels=False,
        )
