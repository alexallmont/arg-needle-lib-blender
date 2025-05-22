import bpy
import math
import mathutils

HALF_PI = math.pi / 2
NODE_COLOUR = (0.5, 1.0, 0.5, 0.5)
SAMPLE_COLOUR = (0.1, 0.1, 1.0, 1.0)
EDGE_COLOUR = (0.1, 0.1, 1.0, 0.3)

class ArgToBlender:
    def __init__(
        self,
        arg,
        png_out_file = None,
        blender_out_file = None,
        render_text = True,
        render_breakpoints = False,
        global_scale = 10,
        text_scale = 0.5
    ):
        self.render_info = ArgRenderInfo(arg, global_scale)

        self._clear_default_scene_objects()
        self._add_arg_nodes_to_scene(render_text, text_scale)

        for node in self.render_info.leaf_nodes:
            self._recurse_add_arg_edges_to_scene(node)

        if render_breakpoints:
            self._add_breakpoints_to_scene(render_text, text_scale)

        self._create_camera()
        if blender_out_file:
            self._save_blender_file(blender_out_file)

        if png_out_file:
            self._save_render_image(png_out_file)

    def _add_arg_nodes_to_scene(self, render_text, text_scale):
        ri = self.render_info
        for id, x_h in ri.node_x_and_height.items():
            node = ri.arg.node(id)
            obj_name = f"node_{id}"
            x, h = ri.scale_x_h(x_h)
            s = node.start * ri.len_scale
            e = node.end * ri.len_scale

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

            node_colour = SAMPLE_COLOUR if ri.arg.is_leaf(id) else NODE_COLOUR
            mat = self._create_flat_color_transparent_material(obj_name, node_colour)
            curvedata.materials.append(mat)
            curvedata.bevel_depth = 0.05

            if render_text:
                bpy.ops.object.text_add(location=(x, s - text_scale, h), rotation=(0, 0, 0), radius=text_scale)
                bpy.context.object.name = f"id_{id}"
                bpy.context.object.data.body = f"{id}"

                bpy.ops.object.text_add(location=(x, e + text_scale, h), rotation=(0, 0, 0), radius=text_scale)
                bpy.context.object.name = f"height_{id}"
                bpy.context.object.data.body = f"{node.height:.3f}"

    def _recurse_add_arg_edges_to_scene(self, node):
        ri = self.render_info
        for edge in node.parent_edges():
            x1, h1 = ri.scale_x_h(ri.node_x_and_height[node.ID])
            x2, h2 = ri.scale_x_h(ri.node_x_and_height[edge.parent.ID])
            s = edge.start * ri.len_scale
            e = edge.end * ri.len_scale
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
            obj_name = f"edge_{node.ID}_{edge.parent.ID}"
            mesh = bpy.data.meshes.new(f"{obj_name}_mesh")
            mesh.from_pydata(vtx, [], faces)
            mesh.update()
            obj = bpy.data.objects.new(obj_name, mesh)
            bpy.context.scene.collection.objects.link(obj)

            edge_colour = [EDGE_COLOUR[i] for i in range(4)]
            edge_colour[0] += node.height / ri.max_height
            mat = self._create_flat_color_transparent_material(obj_name, edge_colour)
            obj.data.materials.append(mat)

            self._recurse_add_arg_edges_to_scene(edge.parent)

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

    def _create_camera(self):
        ri = self.render_info
        cam = bpy.data.cameras.new("Camera")
        cam.lens = 30
        cam_obj = bpy.data.objects.new("Camera", cam)
        cam_obj.location = (
            ri.max_width * 3 * ri.x_scale,
            -ri.max_len * 0.3 * ri.len_scale,
            ri.max_height * 1.5 * ri.height_scale
        )
        bpy.context.scene.collection.objects.link(cam_obj)

        target = mathutils.Vector((
            0,
            ri.max_len * 0.3 * ri.len_scale,
            ri.max_height * 0.3 * ri.height_scale
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
        # Clear any meshes and cameras, keep lights
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_by_type(type == 'MESH')
        bpy.ops.object.select_by_type(type == 'CAMERA')
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


class ArgRenderInfo:
    def __init__(
        self,
        arg,
        global_scale,
    ):
        self.arg = arg
        self._compute_leaves_and_extents(global_scale)

        self._compute_roots_and_children()
        for node in self.root_nodes:
            self._recurse_get_x_and_height(node)

    def scale_x_h(self, x_h):
        x = (x_h[0] - self.max_width / 2) * self.x_scale
        h = x_h[1] * self.height_scale
        return x, h

    def _compute_leaves_and_extents(self, global_scale):
        self.node_x_and_height = {}
        self.node_children = {}
        self.leaf_nodes = []
        self.root_nodes = []

        max_height = 0
        max_len = 0
        for id in range(self.arg.num_nodes()):
            node = self.arg.node(id)
            if self.arg.is_leaf(id):
                self.node_x_and_height[id] = (len(self.leaf_nodes), 0)
                self.leaf_nodes.append(node)
                self.node_children[id] = []
            max_height = max(max_height, node.height)
            max_len = max(max_len, node.end)

        self.max_height = max_height
        self.max_len = max_len
        self.max_width = len(self.leaf_nodes) - 1

        self.x_scale = global_scale / (self.max_width + 1)
        self.height_scale = global_scale / (self.max_height + 1)
        self.len_scale = global_scale * 3 / (self.max_len + 1)

    def _compute_roots_and_children(self):
        self.root_nodes = []
        self.breakpoint_positions = set()

        current_nodes = set(self.leaf_nodes)
        while current_nodes:
            next_nodes = set()
            for node in current_nodes:
                parent_edges = node.parent_edges()
                if parent_edges:
                    for edge in parent_edges:
                        self.breakpoint_positions.add(edge.start)
                        self.breakpoint_positions.add(edge.end)
                        parent_id = edge.parent.ID
                        child_id = node.ID
                        if parent_id in self.node_children:
                            self.node_children[parent_id].append(child_id)
                        else:
                            self.node_children[parent_id] = [child_id]
                        next_nodes.add(edge.parent)
                else:
                    self.root_nodes.append(node)
            current_nodes = next_nodes

    def _recurse_get_x_and_height(self, node):
        if node.ID in self.node_x_and_height:
            return

        child_nodes = [self.arg.node(id) for id in self.node_children[node.ID]]
        for child_node in child_nodes:
            self._recurse_get_x_and_height(child_node)

        total_x = sum([self.node_x_and_height[id][0] for id in self.node_children[node.ID]])
        avg_x = total_x / len(self.node_children[node.ID])
        self.node_x_and_height[node.ID] = (avg_x, node.height)
