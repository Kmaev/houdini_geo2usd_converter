import json
from importlib import reload

import hou

from usd_utils import _hou_geo_import

reload(_hou_geo_import)

"""
 Geometry import class for KitBash library that builds a USD stage from metadata,
    assigns materials based on texture data, and optionally executes a USD export.

    :param json_file: Path to the JSON metadata file.
    :param import_render: Identifier which render setup to use.
    :param source_tag: Metadata library tag used to select assets.
    :param add_displacement: If True, includes displacement textures.
    :param add_extra_tex: If True, includes additional textures based on schema.
    :param execute_rop: If True, executes the USD ROP after building.
"""


class KBGeometryImport(_hou_geo_import.GeometryImport):
    def __init__(self, json_file, import_render, source_tag, add_displacement=True, add_extra_tex=False,
                 execute_rop=False):
        super().__init__(json_file, import_render, source_tag, add_displacement, add_extra_tex)
        self.wrangle_code = "string split[] = split(s@shop_materialpath, '/');\ns@path = split[-1];"
        self.source_tag = source_tag
        self.import_render = import_render
        self.execute_rop = execute_rop

    def create_main_template(self, geometry_file):
        """
         Builds the USD stage for a single geometry asset:
            Reads metadata from JSON.
            Sets up SOP read, prim, graft stages, material library, and assignmaterial.
            Optionally executes and cleans up the network.

        """
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)

        sop_create = self.create_sop_read(geometry_file, read, self.wrangle_code)
        prim = self.create_prim()

        # Create graft stages
        graft_stages = self.create_graft_stages()
        graft_stages.setInput(0, prim)
        graft_stages.setNextInput(sop_create)

        mat_lib = self.create_material_lib()
        mat_lib.setInput(0, graft_stages)
        self.create_materialx_shader(geometry_file, mat_lib)
        assign_mat = mat_lib.createOutputNode("assignmaterial")

        _materials = list(read[self.source_tag][geometry_file]["materials"].keys())
        assign_mat.parm("nummaterials").set(len(_materials))

        for mat in _materials:
            mat_path = ("/main/"
                        + "materials"
                        + "/"
                        + mat
                        )
            prim_path = (
                    prim.parm("primpath").evalAsString()
                    + "/"
                    + sop_create.name()
                    + "/"
                    + sop_create.name()
                    + "/"
                    + mat
                    + "*"  # added to make the same material library work with destruction
            )

            assign_mat.parm("primpattern{}".format(_materials.index(mat) + 1)).set(prim_path)
            assign_mat.parm("matspecpath{}".format(_materials.index(mat) + 1)).set(mat_path)
            assign_mat.setDisplayFlag(True)

        usd_rop = self.create_usd_rop(geometry_file, read, self.source_tag)
        usd_rop.setInput(0, assign_mat)
        """
        After each iteration, the network is destroyed if the user only wants to convert .bgeo files 
        to USD and save them to disk without immediately loading them into Houdini.
        """

        if self.execute_rop:
            usd_rop.parm("execute").pressButton()
            sop_create.destroy()
            prim.destroy()
            mat_lib.destroy()
            graft_stages.destroy()
            assign_mat.destroy()
            usd_rop.destroy()
            print("{} converted to usd".format(geometry_file))
