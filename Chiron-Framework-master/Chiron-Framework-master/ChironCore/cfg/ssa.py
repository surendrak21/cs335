from cfg.ChironCFG import BasicBlock

class PhiFunction:
    def __init__(self, var):
        self.var = var  # Variable instance (e.g., Var(':a'))
        self.args = {}  # Mapping from predecessor block to value

    def add_argument(self, pred, value):
        self.args[pred] = value

    def __str__(self):
        args_str = ', '.join(f"{pred.label()}: {val}" for pred, val in self.args.items())
        return f"{self.var} = φ({args_str})"


def compute_dominators(cfg):
    start_node = list(cfg.nodes())[0]
    dominators = {node: set(cfg.nodes()) for node in cfg}
    dominators[start_node] = {start_node}

    changed = True
    while changed:
        changed = False
        for node in cfg:
            if node == start_node:
                continue
            preds = list(cfg.predecessors(node))
            if preds:
                new_doms = set.intersection(*[dominators[p] for p in preds]) | {node}
                if new_doms != dominators[node]:
                    dominators[node] = new_doms
                    changed = True
    return dominators


def compute_dominance_frontiers(cfg, dominators):
    frontier = {node: set() for node in cfg}

    for node in cfg:
        preds = list(cfg.predecessors(node))
        if len(preds) >= 2:
            for pred in preds:
                runner = pred
                while runner not in dominators[node]:
                    frontier[runner].add(node)
                    doms = dominators[runner] - {runner}
                    if doms:
                        runner = list(doms)[0]
                    else:
                        break
    return frontier


def insert_phi_functions(cfg, dominance_frontier):
    for node in dominance_frontier:
        for frontier in dominance_frontier[node]:
            existing_vars = {
                stmt[0].var for stmt in frontier.instrlist
                if isinstance(stmt[0], PhiFunction)
            }

            for stmt, _ in node.instrlist:
                if hasattr(stmt, 'target') and stmt.target not in existing_vars:
                    phi = PhiFunction(stmt.target)
                    frontier.instrlist.append((phi, len(frontier.instrlist)))
                    existing_vars.add(stmt.target)


def construct_ssa(cfg):
    dominators = compute_dominators(cfg)
    frontier = compute_dominance_frontiers(cfg, dominators)
    insert_phi_functions(cfg, frontier)

