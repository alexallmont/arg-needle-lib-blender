from arg_to_blender import ArgToBlender
from sim_helper import arg_from_sim
from pathlib import Path

Path("example_out").mkdir(exist_ok=True)

arg = arg_from_sim(3, 1_000, 10_000, 2e-7, 2e-7, 1234)

ArgToBlender(
    arg,
    png_out_file="example_out/sim.png",
    blender_out_file="example_out/sim.blend"
)
