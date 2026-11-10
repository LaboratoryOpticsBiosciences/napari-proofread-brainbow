import contextlib
from itertools import tee

import napari
import numpy as np
from magicgui import magic_factory, magicgui
from magicgui.widgets import (
    CheckBox,
    Container,
    Label,
    PushButton,
    SpinBox,
)
from napari import layers as L
from napari import types

from ._widget_utils import _make_titled_panel, setup_layout


@magicgui(
    point_size={
        'label': 'Point size',
        'tooltip': 'Change size of all points at once',
        'widget_type': 'Slider',
        'value': 10,
        'max': 15,
    },
    auto_call=True,
    call_button=False,
)
def widget_points(
    point_layer: L.Points,
    point_size,
):
    """Set the displayed size for the selected points layer.

    Parameters
    ----------
    point_layer : napari.layers.Points or None
        Target points layer whose marker size will be changed.
    point_size : float
        New marker size to use for the layer.

    Returns
    -------
    None
        The points layer is updated in place.
    """
    if point_layer is None:
        return
    # print(f"you have selected {point_layer}")
    # Seems to interact with scales and distance from camera
    point_layer.size = point_size


@magic_factory(
    img_layer={'label': 'Image shape for grid'},
    bins={
        'label': 'bins (x, y)',
        'widget_type': 'TupleEdit',
        'value': (5, 5),
        'options': {'min': 2, 'max': 10, 'step': 1},
        'tooltip': 'Number of bins in x and y direction',
    },
    call_button='make grid',
)
def widget_grid(
    img_layer: 'napari.layers.Image',
    bins: tuple[int, int],
) -> types.LayerDataTuple:
    """Create a line grid overlay for the selected image layer.

    Parameters
    ----------
    img_layer : napari.layers.Image or None
        Image layer used to determine the grid extent.
    xbins : int
        Number of bins to draw in the x direction.
    ybins : int
        Number of bins to draw in the y direction.

    Returns
    -------
    LayerDataTuple or None
        Shapes layer data for the grid overlay, or ``None`` if no image exists.
    """

    xbins, ybins = bins

    def pairwise(x):
        """Yield adjacent pairs from an iterable.

        Parameters
        ----------
        x : iterable
            Input sequence to traverse in pairs.

        Returns
        -------
        iterator
            Iterator of consecutive 2-tuples.
        """
        a, b = tee(x)
        next(b, None)
        return zip(a, b, strict=False)

    if img_layer is None:
        return

    shape = img_layer.data.shape
    width = shape[-2] if shape[-1] == 3 else shape[-1]
    height = shape[-3] if shape[-1] == 3 else shape[-2]
    bins_x = np.linspace(0, width, xbins + 1, endpoint=True)
    bins_y = np.linspace(0, height, ybins + 1, endpoint=True)
    data = []
    # vertical
    for x in bins_x:
        # coord [[y0, x0], [y1, x1]]
        data.append(np.array([[0, x], [height, x]]))
    # horizontal
    for y in bins_y:
        data.append(np.array([[y, 0], [y, width]]))
    # dummies for text
    # a pair of `features` and `text` argument can be used to put text on shape
    # object. but it does not support defining a translation for each obeject.
    XLABELS = 'ABCDEFGHIJ'
    yoffset = -height * 0.05
    xoffset = -width * 0.05
    for x0, x1 in pairwise(bins_x):
        data.append(np.array([[yoffset, x0], [yoffset, x1]]))
    for y0, y1 in pairwise(bins_y):
        data.append(np.array([[y0, xoffset], [y1, xoffset]]))

    text = {
        'string': '{number}',
        # 'anchor': ''
        # 'translation': [0, 0],
        'size': 16,
        'color': 'lime',
    }
    features = {
        'number': (
            ['' for _ in range(xbins + ybins + 2)]  # empty for grid
            + [XLABELS[i] for i in range(xbins)]  # ABCD...
            + list(range(ybins))  # 123..
        )
    }
    kwargs = {
        'name': f'grid({img_layer.name})',
        'shape_type': 'line',
        # edge_width=thickness,
        'features': features,
        'text': text,
    }
    return (data, kwargs, 'shapes')


# ---------------------------------------------------------------------------
# Class annotation: constants
# ---------------------------------------------------------------------------

_N_CLASSES = 10
_CLASS_COLORS_HEX = [
    '#E6194B',  # 0 – red
    '#3CB44B',  # 1 – green
    '#4363D8',  # 2 – blue
    '#F58231',  # 3 – orange
    '#911EB4',  # 4 – purple
    '#42D4F4',  # 5 – cyan
    '#F032E6',  # 6 – magenta
    '#BFEF45',  # 7 – lime
    '#FABED4',  # 8 – pink
    '#469990',  # 9 – teal
]


def _hex_to_rgba(hex_color: str):
    """Convert a six-digit hex color string to an RGBA list.

    Parameters
    ----------
    hex_color : str
        Color string such as ``'#RRGGBB'``.

    Returns
    -------
    list of float
        RGBA values normalized to the range [0, 1].
    """
    h = hex_color.lstrip('#')
    return [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


_CLASS_COLORS_RGBA = [_hex_to_rgba(c) for c in _CLASS_COLORS_HEX]
_UNASSIGNED_RGBA = [0.7, 0.7, 0.7, 0.7]  # grey for points without a class


# ---------------------------------------------------------------------------
# PointClassWidget
# ---------------------------------------------------------------------------


class PointClassWidget(Container):
    """Optional widget for per-point numerical class annotation.

    When enabled:
      * Every point added to the active layer is automatically tagged with
        the currently selected class.
      * Selected points can be re-tagged via 'Assign class to selected'.
      * Points are colored per-class and display their class number.
      * The 'class' column is included when the layer is saved as CSV.
    """

    def __init__(self, point_layer_widget):
        """Create the class-annotation controls bound to a points-layer selector.

        Parameters
        ----------
        point_layer_widget : magicgui.widgets.Widget
            Widget that selects the active points layer.

        Returns
        -------
        None
            The widget is initialized in place.
        """
        self._point_layer_widget = point_layer_widget
        self._layer = None
        self._event_conn = None
        self._refreshing = False

        self._enable_cb = CheckBox(value=False, text='Enable class annotation')
        self._enable_cb.label = ''
        self._enable_cb.tooltip = (
            'Enable or disable class annotation for the active points layer.'
        )

        self._class_spin = SpinBox(value=0, min=0, max=_N_CLASSES - 1)
        self._class_spin.label = ''
        self._class_spin.enabled = False
        self._class_spin.tooltip = 'Select the class for new points.'

        self._class_label = Label(value='Current class')
        self._class_label.label = ''

        self._color_text_label = Label(value='Class color')
        self._color_text_label.label = ''

        self._color_label = Label(value='')
        self._color_label.label = ''
        self._color_label.native.setFixedSize(18, 18)
        self._update_color_label(0)

        self._class_row = Container(
            layout='horizontal',
            widgets=[
                self._class_label,
                self._class_spin,
                self._color_text_label,
                self._color_label,
            ],
            labels=False,
        )
        setup_layout(self._class_row)

        self._assign_btn = PushButton(text='Assign class to selected')
        self._assign_btn.label = ''
        self._assign_btn.enabled = False
        self._assign_btn.tooltip = (
            'Assign the currently selected class to the selected points.'
        )

        self._enable_cb.changed.connect(self._on_toggle)
        self._class_spin.changed.connect(self._on_class_changed)
        self._assign_btn.changed.connect(self._on_assign)
        point_layer_widget.changed.connect(self._on_layer_changed)

        super().__init__(
            layout='vertical',
            widgets=[
                self._enable_cb,
                self._class_row,
                self._assign_btn,
            ],
            labels=False,
        )

    # ---- slots -----------------------------------------------------------

    def _on_toggle(self, enabled):
        """Enable or disable class annotation controls.

        Parameters
        ----------
        enabled : bool
            Whether class annotation should be active.

        Returns
        -------
        None
            Internal state and the active layer are updated in place.
        """
        self._class_spin.enabled = enabled
        self._assign_btn.enabled = enabled
        layer = self._current_layer()
        if enabled:
            self._activate(layer)
        else:
            self._deactivate(layer)

    def _on_layer_changed(self, layer):
        """Switch the widget to a new active points layer.

        Parameters
        ----------
        layer : napari.layers.Points or None
            Newly selected points layer.

        Returns
        -------
        None
            The previous layer is detached and the new one is activated.
        """
        if self._enable_cb.value:
            self._deactivate(self._layer)
            self._activate(layer)
        self._layer = layer

    def _on_class_changed(self, cls):
        """Update the current class label and default new points to that class.

        Parameters
        ----------
        cls : int
            Newly selected class identifier.

        Returns
        -------
        None
            The widget label and active layer properties are updated in place.
        """
        self._update_color_label(cls)
        layer = self._current_layer()
        if layer is not None and self._enable_cb.value:
            layer.current_properties = {'class': [cls]}
            if self._assign_selected_points_class(layer, cls):
                return

        self._refresh_display(layer)

    def _on_data_changed(self, event):
        """Synchronize class metadata after points are added or removed.

        Parameters
        ----------
        event : Event
            Napari layer data event emitted after a points-layer mutation.

        Returns
        -------
        None
            The class column and display are refreshed in place.
        """
        layer = self._current_layer()
        if layer is None or self._refreshing:
            return
        self._sync_class_column(layer)
        self._refresh_display(layer)

    def _on_assign(self, _):
        """Assign the selected class to the currently selected points.

        Parameters
        ----------
        _ : Any
            Button event payload, ignored.

        Returns
        -------
        None
            The selected points are updated in place.
        """
        layer = self._current_layer()
        if layer is None:
            return
        cls = self._class_spin.value
        if not self._assign_selected_points_class(layer, cls):
            return

    # ---- helpers ---------------------------------------------------------

    def _update_color_label(self, cls):
        """Update the class-color swatch to match the selected class.

        Parameters
        ----------
        cls : int
            Class identifier whose configured color should be displayed.

        Returns
        -------
        None
            The preview swatch is updated in place.
        """
        color = _CLASS_COLORS_HEX[cls]
        self._color_label.native.setStyleSheet(
            'background-color: ' + color + ';'
            'border: 1px solid palette(mid);'
            'min-width: 18px;'
            'max-width: 18px;'
            'min-height: 18px;'
            'max-height: 18px;'
        )
        self._color_label.tooltip = color

    def _assign_selected_points_class(self, layer, cls):
        """Assign a class value to all selected points in a layer.

        Parameters
        ----------
        layer : napari.layers.Points or None
            Layer containing the selected points to update.
        cls : int
            Class identifier to assign.

        Returns
        -------
        bool
            ``True`` when at least one selected point is updated, else ``False``.
        """
        if layer is None:
            return False

        selected = list(layer.selected_data)
        if not selected:
            return False

        self._ensure_class_column(layer)

        # Reassigning layer.features emits the features event in napari.
        # In-place pandas edits may not invalidate text labels immediately.
        features = layer.features.copy()
        features.loc[selected, 'class'] = cls
        layer.features = features

        self._refresh_display(layer)
        layer.refresh()
        return True

    def _current_layer(self):
        """Return the currently selected points layer.

        Parameters
        ----------
        None

        Returns
        -------
        napari.layers.Points or None
            The active points layer selected in the companion widget.
        """
        return self._point_layer_widget.value

    def _activate(self, layer):
        """Attach event handling and initialize class data for a points layer.

        Parameters
        ----------
        layer : napari.layers.Points or None
            Layer to activate for class annotation.

        Returns
        -------
        None
            The layer is prepared for class annotation in place.
        """
        if layer is None:
            return
        self._layer = layer
        self._ensure_class_column(layer)
        # New points will inherit the currently selected class.
        layer.current_properties = {'class': [self._class_spin.value]}
        self._disconnect_events()
        self._event_conn = layer.events.data.connect(self._on_data_changed)

        self._refresh_display(layer)

    def _deactivate(self, layer):
        """Detach event handling and hide annotation visuals for a points layer.

        Parameters
        ----------
        layer : napari.layers.Points or None
            Layer to deactivate.

        Returns
        -------
        None
            The layer is left in a non-annotating state.
        """
        self._disconnect_events()
        if layer is None:
            return
        try:
            layer.text.visible = False
            if len(layer.data) > 0:
                layer.face_color = 'white'
        except Exception as e:
            raise RuntimeError(
                'Failed to deactivate class annotation for layer '
                f'{layer.name}.'
            ) from e

    def _disconnect_events(self):
        """Disconnect the stored data-change callback if it is attached.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Any existing event connection is removed.
        """
        if self._event_conn is not None:
            with contextlib.suppress(Exception):
                self._event_conn.disconnect()
            self._event_conn = None

    def _ensure_class_column(self, layer):
        """Ensure the points layer has a ``class`` feature column.

        Parameters
        ----------
        layer : napari.layers.Points
            Points layer whose feature table will be checked.

        Returns
        -------
        None
            The features table is updated in place when needed.
        """
        n = len(layer.data)
        if 'class' not in layer.features.columns:
            layer.features['class'] = np.zeros(n, dtype=np.int64)

    def _sync_class_column(self, layer):
        """Resize the ``class`` column to match the current number of points.

        Parameters
        ----------
        layer : napari.layers.Points
            Points layer whose feature table will be synchronized.

        Returns
        -------
        None
            The ``class`` column is updated in place.
        """
        n = len(layer.data)
        if 'class' not in layer.features.columns:
            layer.features['class'] = np.zeros(n, dtype=np.int64)
            return
        old_n = len(layer.features['class'])
        if old_n == n:
            return
        if n > old_n:
            cls = self._class_spin.value
            layer.features['class'] = np.concatenate(
                [
                    layer.features['class'].to_numpy(),
                    np.full(n - old_n, cls, dtype=np.int64),
                ]
            )
        else:
            layer.features['class'] = layer.features['class'].to_numpy()[:n]

    def _refresh_display(self, layer):
        """Recompute face colors and text labels from the stored class values.

        Parameters
        ----------
        layer : napari.layers.Points
            Points layer to redraw.

        Returns
        -------
        None
            The layer's visual properties are updated in place.
        """
        if self._refreshing:
            return
        n = len(layer.data)
        if n == 0:
            return
        self._ensure_class_column(layer)
        classes = layer.features['class'].to_numpy().astype(int)

        colors = np.array(
            [
                _CLASS_COLORS_RGBA[c]
                if 0 <= c < _N_CLASSES
                else _UNASSIGNED_RGBA
                for c in classes
            ],
            dtype=float,
        )
        self._refreshing = True
        try:
            layer.face_color = colors
            layer.text = {
                'string': '{class}',
                'size': 10,
                'color': 'white',
                'anchor': 'center',
                'visible': True,
            }
        finally:
            self._refreshing = False


class ProofreadWidget(Container):
    """Main widget for point-proofreading tasks.

    This widget provides a set of controls for managing points layers in
    Napari, including size adjustment, grid overlay creation, and optional
    class annotation.
    """

    def __init__(self):
        self.grid_widget = widget_grid()
        self.points_widget = widget_points
        self.point_class_widget = PointClassWidget(
            self.points_widget.point_layer
        )

        setup_layout(self.grid_widget)
        setup_layout(self.points_widget)
        setup_layout(self.point_class_widget)

        grid_tools = _make_titled_panel(
            'Grid Overlay Tools',
            [self.grid_widget],
        )

        point_tools = _make_titled_panel(
            'Point Layer Tools',
            [self.points_widget, self.point_class_widget],
        )

        super().__init__(
            layout='vertical',
            widgets=[
                grid_tools,
                point_tools,
            ],
            labels=False,
        )
