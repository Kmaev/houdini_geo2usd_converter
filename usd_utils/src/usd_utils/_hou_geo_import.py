import json
import os

import hou

"""
 Base class to import geometry and material data from JSON metadata into Houdini, 
    build a USD pipeline with geometry, materials, and optionally execute a USD ROP.

    :param json_file: Path to the JSON metadata file containing geometry and material info.
    :param import_render: Identifier for the render setup (e.g., 'KB', 'MS') used to convert textures names
    :param source_tag: Tag representing the source of metadata entries (e.g., 'MS', 'KB').
    :param add_displacement: If True, adds displacement textures to materials.
    :param add_extra_tex: If True, adds extra textures based on schema.

"""


class GeometryImport:
    def __init__(self, json_file, import_render, source_tag, add_displacement=False, add_extra_tex=False):
        self.stage_path = "stage/"
        self.metadata = json_file
        self.import_render = import_render
        self.source_tag = source_tag

        script_dir = os.path.dirname(__file__)
        parm_schema = os.path.join(script_dir, "parameters_schema.json")
        self.parameters_scheme = os.path.normpath(parm_schema)

        script_dir = os.path.dirname(__file__)
        texture_schema = os.path.join(script_dir, "inputs_schema.json")

        self.texture_schema = os.path.normpath(texture_schema)
        self.wrangle_code = ""
        self.add_extra_tex = add_extra_tex
        self.add_displacement = add_displacement

        # Create main usd template based on json file data

    def create_main_template(self, geometry_file):
        """
        Placeholder entrypoint to build the USD template for a geometry asset.
        To be overridden by subclasses.
        """
        pass

    def create_graft_stages(self):
        """
        Creates Graft Stage node
        """
        graft_stages = hou.node(self.stage_path).createNode("graftstages")
        return graft_stages

    def create_sop_read(self, geometry_file, metadata, wrangle_code):
        """
        Creates a SOP Create node. Populates it with File, Attribute Wrangle, Delete, and Output sub-nodes.
        Imports a .bgeo file and populates the corresponding parameters accordingly.
        """
        # create Sop read
        sop_create = hou.node(self.stage_path).createNode("sopcreate",
                                                          metadata[self.source_tag][geometry_file]["asset_name"])
        sop_create.parm("enable_partitionattribs").set(True)
        sop_create.parm("partitionattribs").set("path")
        sop_create.parm("enable_pathattr").set(True)
        sop_create.parm("enable_group").set(True)
        sop_create.parm("group").set("*")
        sop_create.parm("enable_grouptype").set(True)
        sop_create.parm("enable_subsetgroups").set(True)
        sop_create.parm("subsetgroups").set("*")

        # create file sop
        file_sop = hou.node(sop_create.path() + "/sopnet/create").createNode("file")
        file_sop.parm("file").set(geometry_file)

        # attrib wrangle
        attrib_wrangle = file_sop.createOutputNode("attribwrangle")
        attrib_wrangle.parm("class").set(1)
        attrib_wrangle.parm("snippet").set(wrangle_code)

        # create delete sop
        delete = attrib_wrangle.createOutputNode("attribdelete")
        delete.parm("primdel").set("shop_materialpath")

        # create output
        output_sop = delete.createOutputNode("output")

        return sop_create

    def create_prim(self):
        """
        Creates LOP Primitive node
        """
        prim = hou.node(self.stage_path).createNode("primitive")
        prim.parm("primpath").set("/main")
        prim.parm("primkind").set("assembly")
        return prim

    def create_material_lib(self):
        """
        Creates LOP Material Library node
        """
        mat_lib = hou.node(self.stage_path).createNode("materiallibrary")
        mat_lib.parm("matpathprefix").set("/main/materials/")

        return mat_lib

    def create_usd_rop(self, geometry_file, metadata, source_tag):
        """
        Creates LOP USD OUT node
        """
        usd_rop = hou.node(self.stage_path).createNode("usd_rop")
        output_path = geometry_file.split("/")

        output_path = output_path[:len(output_path) - 2]

        output_path = "/".join(output_path) + "/" + "usd" + "/" + metadata[source_tag][geometry_file][
            "asset_name"] + ".usd"
        usd_rop.parm("lopoutput").set(output_path)
        return usd_rop

    def create_materialx_shader(self, geometry_file, mat_lib):
        """
        Builds a materialx shader network inside the materiallibrary node,
        wiring textures based on parameters and texture schemas.
        """

        # Read schema to convert Mantra texture entries to MaterialX
        with open(self.parameters_scheme, "r") as scheme_file:
            scheme_read = json.load(scheme_file)
        scheme = scheme_read[self.import_render]

        mat_lib_path = hou.node(mat_lib.path())

        # Get materials metadata
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)

        _materials = read[self.source_tag][geometry_file]["materials"]

        # Create a MaterialX node for each material, generate textures, and connect everything accordingly
        for mat in _materials:
            mat_x = mat_lib_path.createNode("subnet", mat)
            mat_x.setMaterialFlag(True)
            output = hou.node(mat_x.path() + "/suboutput1")
            mtlx_st_surface = output.createInputNode(0, "mtlxstandard_surface")
            mtlx_diplacement = output.createInputNode(1, "mtlxdisplacement")
            mat_properties = output.createInputNode(2, "kma_material_properties")

            for texture in _materials[mat]["textures"]:
                texture_node = hou.node(mat_x.path()).createNode("mtlximage")
                try:
                    input = mtlx_st_surface.inputIndex(scheme[texture])
                    mtlx_st_surface.setInput(input, texture_node)
                    texture_node.parm("file").set(_materials[mat]["textures"][texture])
                except:
                    print("texture skipped {}".format(format(_materials[mat]["textures"][texture])))

            # If add extra textures set to True AO and displacement textures will be created
            if self.add_extra_tex:
                with open(self.texture_schema, "r") as tex_scheme_file:
                    tex_scheme_read = json.load(tex_scheme_file)
                tex_scheme = tex_scheme_read[self.source_tag]["surface"]
                for name in tex_scheme:
                    _tex_data = list(_materials[mat]["textures"].items())[0]
                    new_tex = self.patch_texture(_tex_data[1], name)
                    self.add_texture(new_tex, mat_x, mtlx_st_surface, tex_scheme[name])
            if self.add_displacement:
                with open(self.texture_schema, "r") as tex_scheme_file:
                    tex_scheme_read = json.load(tex_scheme_file)
                tex_scheme = tex_scheme_read[self.source_tag]["displacement"]
                for name in tex_scheme:
                    _tex_data = list(_materials[mat]["textures"].items())[0]
                    new_tex = self.patch_texture(_tex_data[1], name)
                    self.add_texture(new_tex, mat_x, mtlx_diplacement, tex_scheme[name])
                    mtlx_diplacement.parm("scale").set(0.01)
            mat_x.layoutChildren()
        mat_lib.layoutChildren()

        # Texture name editing

    def patch_texture(self, source_texture, target_text_name):
        """
        Generates a new texture filename by swapping the suffix.
        """
        _st_end = source_texture.split("/")[-1].split(".")[0].split("_")[-1]
        texture = source_texture.replace(_st_end, target_text_name)
        return texture

    def add_texture(self, texture, mat, mtlx_node, mtlx_input_name):
        """
        Adds a texture node to a materialx network and connects it.
        """
        texture_node = hou.node(mat.path()).createNode("mtlximage")
        texture_node.parm("file").set(texture)
        input_d = mtlx_node.inputIndex(mtlx_input_name)
        mtlx_node.setInput(input_d, texture_node)

    def convert_to_usd(self, remove_template=True):
        """
        Iterates over metadata entries and builds USD templates for all geometry,
        optionally cleaning up the stage after each.
        """
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)
        geo_files = list(read.keys())
        stage = hou.node(self.stage_path)
        for file in geo_files:
            self.create_main_template(file)
            if remove_template is True:
                for child in stage.children():
                    child.destroy()
