import arg_needle_lib

from arg_to_blender import ArgToBlender

op_arg_n = [1, 2, 2, 3, 3]
ops = [
    lambda arg : arg.add_sample(),
    lambda arg : arg.add_sample(),
    lambda arg : arg.thread_sample([0, 20, 80], [0, 0, 0], [3, 4, 3]),
    lambda arg : arg.add_sample(),
    lambda arg : arg.thread_sample([0, 70, 80], [0, 1, 1], [6, 6, 6]),
]

for num_ops in range(len(ops)):
    arg_n = op_arg_n[num_ops]
    print(arg_n)
    arg = arg_needle_lib.ARG(0, 100, arg_n)
    for i in range(num_ops + 1):
        ops[i](arg)
    arg.populate_children_and_roots()
    ts = arg_needle_lib.arg_to_tskit(arg)

    ArgToBlender(arg, png_out_file=f"example_threading_{num_ops}.png")
