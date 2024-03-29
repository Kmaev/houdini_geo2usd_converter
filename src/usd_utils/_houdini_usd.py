import os
import hou
import json
import sys


scheme = {
    "basecolor_texture": "base_color",
    "rough_texture": "specular_roughness",
    "metallic_texture": "metalness",
    "opaccolor_texture": "opacity",

    "emitcolor_texture" : "emission_color"
}


class CAT_GeometryImport:
    def __init__(self, json_file, import_source):
        self.stage_path = "stage/"
        self.metadata  = json_file
        self.import_source = import_source
        self.scheme = r"E:\dev\cat\src\usd_utils\mat_scheme.json"

        pass

    # gather materials from geometry
    def read_geo_file(self, node):
        queue = [node]
        while len(queue) > 0:
            current = queue.pop(0)
            if current.type().name() == "file":  # could be added another option to read from different types of file
                geo = current.parm("file").evalAsString()

                return geo
            for node in current.inputs():
                queue.append(node)
    def get_geometry_data(self, node):
        #open json file
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)


        geometry_file = self.read_geo_file(node)


        # Getting geo name
        geo_name = geometry_file.split("/")[-1]
        geo_name = geo_name.split(".")[0]

        # Writing geomjetry file name and initializing textures dictionary
        read[geometry_file] = {"asset_name": geo_name, "materials": {}}

        # Packing geo based on material path
        pack_all = node.createOutputNode("pack")  # thsi is why pack node is created twice
        pack_all.parm("packbyname").set(True)
        pack_all.parm("nameattribute").set("shop_materialpath")
        pack_all.parm("transfer_attributes").set("shop_materialpath")
        hou_geo = pack_all.geometry()

        # Getting textures data
        for mat in hou_geo.primStringAttribValues("shop_materialpath"):
            shader = hou.node(mat + "/principledshader1")


            mat_name = mat.split("/")[-1]
            read[geometry_file]["materials"][mat_name]= {"shop_materialpath": mat, "textures" : {}}


            for parm in shader.parms():
                if parm.name().endswith("texture"):
                    if parm.evalAsString() != "":
                        read[geometry_file]["materials"][mat_name]["textures"][parm.name()] = parm.evalAsString()

        # Writing json file
        with open(self.metadata, "w") as output_file:
            json.dump(read, output_file, indent=4)

        # Pack remove
        pack_all.destroy()


    def create_main_template(self, geometry_file):
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)

        # Create sop lop
        sop_create = hou.node(self.stage_path).createNode("sopcreate", read[geometry_file]["asset_name"])  # change hardcoded name
        sop_create.parm("enable_partitionattribs").set(True)
        sop_create.parm("partitionattribs").set("path")
        sop_create.parm("enable_pathattr").set(True)
        sop_create.parm("enable_group").set(True)
        sop_create.parm("group").set("*")
        sop_create.parm("enable_grouptype").set(True)
        sop_create.parm("enable_subsetgroups").set(True)
        sop_create.parm("subsetgroups").set("*")
        # file sop

        file_sop = hou.node(sop_create.path() + "/sopnet/create").createNode("file")
        file_sop.parm("file").set(geometry_file)

        # attrib wrangle
        attrib_wrangle = file_sop.createOutputNode("attribwrangle")
        attrib_wrangle.parm("class").set(1)
        attrib_wrangle.parm("snippet").set(
            'string split[] = split(s@shop_materialpath, "/"); \n s@path = split[-1];')

        delete = attrib_wrangle.createOutputNode("attribdelete")
        delete.parm("primdel").set("shop_materialpath")



        # output
        output_sop = delete.createOutputNode("output")


        prim = hou.node(self.stage_path).createNode("primitive")
        prim.parm("primpath").set("/main")
        prim.parm("primkind").set("assembly")

        graft_stages = hou.node(self.stage_path).createNode("graftstages")

        graft_stages.setInput(0, prim)
        graft_stages.setNextInput(sop_create)
        mat_lib = hou.node(self.stage_path).createNode("materiallibrary")
        mat_lib.parm("matpathprefix").set("/main/materials/")
        mat_lib.setInput(0, graft_stages)


        assign_mat = mat_lib.createOutputNode("assignmaterial")

        self.create_materialx_library(geometry_file, mat_lib)

        _materials = list(read[geometry_file]["materials"].keys())
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
                    + "*" # added to make the same material librery work with destruction
            )
            assign_mat.parm("primpattern{}".format(_materials.index(mat) + 1)).set(prim_path)
            assign_mat.parm("matspecpath{}".format(_materials.index(mat) + 1)).set(mat_path)

        usd_rop = assign_mat.createOutputNode("usd_rop")
        output_path = geometry_file.split("/")
        output_path = output_path[:len(output_path) -2]
        output_path = "/".join(output_path) + "/" +"usd" + "/" + read[geometry_file]["asset_name"] + ".usd"
        usd_rop.parm("lopoutput").set(output_path)

        usd_rop.parm("execute").pressButton()



    def create_materialx_library(self, geometry_file, mat_lib):
        with open(self.scheme, "r") as scheme_file:
            scheme_read = json.load(scheme_file)
        scheme = scheme_read[self.import_source]

        mat_lib_path = hou.node(mat_lib.path())
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)
        _materials = read[geometry_file]["materials"]
        for mat in _materials:
            mat_x = mat_lib_path.createNode("subnet",mat)
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
            # TODO: find a way to batch better the textures that are missing oin mantra
            displ = _materials[mat]["textures"]["basecolor_texture"].replace("basecolor", "height")
            texture_node = hou.node(mat_x.path()).createNode("mtlximage")
            texture_node.parm("file").set(displ)
            input_d = mtlx_diplacement.inputIndex("displacement")
            mtlx_diplacement.setInput(input_d, texture_node)
            mtlx_diplacement.parm("scale").set(0.01)


            ao = _materials[mat]["textures"]["basecolor_texture"].replace("basecolor", "ao")
            texture_node = hou.node(mat_x.path()).createNode("mtlximage")
            texture_node.parm("file").set(ao)
            input_ao = mtlx_st_surface.inputIndex("specular_color")
            mtlx_st_surface.setInput(input_ao, texture_node)
            mat_x.layoutChildren()


    def convert_to_usd(self, remove_template = True):
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)
        geo_files = list(read.keys())
        stage = hou.node(self.stage_path)

        for file in geo_files:
            self.create_main_template(file)
            if remove_template is True:
                for child in stage.children():
                    child.destroy()




