"""
Example of threading process using arg-needle-lib

Generates various samples of threading samples into an ARG, rendering image
of ARG and overlaying code at each stage.
"""
import arg_needle_lib
import bpy

from arg_to_blender import ArgToBlender
from pathlib import Path
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from dataclasses import dataclass

@dataclass
class ArgOps:
    name: str       # Name used in output filenames
    op_arg_n: list  # Size of ARG at each step of 'ops'
    start: float    # Start and end of ARG
    end: float
    ops: list       # List of add_sample/thread_sample instructions

Path("example_out").mkdir(exist_ok=True)

# Fix render output resolution for consistent results
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600

# Use system font in Pillow for text rendering
font = ImageFont.load_default(12)

# Example threading operations
threading_examples = [
    ArgOps("simple", [1, 2, 2, 3, 3], 0, 100, [
        "arg.add_sample()",
        "arg.add_sample()",
        "arg.thread_sample([0, 60], [0, 0], [1, 2])",
        "arg.add_sample()",
        "arg.thread_sample([0], [0], [3])",
    ]),
    ArgOps("broken_polytomy", [1, 2, 2, 3, 3], 0, 100, [
        "arg.add_sample()",
        "arg.add_sample()",
        "arg.thread_sample([0, 20, 80], [0, 0, 0], [3, 4, 3])",
        "arg.add_sample()",
        "arg.thread_sample([0, 70, 80], [0, 1, 1], [6, 6, 6])",
    ])
]

for ex in threading_examples:

    # Show ARG as if each operation added per frame
    for num_ops in range(len(ex.ops)):
        arg_n = ex.op_arg_n[num_ops]
        print(f"Frame {arg_n}")

        # Evaluate num_ops number of operations
        init_op = f"arg_needle_lib.ARG({ex.start}, {ex.end}, {arg_n})"
        code_lines = [init_op]
        arg = eval(init_op)
        for i in range(num_ops + 1):
            eval(ex.ops[i], {"arg": arg})
            code_lines.append(ex.ops[i])

        # Full code text to render
        full_code_text = "\n".join(code_lines)
        print(full_code_text)
        print()

        # Summary of ARG as tree sequence
        arg.populate_children_and_roots()
        ts = arg_needle_lib.arg_to_tskit(arg)
        print(ts.draw_text())

        # Render using Blender
        filename = f"example_out/threading_{ex.name}_{num_ops}.png"
        ArgToBlender(
            arg,
            png_out_file=filename,
            camera_location=(17, -5, 8),
            camera_look_at=(0, 9, 3)
        )

        # Overlay source code
        img = Image.open(filename)
        draw = ImageDraw.Draw(img)
        text_pos = (img.width - 300, img.height - 160)
        draw.text(text_pos, full_code_text, (127, 127, 127), font=font)
        img.save(filename)
