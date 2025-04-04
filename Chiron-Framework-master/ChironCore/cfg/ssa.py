import logging
import os
from collections import defaultdict, deque
import time

# Set up logging
log_file = os.path.join(os.getcwd(), "output.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# === Phi Function Representation ===
class PhiFunction:
    def __init__(self, target):
        self.target = target
        self.values = []  # List of (value, predecessor block)

    def add_value(self, value, block):
        self.values.append((value, block))

    def __str__(self):
        joined = ', '.join(f'{v}@{b.label()}' for v, b in self.values)
        return f"{self.target} = Φ({joined})"

# === CFG Validation ===
def validate_cfg(cfg):
    try:
        if cfg is None or not hasattr(cfg, 'nodes'):
            logger.error("Invalid CFG: None or missing nodes")
            return False
        if not list(cfg.nodes()):
            logger.error("CFG is empty")
            return False
        return True
    except Exception as e:
        logger.error(f"CFG validation error: {str(e)}")
        return False

# === Dominator Set Computation ===
def compute_dominators(cfg):
    nodes = list(cfg.nodes())
    entry = nodes[0]
    dominators = {node: set(nodes) for node in nodes}
    dominators[entry] = {entry}
    changed = True

    while changed:
        changed = False
        for node in nodes[1:]:
            preds = list(cfg.predecessors(node))
            if not preds:
                continue
            new_dom = set.intersection(*(dominators[p] for p in preds))
            new_dom.add(node)
            if new_dom != dominators[node]:
                dominators[node] = new_dom
                changed = True

    return dominators

# === Dominance Frontier Computation ===
def compute_dominance_frontiers(cfg, dominators):
    frontiers = defaultdict(set)

    for node in cfg.nodes():
        preds = list(cfg.predecessors(node))
        if len(preds) >= 2:
            for pred in preds:
                runner = pred
                while runner and node not in dominators[runner]:
                    frontiers[runner].add(node)
                    runner_doms = dominators.get(runner, set())
                    runner = next(iter(runner_doms - {runner}), None)
                    if runner == runner_doms:
                        break
    return frontiers

# === Variable Definition Detection ===
def find_variable_defs(cfg):
    var_defs = defaultdict(set)
    entry_block = next(iter(cfg.nodes()))  # assume first block is entry

    for node in cfg.nodes():
        for stmt in node.instrlist:
            instr = stmt[0] if isinstance(stmt, tuple) else stmt
            try:
                if hasattr(instr, 'lvar') and hasattr(instr.lvar, 'name'):
                    name = instr.lvar.name
                elif hasattr(instr, 'var') and hasattr(instr.var, 'name'):
                    name = instr.var.name
                else:
                    # Fallback to string parsing
                    text = str(instr)
                    if text.startswith(':') and '=' in text:
                        name = text.split('=')[0].strip()
                    else:
                        continue
                if name.startswith(':'):
                    var_defs[name].add(node)
            except Exception as e:
                logger.debug(f"Skipping unrecognized instruction: {instr} - {e}")

    for var in var_defs:
        var_defs[var].add(entry_block)

    logger.info(f"Variables found: {list(var_defs.keys())}")
    return var_defs

# === Phi Function Insertion ===
def insert_phi_functions(cfg, dominance_frontier, var_defs):
    phi_insertions = defaultdict(list)

    for var, def_blocks in var_defs.items():
        if len(def_blocks) < 2:
            continue

        worklist = deque(def_blocks)
        has_phi = set()
        processed = set()

        while worklist:
            block = worklist.popleft()
            for frontier in dominance_frontier.get(block, set()):
                if frontier.name in {"START", "END"}:
                    continue
                if (frontier, var) not in has_phi:
                    phi = PhiFunction(var)
                    for pred in cfg.predecessors(frontier):
                        phi.add_value(var, pred)
                    frontier.instrlist.insert(0, (phi, 0))
                    phi_insertions[var].append(frontier.name)
                    has_phi.add((frontier, var))
                    if frontier not in processed:
                        worklist.append(frontier)
                        processed.add(frontier)

    for var, blocks in phi_insertions.items():
        logger.info(f"Inserted Φ({var}) at blocks: {', '.join(blocks)}")
    logger.info(f"Total φ-functions inserted: {sum(len(v) for v in phi_insertions.values())}")

# === SSA Construction Driver ===
def construct_ssa(cfg):
    logger.info("=== SSA Construction Started ===")
    start_time = time.time()

    if not validate_cfg(cfg):
        return None

    try:
        dominators = compute_dominators(cfg)
        dominance_frontier = compute_dominance_frontiers(cfg, dominators)
        var_defs = find_variable_defs(cfg)
        insert_phi_functions(cfg, dominance_frontier, var_defs)

        elapsed = time.time() - start_time
        logger.info(f"=== SSA Completed in {elapsed:.3f} seconds ===")
        return cfg
    except Exception as e:
        logger.error(f"SSA Construction Failed: {str(e)}", exc_info=True)
        return None
