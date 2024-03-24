import os
import hou


scheme = {
    "basecolor_texture": "base_color",
    "rough_texture": "specular_color",
    "metallic_texture": "metalness",
    "opaccolor_texture": "opacity",
    "baseNormal_texture": "normal",
}


class KitBashGeometryImport:
    def __init__(self):
        self.stage_path = "stage/"
        pass

    # gather materials from geometry

    def get_material_data(self, node):

        pack_all = node.createOutputNode("pack")  # thsi is why pack node is created twice
        pack_all.parm("packbyname").set(True)
        pack_all.parm("nameattribute").set("shop_materialpath")

        pack_all.parm("transfer_attributes").set("shop_materialpath")
        geo = pack_all.geometry()
        materials = []
        for mat in geo.primStringAttribValues("shop_materialpath"):
            materials.append(mat)
        # print(materials)
        return materials

    def create_materialx(self, mat, mat_lib):
        shader = hou.node(mat.path() + "/principledshader1")
        # print(shader.parm("basecolor_texture").evalAsString())
        # parms = [parm for parm in shader.parms() if (parm.name().endswith("texture"))]
        parms = []
        for parm in shader.parms():
            if parm.name().endswith("texture"):
                if parm.evalAsString() != "":
                    parms.append(parm)

        mat_lib_path = hou.node(mat_lib.path())
        mat_x = mat_lib_path.createNode("subnet", mat.name())
        mat_x.setMaterialFlag(True)
        output = hou.node(mat_x.path() + "/suboutput1")
        mtlx_st_surface = output.createInputNode(0, "mtlxstandard_surface")

        mtlx_diplacement = output.createInputNode(1, "mtlxdisplacement")

        mat_properties = output.createInputNode(2, "kma_material_properties")

        for parm in parms:
            texture = hou.node(mat_x.path()).createNode("mtlximage")
            try:
                input = mtlx_st_surface.inputIndex(scheme[parm.name()])

                mtlx_st_surface.setInput(input, texture)
                texture.parm("file").set(parm.evalAsString())

            except:
                print("texture skiped {}".format(parm.evalAsString()))
        mat_x.layoutChildren()

    def create_maretial_library(self, stage_path):
        mat_lib = hou.node(stage_path).createNode("materiallibrary")
        return mat_lib

    def build_materialx_library(self, node):

        mat_lib = self.create_maretial_library(self.stage_path)

        materials = self.get_material_data(node)
        for mat in materials:
            mat = hou.node(mat)

            self.create_materialx(mat, mat_lib)
        mat_lib.layoutChildren()
        return mat_lib

    def import_geo(self, node):
        geo = self.read_geo_file(node)
        geo = geo.split("/")[-1]
        geo = geo.split(".")[0]
        print(geo)

        sop_import = hou.node(self.stage_path).createNode("sopimport", geo)  # temp find better way to source name
        sop_import.parm("enable_partitionattribs").set(True)
        sop_import.parm("partitionattribs").set("shop_materialpath")
        sop_import.parm("soppath").set(node.path())
        sop_import.parm("enable_pathattr").set(True)

        prim = hou.node(self.stage_path).createNode("primitive")
        prim.parm("primpath").set("/main")
        prim.parm("primkind").set("assembly")

        mat_lib = self.build_materialx_library(node)

        graft_stages = hou.node(self.stage_path).createNode("graftstages")

        graft_stages.setInput(0, prim)
        graft_stages.setNextInput(sop_import)

        graft_stages.setNextInput(mat_lib)

        materials = self.get_material_data(node)
        assign_mat = graft_stages.createOutputNode("assignmaterial")
        assign_mat.parm("nummaterials").set(len(materials))
        # mat_path should be in for loop

        for mat in materials:
            mat_path = (
                prim.parm("primpath").evalAsString()
                + "/"
                + mat_lib.name()
                + "/"
                + "materials/"
                + "/"
                + mat.split("/")[-1]
            )
            prim_path = (
                prim.parm("primpath").evalAsString()
                + "/"
                + geo
                + "/"
                + geo
                + "/mesh_0/shop_materialpath_"
                + mat.replace("/", "_")
            )
            assign_mat.parm("primpattern{}".format(materials.index(mat) + 1)).set(prim_path)
            assign_mat.parm("matspecpath{}".format(materials.index(mat) + 1)).set(mat_path)
            print(mat_path)

    def read_geo_file(self, node):
        queue = [node]
        while len(queue) > 0:
            current = queue.pop(0)
            if current.type().name() == "file":  # could be added another option to read from different types of file
                geo = current.parm("file").evalAsString()

                return geo
            for node in current.inputs():
                queue.append(node)
