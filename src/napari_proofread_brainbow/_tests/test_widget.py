from napari_proofread_brainbow import MainWidget
from napari_proofread_brainbow._widget import widget_cvtRGB
import numpy as np

# make_napari_viewer is a pytest fixture that returns a napari viewer object
# capsys is a pytest fixture that captures stdout and stderr output streams
def test_main_widget(make_napari_viewer):
    # make viewer and add an image layer using our fixture
    viewer = make_napari_viewer()

    # create main widget, passing in the viewer
    main_widget = MainWidget()

    # Check top-level layout
    assert main_widget[0].text == 'Show help'

    # Check titled image panel
    image_tools = main_widget[1]
    assert image_tools[0].value == 'Image Layer Tools'
    assert len(image_tools) == 10
    assert image_tools[4].contrast_limits_vmax.label == 'vmax'
    assert image_tools[6].scale_z.label == 'scale z'
    assert image_tools[6].scale_y.label == 'scale y'
    assert image_tools[6].scale_x.label == 'scale x'
    assert image_tools[9].xbins.label == 'xbins'
    assert image_tools[9].ybins.label == 'ybins'

    # Check titled point panel
    point_tools = main_widget[2]
    assert point_tools[0].value == 'Point Layer Tools'
    assert len(point_tools) == 2

    # read captured output and check that it's as we expected
    # captured = capsys.readouterr()
    # assert captured.out == "napari has 1 layers\n"


# def test_example_magic_widget(make_napari_viewer, capsys):
#     viewer = make_napari_viewer()
#     layer = viewer.add_image(np.random.random((100, 100)))

#     # this time, our widget will be a MagicFactory or FunctionGui instance
#     my_widget = example_magic_widget()

#     # if we "call" this object, it'll execute our function
#     my_widget(viewer.layers[0])

#     # read captured output and check that it's as we expected
#     captured = capsys.readouterr()
#     assert captured.out == f"you have selected {layer}\n"
