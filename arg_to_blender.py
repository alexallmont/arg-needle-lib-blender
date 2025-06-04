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
        render_scale: RenderScale,
        png_out_file = None,
        blender_out_file = None,
        render_text = True,
        render_breakpoints = False,
        text_scale = 0.5,
        camera_location = None,
        camera_look_at = None
    ):
        self.render_info = arg_render_info
        self.render_scale = render_scale

        self._clear_default_scene_objects()
        self._add_nodes_to_scene(render_text, text_scale)
        self._add_edges_to_scene()

        # FIXME reinstate breakpoint rendering
        # if render_breakpoints:
        #     self._add_breakpoints_to_scene(render_text, text_scale)

        self._create_camera(camera_location, camera_look_at)
        if blender_out_file:
            self._save_blender_file(blender_out_file)

        if png_out_file:
            self._save_render_image(png_out_file)

    def _add_nodes_to_scene(self, render_text, text_scale):
        ri = self.render_info
        rs = self.render_scale

        for node in ri.nodes:
            obj_name = f"node_{node.id}"
            x, h = rs.scale_xh(node.x_pos, node.height)
            s = rs.scale_len(node.y_start)
            e = rs.scale_len(node.y_end)

            line_point_list = ((x, s, h, 0), (x, e, h, 0))
            curvedata = bpy.data.curves.new(name=obj_name, type='CURVE')
            curvedata.dimensions = '3D'

            obj = bpy.data.objects.new(obj_name, curvedata)
            bpy.context.scene.collection.objects.link(obj)

            # add the points for the line
            polyline = curvedata.splines.new('POLY')
            polyline.points.add(len(line_point_list) - 1)
            for p, co in zip(polyline.points, line_point_list):
                p.co = co

            node_colour = SAMPLE_COLOUR if ri.node_is_leaf(node) else NODE_COLOUR
            mat = self._create_flat_color_transparent_material(obj_name, node_colour)
            curvedata.materials.append(mat)
            curvedata.bevel_depth = 0.05

            if render_text:
                bpy.ops.object.text_add(location=(x, s - text_scale, h), rotation=(0, 0, 0), radius=text_scale)
                bpy.context.object.name = f"id_{node.id}"
                bpy.context.object.data.body = f"{node.id}"

                bpy.ops.object.text_add(location=(x, e + text_scale, h), rotation=(0, 0, 0), radius=text_scale)
                bpy.context.object.name = f"height_{node.id}"
                bpy.context.object.data.body = f"{node.height:.3f}"

    def _add_edges_to_scene(self):
        ri = self.render_info
        rs = self.render_scale

        for edge in ri.edges:
            node = ri.node_by_id[edge.child_id]
            parent = ri.node_by_id[edge.parent_id]
            x1, h1 = rs.scale_xh(node.x_pos, node.height)
            x2, h2 = rs.scale_xh(parent.x_pos, parent.height)
            s = rs.scale_len(edge.y_start)
            e = rs.scale_len(edge.y_end)
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

            edge_colour = [EDGE_COLOUR[i] for i in range(4)]
            edge_colour[0] += node.height / rs.max_height
            mat = self._create_flat_color_transparent_material(obj_name, edge_colour)
            obj.data.materials.append(mat)

    def _add_breakpoints_to_scene(self, render_text, text_scale):
        ri = self.render_info
        scale = 1.1
        x1, h1 = ri.scale_x_h((ri.max_width * (1 - scale), ri.max_height * (1 - scale)))
        x2, h2 = ri.scale_x_h((ri.max_width * scale, ri.max_height * scale))
        b = breakpoint * ri.len_scale

        vtx = [
            (x1, b, h1),
            (x2, b, h1),
            (x2, b, h2),
            (x1, b, h2),
        ]
        faces = [
            (0, 1, 2),
            (2, 3, 0),
        ]

        obj_name = f"breakpoint_{breakpoint}"
        mesh = bpy.data.meshes.new(f"{obj_name}_mesh")
        mesh.from_pydata(vtx, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(obj_name, mesh)
        bpy.context.scene.collection.objects.link(obj)

        mat = self._create_flat_color_transparent_material(obj_name, (1, 0, 0, 0.05), 0.05)
        obj.data.materials.append(mat)

        if render_text:
            bpy.ops.object.text_add(location=(x2, b, h1 + text_scale), rotation=(HALF_PI, 0, HALF_PI), radius=text_scale)
            bpy.context.object.name = f"breakpoint_text_{breakpoint}"
            bpy.context.object.data.body = str(breakpoint)

    def _create_camera(self, camera_location, camera_look_at):
        ri = self.render_info
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
    def _create_flat_color_transparent_material(name, color_rgba, alpha=0.2):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        mat.blend_method = 'BLEND'
        mat.diffuse_color = color_rgba
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Nodes
        emission = nodes.new("ShaderNodeEmission")
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        output = nodes.new("ShaderNodeOutputMaterial")

        # Set color and alpha
        emission.inputs["Color"].default_value = color_rgba
        emission.inputs["Strength"].default_value = 1.0
        mix.inputs["Fac"].default_value = alpha

        # Connect
        links.new(transparent.outputs["BSDF"], mix.inputs[1])
        links.new(emission.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])

        return mat
