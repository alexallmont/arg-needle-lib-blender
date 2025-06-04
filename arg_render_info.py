from dataclasses import dataclass

@dataclass
class NodeRenderInfo:
    """
    Memo for ARG node render, represented as a 3D line parallel to y
    y axis (hence start and end position along y) with x position
    determined by layout code in ArgRenderInfo. This is separate from
    arg-needle-lib internals so new theoretical structures may be
    sketched.
    """
    id: int
    height: float
    y_start: float
    y_end: float
    x_pos: float
    colour: tuple
    depth: int

    def __hash__(self):
        return hash(self.id)


@dataclass
class EdgeRenderInfo:
    """
    Memo for ARG edge render, represented as a 3D rectangle between
    existing nodes. The edge may run only a sub-span of nodes it connects
    hence separate start and end positions). The rectangle is tangent to
    y axis, with orientation determined by parent and child node positions.
    Like NodeRenderInfo, this is separate from arg-needle-lib classes
    to articulate experimental structures.
    """
    parent_id: int
    child_id: int
    y_start: float
    y_end: float
    colour: tuple

    def __hash__(self):
        ID_SCALE = 2 ** 32
        return hash(self.child_id * ID_SCALE + self.y_start)


class ArgRenderInfo:
    def __init__(self, arg=None, quantise=False):
        self.quantise = quantise
        if arg:
            self.build_from_arg(arg)
        else:
            self.clear()

    def clear(self):
        self.nodes = []
        self.edges = []
        self._clear_maps()

    def add_node(self, id: int, height: float, y_start: float, y_end: float):
        node = NodeRenderInfo(
            id,
            height,
            y_start,
            y_end,
            None,
            None,
            None
        )
        self.nodes.append(node)
        return node

    def add_edge(self, parent_id: int, child_id: int, y_start: float, y_end: float):
        edge = EdgeRenderInfo(
            parent_id,
            child_id,
            y_start,
            y_end,
            None
        )
        self.edges.append(edge)
        return edge

    def build_from_arg(self, arg):
        self.clear()

        for node_id in arg.node_ids():
            # Create memo of node rendering info per arg node
            arg_node = arg.node(node_id)
            node = self.add_node(
                node_id,
                arg_node.height,
                arg_node.start,
                arg_node.end
            )
            self.node_by_id[node_id] = node

            # Quick lookup of leaf (sample) and interior nodes
            if arg.is_leaf(node_id):
                # Use sample id as first approximation of position
                node.x_pos = node_id
                self.leaf_nodes.add(node)
            else:
                self.interior_nodes.add(node)

            # Create any associated edges, breakpoints and root nodes
            parent_edges = arg_node.parent_edges()
            if parent_edges:
                for arg_edge in parent_edges:
                    edge = self.add_edge(
                        arg_edge.parent.ID,
                        node_id,
                        arg_edge.start,
                        arg_edge.end
                    )

                    # Fast lookup of all edges for a given node
                    self.edges_by_child_node_id.setdefault(
                        node_id,
                        set()
                    ).add(edge)

                    self.breakpoint_positions.add(arg_edge.start)
                    self.breakpoint_positions.add(arg_edge.end)
            else:
                self.root_nodes.add(node)

        self._compute_x_pos_and_depth()

    def rebuild_maps(self):
        self._clear_maps()
        # FIXME need to replicate build_from_arg behaviour for manual nodes
        # Note for each edge, need to check
        # assert(parent_id < len(self.nodes))
        # assert(child_id < len(self.nodes))
        self._compute_x_pos_and_depth()

    def node_is_leaf(self, node):
        return node in self.leaf_nodes

    def _clear_maps(self):
        self.node_by_id = {}
        self.edges_by_child_node_id = {}
        self.leaf_nodes = set()
        self.interior_nodes = set()
        self.root_nodes = set()
        self.breakpoint_positions = set()
        self.node_children = {}
        self.nodes_by_depth = {}

    def _compute_x_pos_and_depth(self):
        # In order to compute internal node positions, determine depth where 0
        # is start leaf nodes (x_pos known) and 1 is their immediate dependants
        # (x_pos averaged from parents), then onto 2, 3.. until all x_pos set
        self.node_children = {}
        max_compute_depth = 0
        current_nodes = self.leaf_nodes
        while current_nodes:
            parent_nodes = set()
            for node in current_nodes:
                # Note this intentionally overwrites a previously-visted node
                # depth if set; the maximal depth is what is needed
                node.depth = max_compute_depth

                # Collect parent nodes coming off this node for next iteration
                parent_edges = self.edges_by_child_node_id.get(node.id, set())
                for edge in parent_edges:
                    parent_node = self.node_by_id[edge.parent_id]
                    parent_nodes.add(parent_node)

                    # Track any nodes to compute contribution to parent's x_pos
                    self.node_children.setdefault(parent_node, set()).add(node)

            # Move up to next layer
            max_compute_depth += 1
            current_nodes = parent_nodes

        self.nodes_by_depth = {}
        for node in self.nodes:
            self.nodes_by_depth.setdefault(
                node.depth,
                []
            ).append(node)

        if self.nodes_by_depth:
            # If the leaf node x positions have not been set - i.e. when working
            # with manually-built structure not via build_from_arg - then set an
            # arbitrary x pos for each.
            if any([node.x_pos == None for node in self.nodes_by_depth[0]]):
                for new_id, node in enumerate(self.nodes_by_depth[0]):
                    node.x_pos = new_id

            # Ascend up compute stack to set each node's position as average of
            # contributors, i.e. ensure any parent (higher) nodes are rendered
            # inbeteen it's children (lower).
            for compute_depth in range(1, max_compute_depth):
                for node in self.nodes_by_depth[compute_depth]:
                    contribs = self.node_children[node]
                    contribs_x_pos = [contrib.x_pos for contrib in contribs]
                    avg = sum(contribs_x_pos) / len(contribs)
                    node.x_pos = avg

        # Quantise the locations so they are not fractional. For example, given
        # a minimal 3 node graph with leaves at 0 and 1, their parent would be
        # 0.5 by default. Quantise instead uses x_pos as sort order and then
        # places at sort index, so leaves at 0 and 2 with parent inbetween at 1.
        if self.quantise:
            x_sorted_nodes = [node for node in self.nodes]
            x_sorted_nodes.sort(key=lambda node: node.x_pos)
            for index_pos, node in enumerate(x_sorted_nodes):
                node.x_pos = index_pos

# FIXME remove ArgRenderScale derivation; it can be rolled directly into this class
class RenderScale:
    def scale_xhl(self, x, h, len):
        x = self.scale_x(x)
        h = self.scale_h(h)
        len = self.scale_len(len)
        return x, h, len

    def scale_xh(self, x, h):
        x = self.scale_x(x)
        h = self.scale_h(h)
        return x, h

    def scale_x(self, x):
        return x

    def scale_h(self, h):
        return h

    def scale_len(self, len):
        return len


class ArgRenderScale(RenderScale):
    def __init__(self, render_info, global_scale=10):
        self._compute_scale(render_info, global_scale)

    def scale_x(self, x):
        return (x - self.max_width / 2) * self.x_scale

    def scale_h(self, h):
        return h * self.height_scale

    def scale_len(self, len):
        return len * self.len_scale

    def _compute_scale(self, render_info, global_scale):
        max_height = 0
        max_len = 0
        for node in render_info.nodes:
            max_height = max(max_height, node.height)
            max_len = max(max_len, node.y_end)

        self.max_height = max_height
        self.max_len = max_len
        self.max_width = len(render_info.leaf_nodes) - 1

        self.x_scale = global_scale / (self.max_width + 1)
        self.height_scale = global_scale / (self.max_height + 1)
        self.len_scale = global_scale * 3 / (self.max_len + 1)
