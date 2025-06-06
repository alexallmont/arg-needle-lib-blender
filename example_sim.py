import arg_needle_lib
import msprime

from arg_render_info import ArgRenderInfo
from arg_to_blender import ArgToBlender
from pathlib import Path

Path("out").mkdir(exist_ok=True)

def arg_from_sim(
    samples: int,
    seq_len: int,
    pop_size: int,
    recom: float,
    mu: float,
    seed: int
):
    ts = msprime.sim_ancestry(
        samples=samples,
        recombination_rate=recom,
        sequence_length=seq_len,
        population_size=pop_size,
        random_seed=seed
    )
    arg = arg_needle_lib.tskit_to_arg(ts)
    arg_needle_lib.generate_mutations(arg, mu=mu, random_seed=seed)
    arg.populate_children_and_roots()
    arg.populate_mutations_on_edges()
    return arg

if __name__ == "__main__":
    arg = arg_from_sim(3, 1_000, 10_000, 2e-7, 2e-7, 1234)

    ArgToBlender(
        ArgRenderInfo(arg),
        png_out_file="out/sim.png",
        blender_out_file="out/sim.blend",
        text_scale = 0.3,
        camera_location=(-15, -12, 8),
        camera_look_at=(-2, 6, 4)
    )
