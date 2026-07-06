"""Plugin main widgets

widgets
-------
widget_cvtRGB()
    Put channel dims to the last dims so that napari can understand it as RGB
widget_norm
    Normalize the selected image with 99 percentile
widget_contrast_limits_all
    Change contrast limit max of all images at once
widget_scale
    Change scales of z, y, x
widget_points
    Change size of points at once
"""
from itertools import tee

import numpy as np

import napari
from magicgui import magic_factory, magicgui
from magicgui.widgets import CheckBox, Container, Label, PushButton, SpinBox
from napari import layers as L
from napari import types
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox


_HELP_TEXT = (
    "<h2>Proofread Brainbow - Quick Guide 🛠</h2>"
    
    "<h3>🖼️ Image workflow</h3>"
    "<ul>"
    "  <li>Open an image (or drag and drop).</li>"
    "  <li>Click 'Convert to RGB'.</li>"
    "  <li>In the layer list, right-click the RGB image and select "
    "  'Split RGB' to separate channels (recommended for 3D).</li>"
    "</ul>"
    
    "<h3>🎨 Display tuning</h3>"
    "<ul>"
    "  <li>Use 'Normalize' or 'Contrast max' to adjust visibility.</li>"
    "  <li>In 3D mode (Ctrl+Y), increase z scale with 'ZYX scale' "
    "  if structures look flattened.</li>"
    "  <li>Use 'Make grid' to overlay a grid on the selected image layer. "
    "  This is useful to focus on specific regions.</li>"
    "</ul>"
    
    "<h3>📄 Points and CSV</h3>"
    "<ul>"
    "  <li>CSV files are loaded as a Points layer.</li>"
    "  <li>Use 'Points size' to improve point visibility.</li>"
    "  <li>Enable class annotation to associate a class with each point.</li>"
    "  <li>Use 'Threshold probability (csv)' to filter predictions "
    "  by confidence.</li>"
    "</ul>"
    
    "<h3>💡 Tip</h3>"
    "<ul>"
    "  <li>Keep Points layers above Image layers so points remain "
    "  clearly visible.</li>"
    "</ul>"
)


def _show_help_dialog(parent=None):
    """Show the plugin help text in a modal dialog.

    Parameters
    ----------
    parent : QWidget or None
        Optional parent widget used for dialog ownership.

    Returns
    -------
    None
        The dialog is shown for its side effect.
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle('Proofread Brainbow Help')
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setText(_HELP_TEXT)
    # Ensure full lines are visible without aggressive wrapping.
    msg_box.setStyleSheet('QLabel{min-width: 400px;}')
    msg_box.exec_()


def _make_titled_panel(title: str, widgets):
    """Build a titled container panel for a group of widgets.

    Parameters
    ----------
    title : str
        Text displayed in the panel header.
    widgets : sequence
        Widgets to place inside the panel body.

    Returns
    -------
    magicgui.widgets.Container
        A styled container holding the title and provided widgets.
    """
    title_label = Label(value=title)
    title_label.label = ''
    title_label.native.setObjectName('panelTitle')

    panel = Container(
        layout='vertical',
        widgets=[title_label, *widgets],
        labels=False,
    )
    panel.native.setObjectName('panelContainer')
    panel.native.setStyleSheet(
        '#panelContainer {'
        ' border: 1px solid palette(mid);'
        ' border-radius: 0px;'
        ' padding: 0px;'
        ' margin: 0px;'
        '}'
        '#panelTitle {'
        ' font-weight: 600;'
        ' padding: 0px;'
        ' margin-bottom: 4px;'
        '}'
    )
    panel.native.layout().setSpacing(0)  # Distance between adjacent widgets (in pixels)
    panel.native.layout().setContentsMargins(2, 0, 2, 1)  # Left, top, right, bottom margins (in pixels)
    return panel

def setup_layout(gui_container):
    """Apply compact spacing and margins to a magicgui container.

    Parameters
    ----------
    gui_container : magicgui.widgets.Container
        Container whose native Qt layout will be adjusted.

    Returns
    -------
    None
        The container is modified in place.
    """
    # Adjust structural layout padding and inner widget spacing
    qt_layout = gui_container.native.layout()
    qt_layout.setSpacing(4)
    qt_layout.setContentsMargins(10, 0, 10, 4)  # left, top, right, bottom


@magic_factory(
    img_layer=dict(tooltip="Select raw Brainbow image"),
    call_button='Convert to RGB',
)
def widget_cvtRGB(
    viewer: 'napari.Viewer',
    img_layer: L.Image,
) -> types.LayerDataTuple:
    """Move a channel axis to the end so napari can display the image as RGB.

    Parameters
    ----------
    viewer : napari.Viewer
        Active Napari viewer that owns the layers.
    img_layer : napari.layers.Image
        The selected image layer to convert.

    Returns
    -------
    LayerDataTuple or None
        RGB image layer data when conversion is possible, otherwise ``None``.
    """
    # print(len(viewer.layers))
    # print(f"you have selected {img_layer}")
    
    # Do nothing if no image layers are present.
    # This prevents errors when the widget is initialized.
    if len(viewer.layers) < 1:
        return None
    
    data = img_layer.data
    # print(data.shape, data.ndim, data.dtype)
    if data.ndim == 4:
        # assume (z, c=3, y, x) or (c=3, z, y, x)
        if data.shape[-1] == 3:
            return None
        elif data.shape[1] == 3:
            # (z, c=3, y, x)
            # data = img_layer.data.transpose(1, 0, 2, 3)
            viewer.layers.pop(viewer.layers.index(img_layer))
            kwargs = dict(
                name=img_layer.name + '_rgb'
            )
            return (data.transpose(0, 2, 3, 1), kwargs, 'image')
        elif data.shape[0] == 3:
            # (c=3, z, y, x)
            # data = img_layer.data.transpose(1, 0, 2, 3)
            viewer.layers.pop(viewer.layers.index(img_layer))
            kwargs = dict(
                name=img_layer.name + '_rgb'
            )
            return (data.transpose(1, 2, 3, 0), kwargs, 'image')
    else:
        return None

@magicgui(
    img_layer=dict(tooltip="Set maximum contrast limit to 99 percentile of the "
                   "given image"),
    call_button='Normalize (perc=99)',
)
def widget_norm(
    viewer: 'napari.Viewer',
    img_layer: L.Image,
):
    """Set the selected image's upper contrast limit to its 99th percentile.

    Parameters
    ----------
    viewer : napari.Viewer
        Active Napari viewer containing the layers.
    img_layer : napari.layers.Image or None
        Image layer to normalize.

    Returns
    -------
    None
        The layer contrast limits are updated in place.
    """
    if img_layer is None:
        return
    data = img_layer.data
    # print(data.shape)
    if data.shape[-1] == 3:
        # per channel
        _vmax = np.percentile(data, 99, axis=tuple(range(data.ndim - 1)))
        # print(f'_vmax: {_vmax}')
        vmax = max(_vmax)
        # print(f'vmax: {vmax}')
    else:
        vmax = np.percentile(data, 99)
        # print(f'vmax: {vmax}')
    contrast_limits = [img_layer.contrast_limits[0], vmax]
    # print(f'contrast_limits: {contrast_limits}')
    img_layer.contrast_limits = contrast_limits


@magicgui(
    contrast_limits_vmax=dict(
        label='vmax',
        widget_type='FloatSlider',
        value=255,
        step=1,
        min=1,
        max=255,
        tooltip="Adjust all images' contrast_limits at once"
    ),
    auto_call=True,
)
def widget_contrast_limits_all(
    viewer: 'napari.Viewer',
    contrast_limits_vmax,
):
    """Apply a shared maximum contrast limit to every image layer.

    Parameters
    ----------
    viewer : napari.Viewer
        Active Napari viewer whose layers will be updated.
    contrast_limits_vmax : float
        Upper contrast limit to apply when it exceeds a layer's lower bound.

    Returns
    -------
    None
        Image layers are updated in place.
    """
    for l in viewer.layers:
        if isinstance(l, L.Image):
            _min = l.contrast_limits[0]
            if contrast_limits_vmax > _min:
                l.contrast_limits = [l.contrast_limits[0], contrast_limits_vmax]


@magicgui(
    scale_z=dict(
        widget_type='FloatSlider',
        value=1.0,
        step=0.1,
        min=0.5,
        max=5.0,
        tooltip="Adjust z scale for all image layers"
    ),
    scale_y=dict(
        widget_type='FloatSlider',
        value=1.0,
        step=0.1,
        min=0.5,
        max=5.0,
        tooltip="Adjust y scale for all image layers"
    ),
    scale_x=dict(
        widget_type='FloatSlider',
        value=1.0,
        step=0.1,
        min=0.5,
        max=5.0,
        tooltip="Adjust x scale for all image layers"
    ),
    scale_z_default=dict(
        widget_type='PushButton',
        value=True,
        text='Reset z',
        tooltip="Reset z scale to 1.0 for all image layers"
    ),
    scale_y_default=dict(
        widget_type='PushButton',
        value=True,
        text='Reset y',
        tooltip="Reset y scale to 1.0 for all image layers"
    ),
    scale_x_default=dict(
        widget_type='PushButton',
        value=True,
        text='Reset x',
        tooltip="Reset x scale to 1.0 for all image layers"
    ),
    auto_call=True,
    call_button=False,
)
def widget_scale(
    viewer: 'napari.Viewer',
    scale_z,
    scale_y,
    scale_x,
    scale_z_default,
    scale_y_default,
    scale_x_default,
):
    """Set a shared z/y/x scale for all layers that support scaling.

    Parameters
    ----------
    viewer : napari.Viewer
        Active Napari viewer whose layers will be updated.
    scale_z, scale_y, scale_x : float
        Scale factors for the z, y, and x axes.
    scale_z_default, scale_y_default, scale_x_default : Any
        Reset controls wired into the widget; included for magicgui binding.

    Returns
    -------
    None
        Layer scales are updated in place.
    """
    scale_z = round(scale_z, 1)
    scale_y = round(scale_y, 1)
    scale_x = round(scale_x, 1)
    # print(scale_z, scale_y, scale_x)
    scale = scale_z, scale_y, scale_x
    for l in viewer.layers:
        if hasattr(l, 'scale'):
            # print(f"set scale of {l.name} to {scale}")
            l.scale = scale


@widget_scale.scale_z_default.changed.connect
def _scale_z_default(value):
    """Reset the z scale slider and apply the new scale to image and points layers.

    Parameters
    ----------
    value : Any
        Button event payload from the reset control.

    Returns
    -------
    None
        The scale widget and matching layers are updated in place.
    """
    viewer = widget_scale.viewer.value
    # print(viewer, type(viewer))
    scale_z = 1.0
    scale_y = widget_scale.scale_y.value
    scale_x = widget_scale.scale_x.value
    scale = scale_z, scale_y, scale_x
    # update widget_scale_z
    widget_scale.scale_z.value = scale_z
    for l in viewer.layers:
        if hasattr(l, 'scale'):
            # print(f"set scale of {l.name} to {scale}")
            if isinstance(l, (L.Image, L.Points)):
                l.scale = scale


@widget_scale.scale_y_default.changed.connect
def _scale_y_default(value):
    """Reset the y scale slider and apply the new scale to all layers.

    Parameters
    ----------
    value : Any
        Button event payload from the reset control.

    Returns
    -------
    None
        The scale widget and matching layers are updated in place.
    """
    viewer = widget_scale.viewer.value
    scale_z = widget_scale.scale_z.value
    scale_y = 1.0
    scale_x = widget_scale.scale_x.value
    scale = scale_z, scale_y, scale_x
    # update widget_scale_z
    widget_scale.scale_y.value = scale_y
    for l in viewer.layers:
        if hasattr(l, 'scale'):
            # print(f"set scale of {l.name} to {scale}")
            l.scale = scale


@widget_scale.scale_x_default.changed.connect
def _scale_x_default(value):
    """Reset the x scale slider and apply the new scale to all layers.

    Parameters
    ----------
    value : Any
        Button event payload from the reset control.

    Returns
    -------
    None
        The scale widget and matching layers are updated in place.
    """
    viewer = widget_scale.viewer.value
    scale_z = widget_scale.scale_z.value
    scale_y = widget_scale.scale_y.value
    scale_x = 1.0
    scale = scale_z, scale_y, scale_x
    # update widget_scale_z
    widget_scale.scale_x.value = scale_x
    for l in viewer.layers:
        if hasattr(l, 'scale'):
            # print(f"set scale of {l.name} to {scale}")
            l.scale = scale


@magicgui(
    point_size=dict(
        tooltip="Change size of all points at once",
        widget_type="Slider",
        value=10,
        max=15
    ),
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
    xbins=dict(
        widget_type='Slider',
        value=5,
        step=1,
        min=2,
        max=10,
        tooltip="Number of bins in x direction for grid"
    ),
    ybins=dict(
        widget_type='Slider',
        value=5,
        step=1,
        min=2,
        max=10,
        tooltip="Number of bins in y direction for grid"
    ),
    # thickness = dict(
    #     widget_type='FloatSlider',
    #     value=1,
    #     step=0.1,
    #     min=1,
    #     max=10,
    # ),
    # auto_call=True
    call_button='make grid'
)
def widget_grid(
    img_layer: 'napari.layers.Image',
    xbins,
    ybins,
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
        return zip(a, b)

    if img_layer is None:
        return
    
    shape = img_layer.data.shape
    width = shape[-2] if shape[-1] == 3 else shape[-1]
    height = shape[-3] if shape[-1] == 3 else shape[-2]
    bins_x = np.linspace(0, width, xbins+1, endpoint=True)
    bins_y = np.linspace(0, height, ybins+1, endpoint=True)
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
    yoffset = - height * 0.05
    xoffset = - width * 0.05
    for x0, x1 in pairwise(bins_x):
        data.append(np.array([[yoffset, x0], [yoffset, x1]]))
        ...
    for y0, y1 in pairwise(bins_y):
        data.append(np.array([[y0, xoffset], [y1, xoffset]]))
        ...

    text = {
        'string': '{number}',
        # 'anchor': ''
        # 'translation': [0, 0],
        'size': 16,
        'color': 'lime',
    }
    features = {
        'number': (
            ['' for _ in range(xbins + ybins + 2)] +  # empty for grid
            [XLABELS[i] for i in range(xbins)] +  # ABCD...
            list(range(ybins))  # 123..
        )
    }
    kwargs = dict(
        name=f'grid({img_layer.name})',
        shape_type='line',
        # edge_width=thickness,
        features=features,
        text=text,
    )
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
    return [int(h[i: i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


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
            "Enable or disable class annotation for the active points layer."
        )

        self._class_spin = SpinBox(value=0, min=0, max=_N_CLASSES - 1)
        self._class_spin.label = ''
        self._class_spin.enabled = False
        self._class_spin.tooltip = "Select the class for new points."

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
        setup_layout( self._class_row )

        self._assign_btn = PushButton(text='Assign class to selected')
        self._assign_btn.label = ''
        self._assign_btn.enabled = False
        self._assign_btn.tooltip = (
            "Assign the currently selected class to the selected points."
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

        # Force the layer name in the GUI to end in '.csv'
        # This ensures that when you click "Save", the native dialog automatically includes the extension.
        if not layer.name.lower().endswith('.csv'):
            layer.name = f"{layer.name}.csv"

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

        # Force the layer name in the GUI to end in '.csv'
        # This ensures that when you click "Save", the native dialog automatically includes the extension.
        if not layer.name.lower().endswith('.csv'):
            layer.name = f"{layer.name}.csv"

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
        except Exception:
            pass

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
            try:
                self._event_conn.disconnect()
            except Exception:
                pass
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
            layer.features['class'] = np.concatenate([
                layer.features['class'].to_numpy(),
                np.full(n - old_n, cls, dtype=np.int64),
            ])
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
            [_CLASS_COLORS_RGBA[c] if 0 <= c < _N_CLASSES else _UNASSIGNED_RGBA
             for c in classes],
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


class MainWidget(Container):
    def __init__(self, layout='vertical'):
        cvt_widget = widget_cvtRGB()
        cvt_widget.call_button.text = 'Convert to RGB'
        cvt_widget.call_button.tooltip = (
            'Convert the selected image to RGB by moving the channel axis to the end'
        )

        norm_widget = widget_norm
        norm_widget.call_button.text = 'Normalize (perc=99)'
        norm_widget.call_button.tooltip = (
            'Normalize the selected image by setting the maximum contrast limit to '
            'the 99 percentile of the image'
        )

        grid_widget = widget_grid()
        grid_widget.call_button.text = 'Make grid'
        grid_widget.call_button.tooltip = (
            'Make a grid on the selected image by drawing lines and labels'
        )
        
        # Hide left labels to keep the UI compact in a single column.
        cvt_widget.label = ''
        norm_widget.label = ''
        widget_contrast_limits_all.label = ''
        widget_scale.label = ''
        widget_points.label = ''
        grid_widget.label = ''

        # Replace stacked reset buttons with one horizontal button row.
        widget_scale.scale_z_default.visible = False
        widget_scale.scale_y_default.visible = False
        widget_scale.scale_x_default.visible = False

        scale_reset_z_button = PushButton(text='Reset z')
        scale_reset_z_button.label = ''
        scale_reset_z_button.changed.connect(_scale_z_default)
        scale_reset_z_button.tooltip = "Reset z scale to 1.0 for all image layers"

        scale_reset_y_button = PushButton(text='Reset y')
        scale_reset_y_button.label = ''
        scale_reset_y_button.changed.connect(_scale_y_default)
        scale_reset_y_button.tooltip = "Reset y scale to 1.0 for all image layers"

        scale_reset_x_button = PushButton(text='Reset x')
        scale_reset_x_button.label = ''
        scale_reset_x_button.changed.connect(_scale_x_default)
        scale_reset_x_button.tooltip = "Reset x scale to 1.0 for all image layers"

        scale_reset_buttons = Container(
            layout='horizontal',
            widgets=[
                scale_reset_z_button,
                scale_reset_y_button,
                scale_reset_x_button,
            ],
            labels=False,
        )

        # Adjust layout spacing and margins for each widget to make the UI compact.
        setup_layout(cvt_widget)
        setup_layout(norm_widget)
        setup_layout(grid_widget)
        setup_layout(scale_reset_buttons)
        setup_layout(widget_scale)
        setup_layout(widget_contrast_limits_all)
        setup_layout(widget_points)
        
        # Share one layer selector across Convert/Normalize/Grid to save space.
        cvt_widget.img_layer.label = 'Image layer'
        norm_widget.img_layer.visible = False
        grid_widget.img_layer.visible = False

        def _sync_shared_img_layer(_event=None):
            selected_layer = cvt_widget.img_layer.value
            shared_choices = tuple(cvt_widget.img_layer.choices)

            # Keep hidden selectors aligned with the shared selector options.
            norm_widget.img_layer.choices = shared_choices
            grid_widget.img_layer.choices = shared_choices

            if selected_layer in shared_choices:
                if norm_widget.img_layer.value is not selected_layer:
                    norm_widget.img_layer.value = selected_layer
                if grid_widget.img_layer.value is not selected_layer:
                    grid_widget.img_layer.value = selected_layer

            # Update vmax slider to match the selected image's contrast limit.
            if selected_layer is not None:
                vmax = selected_layer.contrast_limits[1]
                # print(f"selected_layer: {selected_layer.name}, vmax: {vmax}")
                if widget_contrast_limits_all.contrast_limits_vmax.value != vmax:
                    widget_contrast_limits_all.contrast_limits_vmax.max = vmax
                    widget_contrast_limits_all.contrast_limits_vmax.value = vmax

        cvt_widget.img_layer.changed.connect(_sync_shared_img_layer)
        _sync_shared_img_layer()

        help_button = PushButton(text='❓ Show help')
        help_button.label = ''
        help_button.changed.connect(lambda _: _show_help_dialog(self.native))
        #help_button.native.setStyleSheet('padding: 2px 6px;')
        help_button.native.setMaximumWidth(help_button.native.sizeHint().width())
        help_button.tooltip = (
            'Show a help dialog with usage instructions and tips for this plugin'
        )
        help_button_row = Container(layout='horizontal', widgets=[help_button], labels=False)
        help_button_row.native.layout().setAlignment(help_button.native, Qt.AlignHCenter)
        setup_layout(help_button_row)

        image_tools = _make_titled_panel(
            'Image Layer Tools',
            [
                cvt_widget,
                #Label(value='Normalize'),
                norm_widget,
                Label(value='Contrast max'),
                widget_contrast_limits_all,
                Label(value='ZYX scale'),
                widget_scale,
                scale_reset_buttons,
                Label(value='Grid'),
                grid_widget,
            ],
        )

        point_class_widget = PointClassWidget(widget_points.point_layer)
        setup_layout(point_class_widget)

        point_tools = _make_titled_panel(
            'Point Layer Tools',
            [widget_points, point_class_widget],
        )

        widgets = [
            help_button_row,
            image_tools,
            point_tools,
        ]
        super().__init__(layout=layout, widgets=widgets, labels=False)


# @magic_factory(
#     img_layer=dict(tooltip="Select raw probability image"),
#     threshold=dict(widget_type='FloatSlider',
#                    min=0, max=1.0, step=0.01, value=0.5),
#     auto_call=True
# )
# def threshold_prob(
#     img_layer: L.Image,
#     threshold
# ) -> types.LabelsData:
#     return img_layer.data.copy() > threshold


class ThresholdPoints(L.Points):
    """Same as Points layer with additional data callbacks
    """

    _max_points_thumbnail = 1024

    def __init__(
        self,
        data=None,
        **kwargs
    ):
        """Create a points layer that stores IDs and probabilities.

        Parameters
        ----------
        data : array-like, optional
            Initial point coordinates.
        **kwargs : dict
            Additional keyword arguments passed to the base points layer.

        Returns
        -------
        None
            The layer is initialized in place.
        """
        super().__init__(
            data=data,
            **kwargs,
        )

    def add(self, coord):
        """Add a point and initialize its ID and probability metadata.

        Parameters
        ----------
        coord : sequence of float
            Coordinate where the new point should be inserted.

        Returns
        -------
        None
            The point and mirrored source point are added in place.
        """
        super().add(coord)
        # -2 because the new point is already added.
        ind = max(self._id_offset, self.properties['id'][-2]) + 1
        self._id_offset = ind
        self.border_color[-1] = [0.0, 1.0, 0.0, 1.0]  # green
        # overriding properties
        self.properties['id'][-1] = ind
        self.properties['probability'][-1] = 1.0
        source_points = self.source_points
        source_points.add(coord)
        # match 'id' and 'probability'
        source_points.properties['id'][-1] = ind
        source_points.properties['probability'][-1] = 1.0

    def remove_selected(self):
        """Remove the selected points from this layer and its source layer.

        Parameters
        ----------
        None

        Returns
        -------
        None
            The selected points are removed in place.
        """
        index = list(self.selected_data)
        index.sort()
        if len(index):
            source_points = self.source_points
            selected_ids = [self.properties['id'][i] for i in index]
            source_ids = source_points.properties['id'].tolist()
            source_index = [source_ids.index(i) for i in selected_ids]
            # remove
            super().remove_selected()
            source_points.selected_data = set(source_index)
            source_points.remove_selected()
            # end(ThresholdPoints)

    @property
    def _type_string(self):
        """Return the layer type string used when saving the layer.

        Parameters
        ----------
        None

        Returns
        -------
        str
            The Napari layer type name for this class.
        """
        return 'points'


@magic_factory(
    # point_layer=dict(tooltip="Select probability csv"),
    threshold=dict(widget_type='FloatSlider',
                   min=0, max=1.0, step=0.01, value=0.5),
    auto_call=True,
    call_button=True,
)
def threshold_prob(
    viewer: 'napari.Viewer',
    point_layer: L.Points,
    threshold
) -> L.Points:
    """Filter points by probability and return a thresholded points layer.

    Parameters
    ----------
    viewer : napari.Viewer
        Active Napari viewer used to look up or add the thresholded layer.
    point_layer : napari.layers.Points
        Source points layer containing ``probability`` metadata.
    threshold : float
        Minimum probability required for a point to remain visible.

    Returns
    -------
    napari.layers.Points or None
        A thresholded points layer when one is created, otherwise ``None``.
    """
    if 'probability' in point_layer.properties:
        prob = point_layer.properties['probability']
        m = prob > threshold
        # update Points
        name = 'threshold_prob'
        names = [layer.name for layer in viewer.layers]
        if name in names:
            points = viewer.layers[names.index(name)]
            ids = point_layer.properties['id']
            # update
            points.data = point_layer.data[m]
            points.properties = dict(id=ids[m],
                                     probability=prob[m])
        else:
            # new Points
            # Create 'threshold_prob' layer (custom ThresholdPoints).
            # ThresholdPoints is a subclass of napari.layers.Points.
            ids = np.arange(len(prob))
            m = prob > threshold
            points = ThresholdPoints(
                data=point_layer.data.copy()[m],
                name=name,
                border_color='red',
                # add properties
                properties=dict(id=ids[m],  # assign id
                                probability=prob[m]),  # copy probability
            )
            points.source_points = point_layer
            points._id_offset = ids[-1]
            # Add 'id' properties
            point_layer.features['id'] = ids
            return points
