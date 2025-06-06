"""
Example of manually-built ARG render
"""
import bpy

from arg_render_info import ArgRenderInfo, ArgRenderScale
from arg_to_blender import ArgToBlender
from pathlib import Path

Path("out/manual").mkdir(exist_ok=True, parents=True)

# Fix render output resolution for consistent results
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600

ri = ArgRenderInfo()

# Polytomy: add one  start
ri.add_node(0, 0, 0, 10)
ri.add_node(1, 0, 0, 10)
ri.add_node(2, 3, 1, 8)
ri.add_edge(2, 1, 1, 5)
ri.add_edge(2, 0, 5, 8)

ri.add_node(3, 0, 0, 10)
ri.add_edge(2, 3, 1, 2)
ri.add_edge(2, 3, 1, 2)

rs = ArgRenderScale(ri)
ArgToBlender(
    arg_render_info=ri,
    render_scale=rs,
    png_out_file="out/manual/test.png",
    camera_location=(-12, -8, 8),
    camera_look_at=(-2, 6, 3)
)

