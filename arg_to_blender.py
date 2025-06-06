import bpy
import math
import mathutils

from arg_render_info import RenderScale, ArgRenderInfo

HALF_PI = math.pi / 2
NODE_COLOUR = (0.5, 1.0, 0.5, 0.5)
SAMPLE_COLOUR = (0.1, 0.1, 1.0, 1.0)
EDGE_COLOUR = (0.1, 0.1, 1.0, 0.3)

class ArgToBlender:
    def __init__(
        self,
        arg_render_info: ArgRenderInfo,
        render_scale = None,
        png_out_file = None,
        blender_out_file = None,
        render_text = True,
        render_breakpoints = True,
        text_scale = 0.5,
        camera_location=(-12, -8, 8),
        camera_look_at=(-2, 6, 3)
    ):
        self.render_info = arg_render_info
        if not render_scale:
            render_scale = RenderScale(arg_render_info)
        self.render_scale = render_scale

        self._clear_default_scene_objects()
        self._create_materials()
        self._add_nodes_to_scene(render_text, text_scale)
        self._add_edges_to_scene()

        if render_text and render_breakpoints:
            self._add_breakpoints_text_to_scene(text_scale)

        self._create_camera(camera_location, camera_look_at)
        if blender_out_file:
            self._save_blender_file(blender_out_file)

        if png_out_file:
            self._save_render_image(png_out_file)

    def _create_materials(self):
        self.mat_leaf_node = self._create_material_diffuse("leaf", 0.2, 0.2, 1, 1)
        self.mat_root_node = self._create_material_diffuse("root", 1, 0.2, 0.2, 1)
        self.mat_internal_node = self._create_material_diffuse("internal", 0.2, 1, 0.2, 1)
        self.mat_edge = self._create_material_diffuse("edge", 1, 1, 1, 0.1)
        self.mat_outline = self._create_material_diffuse("outline", 0, 0, 0, 0.5)
        self.mat_breakpoint = self._create_material_diffuse("breakpoint", 0.5, 0.5, 0.5, 1)

    def _add_line(self, obj_name, radius, mat, x1, y1, z1, x2, y2, z2):
        line_point_list = ((x1, y1, z1, 0), (x2, y2, z2, 0))
        curvedata = bpy.data.curves.new(name=obj_name, type='CURVE')
        curvedata.dimensions = '3D'

        obj = bpy.data.objects.new(obj_name, curvedata)
        bpy.context.scene.collection.objects.link(obj)

        # add the points for the line
        polyline = curvedata.splines.new('POLY')
        polyline.points.add(len(line_point_list) - 1)
        for p, co in zip(polyline.points, line_point_list):
            p.co = co

        curvedata.materials.append(mat)
        curvedata.bevel_depth = radius

    def _add_nodes_to_scene(self, render_text, text_scale):
        ri = self.render_info
        rs = self.render_scale

        for node in ri.nodes:
            obj_name = f"node_{node.id}"
            x, h = rs.scale_xh(node.x_pos, node.height)
            s = rs.scale_len(node.start)
            e = rs.scale_len(node.end)

            if ri.node_is_leaf(node):
                mat = self.mat_leaf_node
            elif ri.node_is_root(node):
                mat = self.mat_root_node
            else:
                mat = self.mat_internal_node
            self._add_line(obj_name, 0.05, mat, x, s, h, x, e, h)

            if render_text:
                bpy.ops.object.text_add(
                    location=(x, s - 0.1, h - 0.5),
                    rotation=(HALF_PI, 0, 0),
                    radius=text_scale
                )
                bpy.context.object.name = f"id_{node.id}"
                bpy.context.object.data.body = f"{node.id}"
                bpy.context.object.data.materials.append(mat)

                # FIXME reinstate optional height rendering
                # bpy.ops.object.text_add(location=(x, e + text_scale, h), rotation=(0, 0, 0), radius=text_scale)
                # bpy.context.object.name = f"height_{node.id}"
                # bpy.context.object.data.body = f"{node.height:.3f}"

    def _add_edges_to_scene(self):
        ri = self.render_info
        rs = self.render_scale

        for edge in ri.edges:
            node = ri.node_by_id[edge.child_id]
            parent = ri.node_by_id[edge.parent_id]
            x1, h1 = rs.scale_xh(node.x_pos, node.height)
            x2, h2 = rs.scale_xh(parent.x_pos, parent.height)
            s = rs.scale_len(edge.start)
            e = rs.scale_len(edge.end)
            vtx = [
                (x1, s, h1),
                (x1, e, h1),
                (x2, e, h2),
                (x2, s, h2),
            ]
            faces = [
                (0, 1, 2),
                (2, 3, 0),
            ]
            obj_name = f"edge_{node.id}_{edge.parent_id}"
            mesh = bpy.data.meshes.new(f"{obj_name}_mesh")
            mesh.from_pydata(vtx, [], faces)
            mesh.update()
            obj = bpy.data.objects.new(obj_name, mesh)
            bpy.context.scene.collection.objects.link(obj)

            mat = self.mat_edge
            obj.data.materials.append(mat)

            self._add_line(obj_name, 0.01, self.mat_outline, x1, s, h1, x2, s, h2)
            self._add_line(obj_name, 0.01, self.mat_outline, x1, e, h1, x2, e, h2)

    def _add_breakpoints_text_to_scene(self, text_scale):
        ri = self.render_info
        rs = self.render_scale
        for breakpoint in ri.breakpoint_positions:
            x, h, l = rs.scale_xhl(0, 0, breakpoint)

            bpy.ops.object.text_add(
                location=(x - 0.2, l + 0.5, h - 0.5),
                rotation=(HALF_PI, 0, -HALF_PI),
                radius=text_scale
            )
            bpy.context.object.name = f"breakpoint_text_{breakpoint}"
            bpy.context.object.data.body = str(breakpoint)
            bpy.context.object.data.materials.append(self.mat_breakpoint)

    def _create_camera(self, camera_location, camera_look_at):
        rs = self.render_scale

        cam = bpy.data.cameras.new("Camera")
        cam.lens = 30
        cam_obj = bpy.data.objects.new("Camera", cam)
        cam_obj.location = camera_location or (
            rs.max_width * 3 * rs.x_scale,
            -rs.max_len * 0.3 * rs.len_scale,
            rs.max_height * 1.5 * rs.height_scale
        )
        bpy.context.scene.collection.objects.link(cam_obj)

        target = mathutils.Vector(camera_look_at or (
            0,
            rs.max_len * 0.3 * rs.len_scale,
            rs.max_height * 0.3 * rs.height_scale
        ))
        direction = target - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()
        bpy.context.scene.camera = cam_obj

    @staticmethod
    def _save_blender_file(filename):
        bpy.ops.object.select_all(action='DESELECT')
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'

        bpy.ops.wm.save_as_mainfile(filepath=filename)

    @staticmethod
    def _save_render_image(filename):
        bpy.context.scene.render.filepath = filename
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        bpy.ops.render.render(write_still=True)

    @staticmethod
    def _clear_default_scene_objects():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    @staticmethod
    def _create_material_diffuse(name, r, g, b, a):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        mat.blend_method = 'BLEND'
        mat.diffuse_color = (r, g, b, 1)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()
        emission = nodes.new("ShaderNodeEmission")
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        output = nodes.new("ShaderNodeOutputMaterial")

        # Set color and alpha
        emission.inputs["Color"].default_value = (r, g, b, 1)
        emission.inputs["Strength"].default_value = 1.0
        mix.inputs["Fac"].default_value = a

        # Connect
        links.new(transparent.outputs["BSDF"], mix.inputs[1])
        links.new(emission.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])

        return mat
