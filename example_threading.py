"""
Example of threading process using arg-needle-lib

Generates various samples of threading samples into an ARG, rendering image
of ARG and overlaying code at each stage.
"""
import arg_needle_lib
import bpy

from arg_render_info import ArgRenderInfo, ArgRenderScale
from arg_to_blender import ArgToBlender
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from dataclasses import dataclass

@dataclass
class ThreadingOps:
    name:  str      # Name used in output filenames
    start: float    # Start and end of ARG
    end:   float
    thread_sample_args: list # Arguments passed to arg.thread_sample()

Path("example_out").mkdir(exist_ok=True)

# Fix render output resolution for consistent results
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600

# Use system font in Pillow for text rendering
font = ImageFont.load_default(12)

# Example threading operations
threading_examples = [
    ThreadingOps("simple", 0, 100, [
        ([0, 60], [0, 0], [1, 2]),
        ([0], [0], [3]),
    ]),
    ThreadingOps("broken_polytomy", 0, 100, [
        ([0, 20, 80], [0, 0, 0], [3, 4, 3]),
        ([0, 70, 80], [0, 1, 1], [6, 6, 6]),
    ]),
    ThreadingOps("output-50-10-80000", 0, 80000, [
        ([0, 2080, 7084, 9789, 11545, 15016, 17095, 19419, 20941, 23306, 25067, 27104, 28782, 30253, 32815, 34801, 37361, 40562, 41746, 45551, 54218, 55287, 57900, 59685, 62508, 66830, 73460, 75727], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [10718.618962907021, 4287.134251627941, 15599.740536576062, 12892.15411736792, 11687.615184347811, 20588.900739646706, 40260.17092018282, 37596.219219486309, 26297.077393787757, 24103.30372557517, 21006.575743898084, 34938.80831984539, 28166.262054796731, 8495.0769461326308, 11279.910227356229, 8502.2568424007586, 12863.479293774855, 19088.829436018921, 5552.7651544700575, 2860.9861217558168, 20903.891014173041, 8310.3842842058912, 12668.011742100914, 7627.0297670856462, 4900.6741823746397, 3421.8904058412995, 9739.6963716304235, 23501.096674691464]),
        ([0, 2080, 11545, 30253, 45551, 62508, 66830], [1, 1, 1, 0, 1, 1, 1], [36907.231813543192, 16667.820674772189, 1921.1028043691995, 8571.5781853834269, 5105.7224025381347, 4900.5179465874135, 3727.3676795632632]),
        ([0, 11545], [2, 1], [4490.9246369849961, 876.34155993398133]),
        ([0, 17095, 66830], [0, 3, 2], [2522.21118880416, 1361.6173269208837, 3727.3911379111364]),
        ([0], [3], [766.90707352975653]),
        ([0, 17095], [0, 5], [2005.5670597757173, 941.54404693939023]),
        ([0, 32815], [0, 2], [1767.9631101227581, 2019.6534436236095]),
        ([0, 66830], [5, 7], [1083.7098309923301, 2657.0628987287082]),
        ([0], [8], [1173.2765655254432]),
        ([0, 45551, 66830], [8, 4, 9], [1154.9029624202253, 2700.6488529118078, 2657.0699538248618]),
        ([0], [9], [1173.3042543721676]),
    ])
]

for tex in threading_examples:
    frames = []
    def generate_frame():
        frame_idx = len(frames) + 1
        print(f"Frame {frame_idx}")

        full_code_text = "\n".join(code_lines)
        print(full_code_text)
        print()

        # Render using Blender
        filename = f"example_out/threading_{tex.name}_{frame_idx}.png"
        ri = ArgRenderInfo(arg, False)
        rs = ArgRenderScale(ri)
        ArgToBlender(
            arg_render_info=ri,
            render_scale=rs,
            png_out_file=filename,
            camera_location=(17, -5, 8),
            camera_look_at=(0, 9, 3)
        )

        # Draw code over ARG image
        arg_img = Image.open(filename)
        arg_draw = ImageDraw.Draw(arg_img)
        text_pos = (arg_img.width - 300, arg_img.height - 160)
        arg_draw.text(text_pos, full_code_text, (127, 127, 127), font=font)

        # Compositve over black background and boost contrast
        bg_img = arg_img.copy()
        bg_draw = ImageDraw.Draw(bg_img)
        bg_draw.rectangle([(0, 0), bg_img.size], (0, 0, 0))
        img = Image.alpha_composite(bg_img, arg_img)
        enhancer = ImageEnhance.Contrast(img.convert('RGB'))
        img = enhancer.enhance(1.5)

        frames.append(img)
        img.save(filename)

    # Show ARG as if each operation added per frame
    arg_n = len(tex.thread_sample_args) + 1
    arg = arg_needle_lib.ARG(tex.start, tex.end, arg_n)
    arg.add_sample()
    code_lines = ["arg.add_sample()"]
    generate_frame()

    for threading_args in tex.thread_sample_args:
        # Add next sample and update code text
        arg.add_sample()
        code_lines.append("arg.add_sample()")
        generate_frame()

        # Thread last sample with threading args and update code text
        # Note formatting verbatim op.args tuple will generate brackets so new
        # code line will look like "thread_sample([...], [...], [...])"
        arg.thread_sample(*threading_args)
        code_lines.append(f"thread_sample{threading_args}")
        generate_frame()

    # Save animated GIF
    frames[0].save(
        f"example_out/threading_{tex.name}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=1000,
        loop=0
    )
