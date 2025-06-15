import json
import os.path

import hou
import re

#TODO 1: Change import path to the relative path

class CAT_GeometryImport:
    def __init__(self, json_file, import_render, source_tag, add_displacement=False, add_extra_tex=False):
        self.stage_path = "stage/"
        self.metadata = json_file
        self.import_render = import_render
        self.source_tag = source_tag

        script_dir = os.path.dirname(__file__)
        parm_schema = os.path.join(script_dir, "parameters_schema.json")
        self.parameters_scheme =os.path.normpath(parm_schema)


        script_dir = os.path.dirname(__file__)
        texture_schema = os.path.join(script_dir, "inputs_schema.json")

        self.texture_schema = os.path.normpath(texture_schema)
        self.wrangle_code = ""
        self.add_extra_tex = add_extra_tex
        self.add_displacement = add_displacement

        # Create main usd template based on json file data
    def create_main_template(self, geometry_file):
        pass
    def create_graft_stages(self):
        graft_stages = hou.node(self.stage_path).createNode("graftstages")
        return graft_stages
    def create_sop_read(self, geometry_file, metadata, wrangle_code):
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
        prim = hou.node(self.stage_path).createNode("primitive")
        prim.parm("primpath").set("/main")
        prim.parm("primkind").set("assembly")
        return prim

    def create_material_lib(self):
        mat_lib = hou.node(self.stage_path).createNode("materiallibrary")
        mat_lib.parm("matpathprefix").set("/main/materials/")


        return mat_lib

    def create_usd_rop(self, geometry_file, metadata, source_tag):
        usd_rop = hou.node(self.stage_path).createNode("usd_rop")
        output_path = geometry_file.split("/")

        output_path = output_path[:len(output_path) - 2]

        output_path = "/".join(output_path) + "/" + "usd" + "/" + metadata[source_tag][geometry_file]["asset_name"] + ".usd"
        usd_rop.parm("lopoutput").set(output_path)
        return usd_rop

    def create_materialx_library(self, geometry_file, mat_lib):
        with open(self.parameters_scheme, "r") as scheme_file:
            scheme_read = json.load(scheme_file)
        scheme = scheme_read[self.import_render]

        mat_lib_path = hou.node(mat_lib.path())

        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)
        _materials = read[self.source_tag][geometry_file]["materials"]
        for mat in _materials:
            mat_x = mat_lib_path.createNode("subnet", mat)
            mat_x.setMaterialFlag(True)
            output = hou.node(mat_x.path() + "/suboutput1")
            mtlx_st_surface = output.createInputNode(0, "mtlxstandard_surface")
            mtlx_diplacement = output.createInputNode(1, "mtlxdisplacement")
            mat_properties = output.createInputNode(2, "kma_material_properties")

            # match = re.search("\d*({})\d*".format("Gold"), mat)
            # if match:
            #     mtlx_st_surface.parm("specular_IOR").set(0.47)

            for texture in _materials[mat]["textures"]:
                texture_node = hou.node(mat_x.path()).createNode("mtlximage")
                try:
                    input = mtlx_st_surface.inputIndex(scheme[texture])
                    mtlx_st_surface.setInput(input, texture_node)
                    texture_node.parm("file").set(_materials[mat]["textures"][texture])
                except:
                    print("texture skipped {}".format(format(_materials[mat]["textures"][texture])))
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


    def patch_texture(self, source_texture, target_text_name):
        _st_end = source_texture.split("/")[-1].split(".")[0].split("_")[-1]
        texture = source_texture.replace(_st_end, target_text_name)
        return texture

    def add_texture(self, texture, mat, mtlx_node, mtlx_input_name):
        texture_node = hou.node(mat.path()).createNode("mtlximage")
        texture_node.parm("file").set(texture)
        input_d = mtlx_node.inputIndex(mtlx_input_name)
        mtlx_node.setInput(input_d, texture_node)

    def convert_to_usd(self, remove_template=True):
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)
        geo_files = list(read.keys())
        stage = hou.node(self.stage_path)
        for file in geo_files:
            self.create_main_template(file)
            if remove_template is True:
                for child in stage.children():
                    child.destroy()

class KB_GeometryImport(CAT_GeometryImport):
    def __init__(self,  json_file, import_render, source_tag, add_displacement = True, add_extra_tex = False, execute_rop= False):
        super().__init__(json_file, import_render, source_tag,  add_displacement, add_extra_tex)
        self.wrangle_code = "string split[] = split(s@shop_materialpath, '/');\ns@path = split[-1];"
        self.source_tag = source_tag
        self.import_render = import_render
        self.execute_rop = execute_rop

    def create_main_template(self, geometry_file):
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
        self.create_materialx_library(geometry_file, mat_lib)
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



        if self.execute_rop:
            usd_rop.parm("execute").pressButton()
            sop_create.destroy()
            prim.destroy()
            mat_lib.destroy()
            graft_stages.destroy()
            assign_mat.destroy()
            usd_rop.destroy()
            print("{} converted to usd".format(geometry_file))


class MS_GeometryImport(CAT_GeometryImport):
    def __init__(self,  json_file, import_render, source_tag, add_displacment = True, add_extra_tex = False, execute_rop = False):
        super().__init__(json_file, import_render, source_tag, add_displacment, add_extra_tex)
        self.wrangle_code = "s@path = s@name;"
        self.source_tag = source_tag
        self.import_render = import_render
        self.execute_rop = execute_rop

    def create_main_template(self, geometry_file):
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
        self.create_materialx_library(geometry_file, mat_lib)
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
                    + "*"  # added to make the same material librery work with destruction
            )
            assign_mat.parm("primpattern{}".format(_materials.index(mat) + 1)).set(prim_path)
            assign_mat.parm("matspecpath{}".format(_materials.index(mat) + 1)).set(mat_path)

        transform = assign_mat.createOutputNode("xform")
        transform.parm("scale").set("0.01")
        transform.setDisplayFlag(True)
        usd_rop = self.create_usd_rop(geometry_file, read, self.source_tag)
        usd_rop.setInput(0, transform)


        if self.execute_rop:
            usd_rop.parm("execute").pressButton()
            sop_create.destroy()
            prim.destroy()
            mat_lib.destroy()
            graft_stages.destroy()
            assign_mat.destroy()
            transform.destroy()
            usd_rop.destroy()
            print("{} converted to usd".format(geometry_file))

class CAT_ExtractMaterialsData:
    def __init__(self, json_file, source_tag):
        self.metadata = json_file
        self.source_tag = source_tag

    def read_geo_file(self, node):
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
        # open json file
        with open(self.metadata, "r") as read_file:
            read = json.load(read_file)

        files = self.read_geo_file(node)
        with hou.InterruptableOperation("Performing Tasks", long_operation_name="Saving geometry data",
                                        open_interrupt_dialog=True) as op:

            for file in files:
                geometry_file =  file.parm("file").evalAsString()
                op.updateLongProgress(files.index(file) / float(len(files))), "{}/{}".format(files.index(file) + 1,len(files))

                # Getting geo name
                geo_name = self.get_geometry_name(node, geometry_file, self.source_tag)

                try:
                # Writing geomjetry file name and initializing textures dictionary
                    read[self.source_tag][geometry_file]={"asset_name": geo_name, "materials": {}}
                except:
                    read[self.source_tag] = {geometry_file: {}}
                    read[self.source_tag][geometry_file] = {"asset_name": geo_name, "materials": {}}

                # Add Thumbnail
                thumbnail = self.add_thumbnail(geometry_file)
                if thumbnail:
                    read[self.source_tag][geometry_file]["thumbnail"] = thumbnail

                # Packing geo based on material path
                pack_all = node.input(files.index(file)).createOutputNode("pack")  # this is why pack node is created twice
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
                    read[self.source_tag][geometry_file]["materials"][mat_name] = {"shop_materialpath": mat, "textures": {}}

                    for parm in shader.parms():
                        if parm.name().endswith("texture"):
                            if parm.evalAsString() != "":
                                read[self.source_tag][geometry_file]["materials"][mat_name]["textures"][parm.name()] = parm.evalAsString()

                # Pack remove
                pack_all.destroy()
            # Writing json file
            with open(self.metadata, "w") as output_file:
                json.dump(read, output_file, indent=4)

        if hou.isUIAvailable():
            if len(files) > 1:
                text = "{} assets added to metadata".format(len(files))
                user_response = hou.ui.displayMessage(
                    text)
            else:
                text = "{} asset added to metadata".format(len(files))
                user_response = hou.ui.displayMessage(
                    text)
    def get_geometry_name(self, node, geometry_file, source_tag):
        geo_name = geometry_file.split("/")[-1]
        geo_name = geo_name.split(".")[0]
        if source_tag == "MS":
            try:
                geo_name = geo_name.split("_").pop(0)
                _dir = os.path.dirname(os.path.realpath(geometry_file))
                json_file =  r"{}\{}.json".format(_dir, geo_name)
                with open(json_file, "r") as data_file:
                    read = json.load(data_file)
                geo_name = read["semanticTags"]["name"]
                geo_name.repalce("", "_")
            except:
                geo_name = node.path().split("/")[2]
        return geo_name
#TODO 2 Review this fucntion logic there should be returns
    def add_thumbnail(self, geometry_file):
        _dir = os.path.dirname(os.path.realpath(geometry_file))
        for file in os.listdir(_dir):
            if os.path.isfile(os.path.join(_dir, file)):
                match = re.search("\d*({})\d*".format("review"), file.lower())
                if match:
                    thumb_path = os.path.join(_dir, file)
                    return thumb_path









