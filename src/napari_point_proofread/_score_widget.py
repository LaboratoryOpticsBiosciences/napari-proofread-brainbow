
from magicgui import magic_factory
from magicgui.widgets import Container, Label
from napari import Viewer
from napari.layers import Points
import numpy as np
from scipy.spatial import distance_matrix
from typing import Tuple, List

from qtpy.QtWidgets import QMessageBox

def compute_f1(tp:int,
               fp:int,
               fn:int,
               am:int=0
    ) -> float:
    """Compute the F1 score.

    Parameters
    ----------
    tp : int
        The number of true positives.
    fp : int
        The number of false positives.
    fn : int
        The number of false negatives.
    amint : int, optional
        The number of ambiguous pairs, by default 0

    Returns
    -------
    float
        The F1 score.
    """

    # Avoid division by zero
    if tp == 0 and fp == 0 and fn == 0:
        return 0.0

    f1_score = (tp) / (tp + 0.5 * (fn + fp + am))

    return f1_score

def create_points_layer_from_pairs(
    annotations: np.ndarray,
    detections: np.ndarray,
    pairs: List[Tuple[int, int, float]],
) -> Points:
    pairs = [(int(p[0]), int(p[1]), float(p[2])) for p in pairs]

    matched_det_idx = {p[0] for p in pairs}
    matched_ann_idx = {p[1] for p in pairs}

    coords = []
    types = []
    distances = []
    colors = []

    # Matched (use detection coordinates)
    for det_idx, _, dist in pairs:
        coords.append(detections[det_idx])
        types.append("matched")
        distances.append(dist)
        colors.append("green")

    # False positives
    for i in range(len(detections)):
        if i not in matched_det_idx:
            coords.append(detections[i])
            types.append("false_positive")
            distances.append(np.nan)
            colors.append("red")

    # False negatives
    for i in range(len(annotations)):
        if i not in matched_ann_idx:
            coords.append(annotations[i])
            types.append("false_negative")
            distances.append(np.nan)
            colors.append("blue")

    return Points(
        np.array(coords),
        name="Greedy matching",
        ndim=annotations.shape[1],
        properties={"type": types, "distance": distances},
        face_color=colors,
        size=5,
    )


def greedy_matching(annotations: np.ndarray,
                    detections: np.ndarray,
                    threshold: float,
                    return_ambiguous: bool = False
                    ) -> Tuple[int, int, int, List[Tuple[int, int, float]]]:
    """Apply greedy matching to the annotations and detections.
    Note there is no False negative detection.

    Parameters
    ----------
    annotations : array_like
        (n*d) with n the number of annotations and d the dimensionality of the
        annotations
    detections : array_like
        (m*d) with m the number of detections and d the dimensionality of the
        detections
    threshold : float
        The maximum distance between an annotation and a detection for them to
        be considered a possible match.
    return_ambiguous : bool
        Whether to return the number of ambiguous matches.

    Returns
    -------
    n_true_positives : int
        The number of true positives.
    n_false_positives : int
        The number of false positives.
    n_false_negatives : int
        The number of false negatives.
    distance_pairs : list of tuples
        The list of distance pairs. Each tuple contains the indices of the
        detection and the annotation, and the distance between them.
    n_ambiguous : int
        The number of ambiguous matches. An ambiguous match is a detection
        that is matched to more than one annotation. This is only returned if
        return_ambiguous is True.
    ambiguous : list of int
        The indices of the ambiguous matches in detections.
        This is only returned if return_ambiguous is True.
    """

    distance_matrix_ = distance_matrix(annotations, detections).T

    distance_matrix_copy = distance_matrix_.copy()
    pairs = []

    while True:
        min_idx = np.unravel_index(np.argmin(distance_matrix_copy), distance_matrix_copy.shape)

        if distance_matrix_copy[min_idx] > threshold: # No more matches
            break

        pairs.append((int(min_idx[0]), int(min_idx[1]), distance_matrix_copy[min_idx]))

        # Set distances to infinity for the selected row and column
        distance_matrix_copy[min_idx[0], :] = np.inf
        distance_matrix_copy[:, min_idx[1]] = np.inf

    pairs = np.array(pairs)
    true_positives = len(pairs)
    false_positives = int(distance_matrix_.shape[0] - len(pairs))
    false_negatives = int(distance_matrix_.shape[1] - len(pairs))

    if return_ambiguous:
        ambiguous = []

        if true_positives != 0:
            for i in range(distance_matrix_.shape[0]):
                if i not in pairs[:,0]:
                    continue

                matches = np.sum(distance_matrix_[i,:] < threshold)

                if matches > 1:
                    ambiguous.append(i)

        return true_positives, false_positives, false_negatives, pairs, len(ambiguous), ambiguous

    return true_positives, false_positives, false_negatives, pairs

def compute_score() -> Container:
    """Build the score widget with a visible F1 result label."""
    score_label = Label(value="F1 score: -")
    score_label.label = ""

    @magic_factory(
        greedy_threshold={
            "widget_type": "FloatSlider",
            "min": 0.0,
            "max": 100.0,
            "step": 1.0,
            "value": 10.0,
        },
        auto_call=False,
        call_button="Show greedy matching",
    )
    def _compute_score(
        viewer: Viewer,
        annotation_layer: Points,
        detection_layer: Points,
        greedy_threshold: float = 10.0,
        return_ambiguous: bool = False
    ) -> Points | None:
        """
        Compute the (F1) score between the annotation and detection layers using greedy matching.

        The distance threshold is measured in world coordinates, so it is important to set the scale of the layers correctly.
        Higher-probability points are prioritized in the matching process.
        The function returns a new Points layer containing the matched pairs in green, the false positives in red, and the false negatives in blue.
        """
        if annotation_layer is None or detection_layer is None:
            score_label.value = "F1 score: -"
            return None

        coordinates_annotations = annotation_layer.data
        coordinates_detections = detection_layer.data

        if len(coordinates_annotations) == 0 or len(coordinates_detections) == 0:
            score_label.value = "F1 score: -"
            QMessageBox.warning(
                None,
                "Empty layer",
                "One of the layers is empty. Please provide non-empty annotation and detection layers.",
            )
            return None
        
        result = greedy_matching(
            annotations=coordinates_annotations,
            detections=coordinates_detections,
            threshold=greedy_threshold,
            return_ambiguous=return_ambiguous,
        )


        if return_ambiguous:
            tp, fp, fn, pairs, n_ambiguous, ambiguous = result
        else:
            tp, fp, fn, pairs = result
            n_ambiguous, ambiguous = 0, []

        score = compute_f1(tp, fp, fn, n_ambiguous)
        score_label.value = f"F1 score: {score:.3f}, TP: {tp}, FP: {fp}, FN: {fn}, Ambiguous: {n_ambiguous}"

        name = f"Greedy matching"

        existing = next(
            (layer for layer in viewer.layers if layer.name == name),
            None,
        )

        if existing is not None:
            viewer.layers.remove(existing)

        points = create_points_layer_from_pairs(
            annotations=coordinates_annotations,
            detections=coordinates_detections,
            pairs=pairs,
        )

        points.name = name
        viewer.add_layer(points)
        return points

    score_widget = _compute_score()
    return Container(
        widgets=[score_widget, score_label],
        labels=False,
    )