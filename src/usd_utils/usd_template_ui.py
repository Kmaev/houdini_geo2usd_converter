from importlib import reload
from PySide2 import QtWidgets
import json
import os
import hou
import _houdini_usd
reload(_houdini_usd)

class PublishDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(PublishDialog, self).__init__(parent=parent)

        self.project_file = r"E:\dev\cat\src\usd_utils\assets_metadata.json"
        libraries = {"KB" : "KitBash", "MS" : "Megascans"}
        self.selected_assets = []

        self.central_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.central_layout)
        self.resize(700, 600)
        self.setWindowTitle('CAT_USD')

        with open(self.project_file, "r") as read_file:
            self.read = json.load(read_file)

        self.lib_list = QtWidgets.QListWidget(self)
        self.assets_list = QtWidgets.QListWidget(self)
        self.assets_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.add_missing_textures = QtWidgets.QCheckBox("Add Missing Textures")
        self.add_missing_textures.setEnabled(False)

        self.add_displacement_texture = QtWidgets.QCheckBox("Add Displacement Textures")
        self.add_displacement_texture.setEnabled(False)

        library_list = self.read.keys()

        for i in library_list:
            item = QtWidgets.QListWidgetItem()
            item.setText(libraries[i])
            item.setData(1, i)
            self.lib_list.addItem(item)

        self.libraries_grp = QtWidgets.QGroupBox('Libreries')
        self.libraries_grp_layout = QtWidgets.QHBoxLayout()
        self.libraries_grp.setLayout(self.libraries_grp_layout)
        self.libraries_grp_layout.addWidget(self.lib_list)

        self.assets_grp = QtWidgets.QGroupBox('Assets Group')
        self.assets_grp_layout = QtWidgets.QHBoxLayout()
        self.assets_grp.setLayout(self.assets_grp_layout)
        self.assets_grp_layout.addWidget(self.assets_list)

        self.save_in_bg = QtWidgets.QPushButton("Save to Disk in Background", self)
        self.save_in_bg.setEnabled(False)
        self.load_template = QtWidgets.QPushButton("Load Template", self)
        self.load_template.setEnabled(False)

        # Add the group box to the central layout
        self.central_layout.addWidget(self.libraries_grp)
        self.central_layout.addWidget(self.assets_grp)
        self.central_layout.addWidget(self.add_missing_textures)
        self.central_layout.addWidget(self.add_displacement_texture)

        self.central_layout.addWidget(self.save_in_bg)
        self.central_layout.addWidget(self.load_template)

        self.lib_list.itemSelectionChanged.connect(self.onLibChanged)
        self.assets_list.itemSelectionChanged.connect(
            self.onAssetChanged)
        self.save_in_bg.clicked.connect(self.onSaveInBg)
        self.load_template.clicked.connect(self.onLoadTemplate)

        style_folder = r"E:\dev\cat\resources"
        with open(os.path.join(style_folder, "style_hou.qss"), 'r') as f:
            self.setStyleSheet(f.read())

    def selectedLibrary(self):
        selected =self.lib_list.selectedItems()[0].data(1)
        return selected if selected else None

    def selectedAsset(self):
        items = self.assets_list.selectedItems()
        for i in range(len(items)):
            self.selected_assets.append(str(self.assets_list.selectedItems()[i].data(1)))
        return self.selected_assets if self.selected_assets else None

    def onLibChanged(self):
        self.assets_list.clear()
        lib = self.selectedLibrary()
        assets_list = sorted(list(self.read[lib].keys()))
        if not lib:
            return
        for i in assets_list:

            name = self.read[lib][i]["asset_name"]

            item = QtWidgets.QListWidgetItem()
            item.setText(name)
            item.setData(1, i)
            self.assets_list.addItem(item)

    def onAssetChanged(self):
        if not self.assets_list.selectedItems():
            self.save_in_bg.setEnabled(False)
            self.load_template.setEnabled(False)
            self.add_missing_textures.setEnabled(False)
            self.add_displacement_texture.setEnabled(False)
            return
        self.selected_assets = []
        self.save_in_bg.setEnabled(True)
        self.load_template.setEnabled(True)
        self.add_missing_textures.setEnabled(True)
        self.add_displacement_texture.setEnabled(True)
        self.selectedAsset()

    def onSaveInBg(self):
        add_missing_tex = self.add_missing_textures.isChecked()
        add_displ_tex = self.add_displacement_texture.isChecked()
        lib_tag = self.selectedLibrary()
        with hou.InterruptableOperation("Performing Tasks", long_operation_name="Assets Name",
                                        open_interrupt_dialog=True) as op:
            for i in self.selected_assets:
                op.updateLongProgress(self.selected_assets.index(i) / float(len(self.selected_assets)),
                                      "Converting to .usd {}/{}".format(self.selected_assets.index(i) + 1,
                                                                    len(self.selected_assets)))
                if lib_tag == "MS":
                    template1 = _houdini_usd.MS_GeometryImport(self.project_file, "mantra", lib_tag, add_displ_tex, add_missing_tex, True)

                elif lib_tag == "KB":
                    template1 = _houdini_usd.KB_GeometryImport(self.project_file, "mantra", lib_tag, add_displ_tex,
                                                               add_missing_tex, True)
                template1.create_main_template(i)

    def onLoadTemplate(self):
        add_missing_tex = self.add_missing_textures.isChecked()
        add_displ_tex = self.add_displacement_texture.isChecked()
        lib_tag = self.selectedLibrary()
        with hou.InterruptableOperation("Performing Tasks", long_operation_name="Assets Name",
                                        open_interrupt_dialog=True) as op:
            for i in self.selected_assets:

                op.updateLongProgress(self.selected_assets.index(i) / float(len(self.selected_assets)),
                                      "Loading Assets {}/{}".format(self.selected_assets.index(i) + 1, len(self.selected_assets)))
                if lib_tag == "MS":
                    template1 = _houdini_usd.MS_GeometryImport(self.project_file, "mantra", lib_tag, add_displ_tex,
                                                               add_missing_tex)

                elif lib_tag == "KB":
                    template1 = _houdini_usd.KB_GeometryImport(self.project_file, "mantra", lib_tag, add_displ_tex,
                                                               add_missing_tex)
                template1.create_main_template(i)


dialog = None
def show_houdini():
    import hou
    global dialog
    dialog =PublishDialog(parent=hou.qt.mainWindow())
    dialog.show()
    return dialog
