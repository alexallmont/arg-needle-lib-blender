# Generate blender render from ARG
# Example code, very much work in progress! Lots to fix and tidy here.
#
# Note bpy currently requires numpy>=1.26,<2.0
# https://projects.blender.org/blender/blender/issues/134550

import arg_needle_lib
import bpy
import msprime
import math

from dataclasses import dataclass

X_SCALE = 8
Y_SCALE = 0.001
LEN_SCALE = 0.1
NODE_COLOUR = (0.5, 1.0, 0.5, 0.5)
SAMPLE_COLOUR = (0.1, 0.1, 1.0, 1.0)
EDGE_COLOUR = (0.1, 0.1, 1.0, 0.3)
HALF_PI = math.pi / 2
SHOW_TEXT = True

"""
arg = arg_needle_lib.ARG(0, 100, 3)
arg.add_sample()
arg.add_sample()
arg.thread_sample([0], [0], [5])
arg.add_sample()
arg.thread_sample([0], [0], [3])
arg.populate_children_and_roots()

print(arg_needle_lib.arg_to_tskit(arg).draw_text())
"""

# Convenience for wrapping up test scenarios
@dataclass
class Sim:
    samples: int
    seq_len: int
    pop_size: int
    recom: float
    mu: float

def arg_from_sim(sim: Sim):
    ts = msprime.sim_ancestry(
        samples=sim.samples,
        recombination_rate=sim.recom,
        sequence_length=sim.seq_len,
        population_size=sim.pop_size,
        random_seed=1234
    )
    arg = arg_needle_lib.tskit_to_arg(ts)
    arg_needle_lib.generate_mutations(arg, mu=sim.mu, random_seed=1234)
    arg.populate_children_and_roots()
    arg.populate_mutations_on_edges()
    return arg

sim_1000 = Sim(3, 1_000, 10_000, 2e-7, 2e-7)
arg = arg_from_sim(sim_1000)

node_children = {}
leaf_nodes = []
current_nodes = set()
node_x_and_height = {}
max_width = 0


# Compute node positions to render in blender

for id in range(arg.num_nodes()):
    node = arg.node(id)
    if arg.is_leaf(id):
        leaf_nodes.append(node)
        node_children[id] = []
        node_x_and_height[id] = (id, 0)
        max_width = max(max_width, id)

current_nodes = set(leaf_nodes)
root_nodes = []
while current_nodes:
    next_nodes = set()
    for node in current_nodes:
        parent_edges = node.parent_edges()
        if parent_edges:
            for edge in parent_edges:
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




for c in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.unlink(c)

for c in bpy.data.collections:
    bpy.data.collections.remove(c)

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

    material = bpy.data.materials.new(name+"_material")
    material.diffuse_color = NODE_COLOUR
    if arg.is_leaf(id):
        material.diffuse_color = SAMPLE_COLOUR
    curvedata.materials.append(material)
    curvedata.bevel_depth = 0.1

    if SHOW_TEXT:
        bpy.ops.object.text_add(location=(x, s - 1, h), rotation=(0, 0, 0))
        bpy.context.object.name = f"id_{id}"
        bpy.context.object.data.body = str(id)

        bpy.ops.object.text_add(location=(x, e + 1, h), rotation=(0, 0, 2 * HALF_PI))
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

        #create new material with name of object and assign to obj
        new_mat = bpy.data.materials.new(obj_name)
        edge_colour = [EDGE_COLOUR[i] for i in range(4)]
        if not arg.is_leaf(node.ID):
            edge_colour[0] += node.ID / colour_tweak_scale
            edge_colour[3] = 0.05
        new_mat.diffuse_color = edge_colour
        obj.data.materials.append(new_mat)

        if SHOW_TEXT:
            u = 0.5
            v = 1 - u
            mid_x = u * x1 + v * x2
            mid_h = u * h1 + v * h2
            bpy.ops.object.text_add(location=(mid_x, s, mid_h), rotation=(HALF_PI, 0, HALF_PI))
            bpy.context.object.name = f"start_{id}"
            bpy.context.object.data.body = str(edge.start)
            bpy.ops.object.text_add(location=(mid_x, e, mid_h), rotation=(HALF_PI, 0, HALF_PI))
            bpy.context.object.name = f"end_{id}"
            bpy.context.object.data.body = str(edge.end)

        recurse_create_edges(edge.parent)

for node in leaf_nodes:
    recurse_create_edges(node)

bpy.ops.wm.save_as_mainfile(filepath="example.blend")
