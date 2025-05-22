# arg-needle-lib-blender

Blender output to help diagnose ARGs. This is an aid to diagnosis whilst adding
new features, in particular support for polytomy in arg-needle-lib.

## Usage

Install Blender and run the following

```sh
pip install -r requirements.txt
python example.py && open example.blend
```

Example screenshot of internals of ARG. Nodes in an arg can contain many spans
of edges, so to display this they are shown - somewhat counterintuitively - as
lines in green. The ARG's edges to other nodes span subregions between nodes
so these are the rectangles shown from blue to red depending on node ID.

![screenshot](screenshot.png)

The selection in Blender here shows three different edge spans coming off one
node.
