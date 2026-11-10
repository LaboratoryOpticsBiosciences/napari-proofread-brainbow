"""
Image widget for the napari-point-proofread plugin.

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
"""

import napari
import numpy as np
from magicgui import magic_factory, magicgui
from magicgui.widgets import (
    Container,
    Label,
    ProgressBar,
    PushButton,
)
from napari import layers as L
from napari import types
from napari.qt import thread_worker
from qtpy.QtCore import Qt

from ._widget_utils import _make_titled_panel, _show_help_dialog, setup_layout


@magic_factory(
    img_layer={'tooltip': 'Select raw image'},
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
            kwargs = {'name': img_layer.name + '_rgb'}
            return (data.transpose(0, 2, 3, 1), kwargs, 'image')
        elif data.shape[0] == 3:
            # (c=3, z, y, x)
            # data = img_layer.data.transpose(1, 0, 2, 3)
            viewer.layers.pop(viewer.layers.index(img_layer))
            kwargs = {'name': img_layer.name + '_rgb'}
            return (data.transpose(1, 2, 3, 0), kwargs, 'image')
    else:
        return None


@thread_worker
def normalize(
    img_layer: L.Image,
    perc: float = 99.0,
):
    """Calculate the 99th percentile in a background thread."""
    data = img_layer.data

    if data.shape[-1] == 3:
        _vmax = np.percentile(data, perc, axis=tuple(range(data.ndim - 1)))
        vmax = max(_vmax)
    else:
        vmax = np.percentile(data, perc)

    return vmax


@magicgui(
    img_layer={
        'tooltip': 'Set maximum contrast limit to 99 percentile of the given image'
    },
    call_button='Normalize (perc=99)',
)
def widget_norm(
    viewer: 'napari.Viewer',
    img_layer: L.Image,
):
    if img_layer is None:
        return

    worker = normalize(img_layer, perc=99)

    def update_layer(vmax):
        # Update safely on the main thread
        img_layer.contrast_limits = [img_layer.contrast_limits[0], vmax]

    worker.returned.connect(update_layer)

    # 1. Initialize and control the progress bar cleanly
    def start_progress():
        # Set to (0,0) for an indeterminate loading/busy animation
        pbar.range = (0, 0)
        pbar.show()

    def stop_progress():
        pbar.hide()

    worker.started.connect(start_progress)
    worker.finished.connect(stop_progress)

    worker.start()


# 2. Instantiate the progress bar widget and append it to the norm widget
pbar = ProgressBar(visible=False)
pbar.label = ''


@magicgui(
    contrast_limits_vmax={
        'label': 'vmax',
        'widget_type': 'FloatSlider',
        'value': 255,
        'step': 1,
        'min': 1,
        'max': 255,
        'tooltip': "Adjust all images' contrast_limits at once",
    },
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
    for layer in viewer.layers:
        if isinstance(layer, L.Image):
            _min = layer.contrast_limits[0]
            if contrast_limits_vmax > _min:
                layer.contrast_limits = [
                    layer.contrast_limits[0],
                    contrast_limits_vmax,
                ]


@magicgui(
    scale_z={
        'label': 'Scale z',
        'widget_type': 'FloatSlider',
        'value': 1.0,
        'step': 0.1,
        'min': 0.5,
        'max': 5.0,
        'tooltip': 'Adjust z scale for all image layers',
    },
    scale_y={
        'label': 'Scale y',
        'widget_type': 'FloatSlider',
        'value': 1.0,
        'step': 0.1,
        'min': 0.5,
        'max': 5.0,
        'tooltip': 'Adjust y scale for all image layers',
    },
    scale_x={
        'label': 'Scale x',
        'widget_type': 'FloatSlider',
        'value': 1.0,
        'step': 0.1,
        'min': 0.5,
        'max': 5.0,
        'tooltip': 'Adjust x scale for all image layers',
    },
    scale_z_default={
        'widget_type': 'PushButton',
        'value': True,
        'text': 'Reset z',
        'tooltip': 'Reset z scale to 1.0 for all image layers',
    },
    scale_y_default={
        'widget_type': 'PushButton',
        'value': True,
        'text': 'Reset y',
        'tooltip': 'Reset y scale to 1.0 for all image layers',
    },
    scale_x_default={
        'widget_type': 'PushButton',
        'value': True,
        'text': 'Reset x',
        'tooltip': 'Reset x scale to 1.0 for all image layers',
    },
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
    for layer in viewer.layers:
        if hasattr(layer, 'scale'):
            # print(f"set scale of {layer.name} to {scale}")
            layer.scale = scale


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
    for layer in viewer.layers:
        if hasattr(layer, 'scale') and isinstance(layer, (L.Image, L.Points)):
            layer.scale = scale


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
    for layer in viewer.layers:
        if hasattr(layer, 'scale'):
            # print(f"set scale of {layer.name} to {scale}")
            layer.scale = scale


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
    for layer in viewer.layers:
        if hasattr(layer, 'scale'):
            # print(f"set scale of {layer.name} to {scale}")
            layer.scale = scale


class MainWidget(Container):
    def __init__(self, layout='vertical'):
        cvt_widget = widget_cvtRGB()
        cvt_widget.call_button.text = 'Convert to RGB'
        cvt_widget.call_button.tooltip = 'Convert the selected image to RGB by moving the channel axis to the end'

        norm_widget = widget_norm
        norm_widget.call_button.text = 'Normalize (perc=99)'
        norm_widget.call_button.tooltip = (
            'Normalize the selected image by setting the maximum contrast limit to '
            'the 99 percentile of the image'
        )

        # Hide left labels to keep the UI compact in a single column.
        cvt_widget.label = ''
        norm_widget.label = ''
        widget_contrast_limits_all.label = ''
        widget_scale.label = ''

        # Replace stacked reset buttons with one horizontal button row.
        widget_scale.scale_z_default.visible = False
        widget_scale.scale_y_default.visible = False
        widget_scale.scale_x_default.visible = False

        scale_reset_z_button = PushButton(text='Reset z')
        scale_reset_z_button.label = ''
        scale_reset_z_button.changed.connect(_scale_z_default)
        scale_reset_z_button.tooltip = (
            'Reset z scale to 1.0 for all image layers'
        )

        scale_reset_y_button = PushButton(text='Reset y')
        scale_reset_y_button.label = ''
        scale_reset_y_button.changed.connect(_scale_y_default)
        scale_reset_y_button.tooltip = (
            'Reset y scale to 1.0 for all image layers'
        )

        scale_reset_x_button = PushButton(text='Reset x')
        scale_reset_x_button.label = ''
        scale_reset_x_button.changed.connect(_scale_x_default)
        scale_reset_x_button.tooltip = (
            'Reset x scale to 1.0 for all image layers'
        )

        scale_reset_buttons = Container(
            layout='horizontal',
            widgets=[
                scale_reset_z_button,
                scale_reset_y_button,
                scale_reset_x_button,
            ],
            labels=False,
        )

        # Keep normalize progress full-width outside the form-layout label column.
        norm_progress_row = Container(
            layout='horizontal',
            widgets=[pbar],
            labels=False,
        )

        # Adjust layout spacing and margins for each widget to make the UI compact.
        setup_layout(cvt_widget)
        setup_layout(norm_widget)
        setup_layout(scale_reset_buttons)
        setup_layout(norm_progress_row)
        setup_layout(widget_scale)
        setup_layout(widget_contrast_limits_all)

        # Share one layer selector across Convert/Normalize to save space.
        cvt_widget.img_layer.label = 'Image layer'
        norm_widget.img_layer.visible = False

        def _sync_shared_img_layer(_event=None):
            selected_layer = cvt_widget.img_layer.value
            shared_choices = tuple(cvt_widget.img_layer.choices)

            # Keep hidden selectors aligned with the shared selector options.
            norm_widget.img_layer.choices = shared_choices

            if (
                selected_layer in shared_choices
                and norm_widget.img_layer.value is not selected_layer
            ):
                norm_widget.img_layer.value = selected_layer

            # Update vmax slider to match the selected image's contrast limit.
            if selected_layer is not None:
                vmax = selected_layer.contrast_limits[1]

                if (
                    widget_contrast_limits_all.contrast_limits_vmax.value
                    != vmax
                ):
                    widget_contrast_limits_all.contrast_limits_vmax.max = vmax
                    widget_contrast_limits_all.contrast_limits_vmax.value = (
                        vmax
                    )

        cvt_widget.img_layer.changed.connect(_sync_shared_img_layer)
        _sync_shared_img_layer()

        help_button = PushButton(text='❓ Show help')
        help_button.label = ''
        help_button.changed.connect(lambda _: _show_help_dialog(self.native))
        help_button.tooltip = 'Show a help dialog with usage instructions and tips for this plugin'
        help_button_row = Container(
            layout='horizontal', widgets=[help_button], labels=False
        )
        help_button_row.native.layout().setAlignment(
            help_button.native, Qt.AlignHCenter
        )

        image_tools = _make_titled_panel(
            'Image Layer Tools',
            [
                cvt_widget,
                norm_widget,
                norm_progress_row,
                Label(value='Contrast max'),
                widget_contrast_limits_all,
                Label(value='ZYX scale'),
                widget_scale,
                scale_reset_buttons,
            ],
        )

        widgets = [
            help_button_row,
            image_tools,
        ]
        super().__init__(layout=layout, widgets=widgets, labels=False)
