from magicgui.widgets import (
    Container,
    Label,
)
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QMessageBox, QSizePolicy

_HELP_TEXT = (
    '<h2>Point Proofread - Quick Guide 🛠</h2>'
    '<h3>🖼️ Image workflow</h3>'
    '<ul>'
    '  <li>Open an image (or drag and drop).</li>'
    "  <li>Click 'Convert to RGB'.</li>"
    '  <li>In the layer list, right-click the RGB image and select '
    "  'Split RGB' to separate channels (recommended for 3D).</li>"
    '</ul>'
    '<h3>🎨 Display tuning</h3>'
    '<ul>'
    "  <li>Use 'Normalize' or 'Contrast max' to adjust visibility.</li>"
    "  <li>In 3D mode (Ctrl+Y), increase z scale with 'ZYX scale' "
    '  if structures look flattened.</li>'
    "  <li>Use 'Make grid' to overlay a grid on the selected image layer. "
    '  This is useful to focus on specific regions.</li>'
    '</ul>'
    '<h3>📄 Points and CSV</h3>'
    '<ul>'
    '  <li>CSV files are loaded as a Points layer.</li>'
    "  <li>Use 'Points size' to improve point visibility.</li>"
    '  <li>Enable class annotation to associate a class with each point.</li>'
    "  <li>Use 'Threshold probability (csv)' to filter predictions "
    '  by confidence.</li>'
    '</ul>'
    '<h3>💡 Tip</h3>'
    '<ul>'
    '  <li>Keep Points layers above Image layers so points remain '
    '  clearly visible.</li>'
    '</ul>'
)


def _build_help_dialog(parent=None):
    """Build the plugin help dialog with explicit rich-text wrapping.

    Parameters
    ----------
    parent : QWidget or None
        Optional parent widget used for dialog ownership.

    Returns
    -------
    QMessageBox
        Configured modal help dialog.
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle('Point Proofread Help')
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setTextFormat(Qt.RichText)
    msg_box.setText(_HELP_TEXT)
    msg_box.setMinimumWidth(560)

    # Ubuntu may keep rich-text labels too narrow inside QMessageBox.
    # Force wrapping on the text label and give it a wider preferred width.
    for label in msg_box.findChildren(QLabel):
        if label.text() == _HELP_TEXT:
            label.setWordWrap(True)
            label.setTextFormat(Qt.RichText)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            label.setMinimumWidth(520)
            break

    return msg_box


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
    msg_box = _build_help_dialog(parent)
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
    panel.native.layout().setSpacing(
        0
    )  # Distance between adjacent widgets (in pixels)
    panel.native.layout().setContentsMargins(
        2, 0, 2, 1
    )  # Left, top, right, bottom margins (in pixels)
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
