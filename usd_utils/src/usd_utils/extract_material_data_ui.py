from importlib import reload
from PySide2 import QtWidgets, QtCore
import os
import hou
from usd_utils import _houdini_usd

reload(_houdini_usd)


class PublishDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(PublishDialog, self).__init__(parent=parent)
        self.resize(300, 100)
        self.setWindowTitle('CAT Save metadata')

        script_dir = os.path.dirname(__file__)
        assets_metadata_path = os.path.join(script_dir, "assets_metadata.json")
        self.metadata = os.path.normpath(assets_metadata_path)

        self.central_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.central_layout)
        self.central_layout.setAlignment(QtCore.Qt.AlignTop)

        self.input_label = QtWidgets.QLabel("Library Tag")
        self.central_layout.addWidget(self.input_label)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Type library tag here")
        self.central_layout.addWidget(self.name_input)
        spacerItem1 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.central_layout.addItem(spacerItem1)

        self.save_button = QtWidgets.QPushButton("Save Data")
        self.central_layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self.save)

        # Add Styles:
        script_dir = os.path.dirname(__file__)
        resources_path = os.path.join(script_dir, "..", "..", "resources")

        resources_path = os.path.normpath(resources_path)

        with open(os.path.join(resources_path, "style_hou.qss"), 'r') as f:
            self.setStyleSheet(f.read())

    def save(self):
        if self.name_input.text() != "":
            template1 = _houdini_usd.CAT_ExtractMaterialsData(self.metadata, self.name_input.text())
            for node in hou.selectedNodes():
                template1.get_geometry_data(node)
            self.close()
        else:
            if hou.isUIAvailable():
                text = "Type Library Tag"
                user_response = hou.ui.displayMessage(
                    text)


dialog = None


def show_houdini():
    import hou
    global dialog
    dialog = PublishDialog(parent=hou.qt.mainWindow())
    dialog.show()
    return dialog
