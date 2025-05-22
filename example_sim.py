from sim_helper import arg_from_sim
from arg_to_blender import ArgToBlender

arg = arg_from_sim(3, 1_000, 10_000, 2e-7, 2e-7, 1234)

ArgToBlender(
    arg,
    png_out_file="sim.png",
    blender_out_file="sim.blend"
)
