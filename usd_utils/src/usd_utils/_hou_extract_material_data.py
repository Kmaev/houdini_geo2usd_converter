import json

import hou

"""
    This class extracts material metadata from selected geometry in a Houdini scene and saves it as JSON.

    :param json_file: Path to the JSON metadata file to read from and write to.
    :param source_tag: Identifier tag for the source (e.g., 'MS', 'KB') to separate assets from different libraries
    """


class ExtractMaterialsData:
    def __init__(self, json_file, source_tag):
        self.metadata = json_file
        self.source_tag = source_tag

    def read_geo_file(self, node):
        """
        Traverse the node graph from the given starting node and collect all file nodes.
        """
        queue = [node]
        files = []
        while len(queue) > 0:
            current = queue.pop(0)
            if current.type().name() == "file":  # could be added another option to read from different types of file
                files.append(current)
            for node in current.inputs():
                queue.append(node)
        return files

    def get_geometry_data(self, node):
        """
        Extract geometry and material texture data from file nodes,
        updates or creates metadata entries in the JSON file.
        """
        # open json file
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)

        files = self.read_geo_file(node)
        with hou.InterruptableOperation("Performing Tasks", long_operation_name="Saving geometry data",
                                        open_interrupt_dialog=True) as op:

            for file in files:
                geometry_file = file.parm("file").evalAsString()
                op.updateLongProgress(files.index(file) / float(len(files))), "{}/{}".format(files.index(file) + 1,
                                                                                             len(files))

                # Getting geo name
                geo_name = self.get_geometry_name(node, geometry_file, self.source_tag)

                try:
                    # Writing geomjetry file name and initializing textures dictionary
                    read[self.source_tag][geometry_file] = {"asset_name": geo_name, "materials": {}}
                except:
                    read[self.source_tag] = {geometry_file: {}}
                    read[self.source_tag][geometry_file] = {"asset_name": geo_name, "materials": {}}

                # Packing geo based on material path
                pack_all = node.input(files.index(file)).createOutputNode(
                    "pack")
                pack_all.parm("packbyname").set(True)
                pack_all.parm("nameattribute").set("shop_materialpath")
                pack_all.parm("transfer_attributes").set("shop_materialpath")
                hou_geo = pack_all.geometry()

                # Getting textures data
                for mat in hou_geo.primStringAttribValues("shop_materialpath"):
                    if hou.node(mat).type().name() == "principledshader::2.0":
                        shader = hou.node(mat)
                    else:
                        shader = hou.node(mat + "/principledshader1")

                    mat_name = mat.split("/")[-1]
                    read[self.source_tag][geometry_file]["materials"][mat_name] = {"shop_materialpath": mat,
                                                                                   "textures": {}}

                    for parm in shader.parms():
                        if parm.name().endswith("texture"):
                            if parm.evalAsString() != "":
                                read[self.source_tag][geometry_file]["materials"][mat_name]["textures"][
                                    parm.name()] = parm.evalAsString()

                # Pack remove
                pack_all.destroy()
            # Writing json file
            with open(self.metadata, "w") as output_file:
                json.dump(read, output_file, indent=4)

        if hou.isUIAvailable():
            if len(files) > 1:
                text = "{} assets added to metadata".format(len(files))
                hou.ui.displayMessage(text)
            else:
                text = "{} asset added to metadata".format(len(files))
                hou.ui.displayMessage(text)

    def get_geometry_name(self, node, geometry_file, source_tag):
        """
         Extracts asset name from the geometry file path.

        """
        geo_name = geometry_file.split("/")[-1]
        geo_name = geo_name.split(".")[0]

        return geo_name
