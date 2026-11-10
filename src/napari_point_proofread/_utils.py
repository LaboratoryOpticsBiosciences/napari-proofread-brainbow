
from magicgui.widgets import Container, Label


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