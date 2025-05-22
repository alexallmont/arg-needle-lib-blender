# arg-needle-lib-blender

Blender output to help visualise ARG internals. This is diagnosis aid whilst
adding new features, in particular support for polytomy in arg-needle-lib.

## Usage

Install Blender and run the following

```sh
pip install -r requirements.txt
python example.py && open example.blend
```

Example screenshot of internals of ARG. Nodes in an arg can contain many spans
of edges. To render this they are shown - somewhat counterintuitively for
nodes - as lines, with samples in blue and internal nodes in green. Edges span
subregions between start and end range along nodes so these are rendered as
rectangles, blue at base shifting to red for higher node IDs.

![screenshot](screenshot.png)

The selection in Blender here shows four overlapping edge spans coming off one
node. Text can be disabled in code by setting `SHOW_TEXT` to False.
