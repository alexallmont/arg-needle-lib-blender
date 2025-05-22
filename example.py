# Generate blender render from ARG
# Example code, very much work in progress! Lots to fix and tidy here.
#
# Note bpy currently requires numpy>=1.26,<2.0
# https://projects.blender.org/blender/blender/issues/134550

import arg_needle_lib
import bpy
import math
import mathutils

HALF_PI = math.pi / 2

NODE_COLOUR = (0.5, 1.0, 0.5, 0.5)
SAMPLE_COLOUR = (0.1, 0.1, 1.0, 1.0)
EDGE_COLOUR = (0.1, 0.1, 1.0, 0.3)
RENDER_TEXT = True
RENDER_BREAKPOINT_PLANES = False
TEXT_RADIUS = 0.5
SAVE_BLENDER_FILE = True

"""
arg = arg_needle_lib.ARG(0, 100, 2)
s0 = arg.add_sample()
s1 = arg.add_sample()
arg.thread_sample([0, 20, 80], [s0, s0, s0], [3, 4, 3])
s2 = arg.add_sample()
#arg.thread_sample([0, 70, 80], [s0, s1, s1], [6, 6, 6])
arg.thread_sample([0], [s0], [6])
arg.populate_children_and_roots()

ts = arg_needle_lib.arg_to_tskit(arg)
print(ts.draw_text())
print(ts)
#for t in ts.trees():
#    for n in t.nodes():
#        print(n)

"""
import msprime
from dataclasses import dataclass

# Convenience for wrapping up test scenarios
@dataclass
class Sim:
    samples: int
    seq_len: int
    pop_size: int
    recom: float
    mu: float
    seed: int

def arg_from_sim(sim: Sim):
    ts = msprime.sim_ancestry(
        samples=sim.samples,
        recombination_rate=sim.recom,
        sequence_length=sim.seq_len,
        population_size=sim.pop_size,
        random_seed=sim.seed
    )
    arg = arg_needle_lib.tskit_to_arg(ts)
    arg_needle_lib.generate_mutations(arg, mu=sim.mu, random_seed=1234)
    arg.populate_children_and_roots()
    arg.populate_mutations_on_edges()
    return arg

sim_1000 = Sim(3, 1_000, 10_000, 2e-7, 2e-7, 1234)
arg = arg_from_sim(sim_1000)


# Compute node positions to render in blender
node_children = {}
leaf_nodes = []
current_nodes = set()
node_x_and_height = {}
max_height = 0
max_len = 0

for id in range(arg.num_nodes()):
    node = arg.node(id)
    if arg.is_leaf(id):
        node_x_and_height[id] = (len(leaf_nodes), 0)
        leaf_nodes.append(node)
        node_children[id] = []
    max_height = max(max_height, node.height)
    max_len = max(max_len, node.end)
max_width = len(leaf_nodes) - 1

GLOBAL_SCALE = 10
X_SCALE = GLOBAL_SCALE / (max_width + 1)
Y_SCALE = GLOBAL_SCALE / (max_height + 1)
LEN_SCALE = GLOBAL_SCALE * 3 / (max_len + 1)

breakpoint_positions = set()

current_nodes = set(leaf_nodes)
root_nodes = []
while current_nodes:
    next_nodes = set()
    for node in current_nodes:
        parent_edges = node.parent_edges()
        if parent_edges:
            for edge in parent_edges:
                breakpoint_positions.add(edge.start)
                breakpoint_positions.add(edge.end)
                parent_id = edge.parent.ID
                child_id = node.ID
                if parent_id in node_children:
                    node_children[parent_id].append(child_id)
                else:
                    node_children[parent_id] = [child_id]
                next_nodes.add(edge.parent)
        else:
            root_nodes.append(node)
    current_nodes = next_nodes


def recurse_get_x_and_height(node):
    if node.ID in node_x_and_height:
        return

    child_nodes = [arg.node(id) for id in node_children[node.ID]]
    for child_node in child_nodes:
        recurse_get_x_and_height(child_node)

    total_x = sum([node_x_and_height[id][0] for id in node_children[node.ID]])
    avg_x = total_x / len(node_children[node.ID])
    node_x_and_height[node.ID] = (avg_x, node.height)

for node in root_nodes:
    recurse_get_x_and_height(node)

print(node_x_and_height)


def create_flat_color_transparent_material(name, color_rgba, alpha=0.2):
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


# Clear default scene camera and cube, keep default light for now
objs = [bpy.context.scene.objects['Camera'], bpy.context.scene.objects['Cube']]
with bpy.context.temp_override(selected_objects=objs):
    bpy.ops.object.delete()

def scale_x_h(x_h):
    x = (x_h[0] - max_width / 2) * X_SCALE
    h = x_h[1] * Y_SCALE
    return x, h

for id, x_h in node_x_and_height.items():
    node = arg.node(id)
    name = f"node_{id}"
    x, h = scale_x_h(x_h)
    s = node.start * LEN_SCALE
    e = node.end * LEN_SCALE

    cList = ((x, s, h, 0), (x, e, h, 0))
    curvedata = bpy.data.curves.new(name=name, type='CURVE')
    curvedata.dimensions = '3D'

    obj = bpy.data.objects.new(name, curvedata)
    bpy.context.scene.collection.objects.link(obj)

    # add the points for the line
    polyline = curvedata.splines.new('POLY')
    polyline.points.add(len(cList)-1)
    for p, co in zip(polyline.points, cList):
        p.co = co

    node_colour = SAMPLE_COLOUR if arg.is_leaf(id) else NODE_COLOUR
    mat = create_flat_color_transparent_material(name, node_colour)
    curvedata.materials.append(mat)
    curvedata.bevel_depth = 0.05

    if RENDER_TEXT:
        bpy.ops.object.text_add(location=(x, s - TEXT_RADIUS, h), rotation=(0, 0, 0), radius=TEXT_RADIUS)
        bpy.context.object.name = f"id_{id}"
        bpy.context.object.data.body = f"{id}"

        bpy.ops.object.text_add(location=(x, e + TEXT_RADIUS, h), rotation=(0, 0, 0), radius=TEXT_RADIUS)
        bpy.context.object.name = f"height_{id}"
        bpy.context.object.data.body = f"{node.height:.3f}"


colour_tweak_scale = arg.num_nodes() * 4

def recurse_create_edges(node):
    for edge in node.parent_edges():
        x1, h1 = scale_x_h(node_x_and_height[node.ID])
        x2, h2 = scale_x_h(node_x_and_height[edge.parent.ID])
        s = edge.start * LEN_SCALE
        e = edge.end * LEN_SCALE
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
        mesh = bpy.data.meshes.new(obj_name+"Data")
        mesh.from_pydata(vtx, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(obj_name, mesh)
        bpy.context.scene.collection.objects.link(obj)

        edge_colour = [EDGE_COLOUR[i] for i in range(4)]
        mat = create_flat_color_transparent_material(obj_name, edge_colour)
        obj.data.materials.append(mat)

        recurse_create_edges(edge.parent)

for node in leaf_nodes:
    recurse_create_edges(node)

for breakpoint in breakpoint_positions:
    scale = 1.1
    x1, h1 = scale_x_h((max_width * (1 - scale), max_height * (1 - scale)))
    x2, h2 = scale_x_h((max_width * scale, max_height * scale))
    b = breakpoint * LEN_SCALE

    if RENDER_BREAKPOINT_PLANES:
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
        mesh = bpy.data.meshes.new(obj_name+"Data")
        mesh.from_pydata(vtx, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(obj_name, mesh)
        bpy.context.scene.collection.objects.link(obj)

        mat = create_flat_color_transparent_material(obj_name, (1, 0, 0, 0.05), 0.05)
        obj.data.materials.append(mat)

    if RENDER_TEXT:
        bpy.ops.object.text_add(location=(x2, b, h1 + TEXT_RADIUS), rotation=(HALF_PI, 0, HALF_PI), radius=TEXT_RADIUS)
        bpy.context.object.name = f"breakpoint_text_{breakpoint}"
        bpy.context.object.data.body = str(breakpoint)


cam = bpy.data.cameras.new("Camera")
cam.lens = 30
cam_obj = bpy.data.objects.new("Camera", cam)
cam_obj.location = (
    max_width * 3 * X_SCALE,
    -max_len * 0.3 * LEN_SCALE,
    max_height * 1.5 * Y_SCALE
)
bpy.context.scene.collection.objects.link(cam_obj)

def look_at(obj_camera, target):
    direction = target - obj_camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj_camera.rotation_euler = rot_quat.to_euler()

target = mathutils.Vector((
    0,
    max_len * 0.3 * LEN_SCALE,
    max_height * 0.3 * Y_SCALE
))
look_at(cam_obj, target)
bpy.context.scene.camera = cam_obj

if SAVE_BLENDER_FILE:
    bpy.ops.object.select_all(action='DESELECT')
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'

    bpy.ops.wm.save_as_mainfile(filepath="example.blend")

bpy.context.scene.render.filepath = "example.png"
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.image_settings.color_mode = 'RGBA'
bpy.ops.render.render(write_still=True)
