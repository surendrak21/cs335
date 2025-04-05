#!/usr/bin/python3.8

import networkx as nx

class BasicBlock:
    """
    Represents a basic block in the control flow graph (CFG).
    Each block has a unique name and a list of instructions.
    """
    _counter = 0  # Static counter to generate unique IR IDs for unnamed blocks

    def __init__(self, bbname):
        self.name = bbname
        self.instrlist = []  # List of (instruction, index) tuples

        if bbname in {"START", "END"}:
            self.irID = bbname
        else:
            self.irID = BasicBlock._counter
            BasicBlock._counter += 1

        self.var_versions = {}  # ✅ [ADDED] SSA variable version tracking per block

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"BB({self.name})"

    def append(self, instruction):
        """Append a single instruction to this basic block."""
        self.instrlist.append(instruction)

    def extend(self, instructions):
        """Extend the instruction list with multiple instructions."""
        self.instrlist.extend(instructions)

    def label(self):
        """
        Generate a label for visualization or printing.
        Shows instructions with their IR index if present, otherwise block name.
        """
        # ✅ [UPDATED] Use actual idx for label like L3, L4... for uniqueness
        if self.instrlist:
            return '\n'.join(f"{str(instr[0])}; L{instr[1]}" for instr in self.instrlist)
        else:
            return self.name

    @staticmethod
    def reset_counter():
        """Reset the static counter for IR IDs. Useful for regenerating fresh CFGs."""
        BasicBlock._counter = 0

    # ✅ [ADDED] Optional method for debug output including variable version tracking
    def get_instr_with_versions(self):
        """
        Return instructions as strings including SSA variable versions.
        Only for debug/analysis purposes.
        """
        output = []
        for instr, idx in self.instrlist:
            output.append(f"[L{idx}] {instr}")
        return "\n".join(output)


class ChironCFG:
    """
    An adapter for NetworkX's DiGraph to represent control flow graphs.
    Allows easy use of graph algorithms with our custom BasicBlocks.
    """

    def __init__(self, gname='cfg'):
        self.name = gname
        self.nxgraph = nx.DiGraph(name=gname)
        self.entry = "START"
        self.exit = "END"

    def __iter__(self):
        return iter(self.nxgraph)

    def is_directed(self):
        return True

    def add_node(self, node):
        if not isinstance(node, BasicBlock):
            raise ValueError("Only BasicBlock instances can be added to CFG.")
        self.nxgraph.add_node(node)

    def has_node(self, node):
        return self.nxgraph.has_node(node)

    def add_edge(self, u, v, **attr):
        if self.has_node(u) and self.has_node(v):
            self.nxgraph.add_edge(u, v, **attr)
        else:
            raise NameError(f"One or both nodes not in graph: {u}, {v}")

    def nodes(self):
        return self.nxgraph.nodes()

    def edges(self):
        return self.nxgraph.edges()

    def successors(self, node):
        return self.nxgraph.successors(node)

    def predecessors(self, node):
        return self.nxgraph.predecessors(node)

    def out_degree(self, node):
        return self.nxgraph.out_degree(node)

    def in_degree(self, node):
        return self.nxgraph.in_degree(node)

    def get_edge_label(self, u, v):
        edata = self.nxgraph.get_edge_data(u, v)
        return edata.get('label', 'T') if edata else 'T'

    def get_graph(self):
        return self.nxgraph
