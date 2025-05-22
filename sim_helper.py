import arg_needle_lib
import msprime

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
