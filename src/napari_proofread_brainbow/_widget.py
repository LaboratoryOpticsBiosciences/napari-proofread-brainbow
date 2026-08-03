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

from magicgui import magic_factory, magicgui
from magicgui.widgets import Container, Label, PushButton
from napari import layers as L
from napari import types
from qtpy.QtWidgets import QMessageBox


_HELP_TEXT = (
    "Proofread Brainbow - Quick Guide\n"
    "================================\n\n"
    "Image workflow\n"
    "- Open an image (or drag and drop).\n"
    "- Click 'Convert to RGB'.\n"
    "- In the layer list, right-click the RGB image and select\n"
    "  'Split RGB' to separate channels (recommended for 3D).\n\n"
    "Display tuning\n"
    "- Use 'Normalize' or 'Contrast max' to adjust visibility.\n"
    "- In 3D mode (Ctrl+Y), increase z scale with 'ZYX scale'\n"
    "  if structures look flattened.\n\n"
    "Points and CSV\n"
    "- CSV files are loaded as a Points layer.\n"
    "- Use 'Points size' to improve point visibility.\n"
    "- Use 'Threshold probability (csv)' to filter predictions\n"
    "  by confidence.\n\n"
    "Tip\n"
    "- Keep Points layers above Image layers so points remain\n"
    "  clearly visible."
)


def _show_help_dialog(parent=None):
    """Show plugin usage help in a compact popup dialog."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle('Proofread Brainbow Help')
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setText(_HELP_TEXT)
    # Ensure full lines are visible without aggressive wrapping.
    msg_box.setStyleSheet('QLabel{min-width: 400px;}')
    msg_box.exec_()


def _make_titled_panel(title: str, widgets):
    """Create a compact bordered panel with a title row."""
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
    """Adjust layout spacing and margins for a magicgui container."""
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
    def pairwise(x):
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

        scale_reset_y_button = PushButton(text='Reset y')
        scale_reset_y_button.label = ''
        scale_reset_y_button.changed.connect(_scale_y_default)

        scale_reset_x_button = PushButton(text='Reset x')
        scale_reset_x_button.label = ''
        scale_reset_x_button.changed.connect(_scale_x_default)

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

        help_button = PushButton(text='Show help')
        help_button.label = ''
        help_button.changed.connect(lambda _: _show_help_dialog(self.native))

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

        point_tools = _make_titled_panel(
            'Point Layer Tools',
            [widget_points],
        )

        widgets = [
            help_button,
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
        super().__init__(
            data=data,
            **kwargs,
        )

    def add(self, coord):
        """Adds point at coordinate. (Override napari.Points.add)

        Parameters
        ----------
        coord : sequence of indices to add point at
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
        """Removes selected points if any. (Override napari.Points.remove_selected)
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
        """If not set, it set to classname. It's used for save()"""
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
