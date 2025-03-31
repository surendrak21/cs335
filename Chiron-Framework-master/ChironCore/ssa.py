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

class PhiFunction:
    def _init_(self, target):
        self.target = target
        self.values = []  # Will be filled with (value, block) pairs

    def add_value(self, value, block):
        self.values.append((value, block))

    def _str_(self):
        return f"{self.target} = Φ({', '.join(f'{v}@{b.label()}' for v, b in self.values)})"

def validate_cfg(cfg):
    try:
        if cfg is None or not hasattr(cfg, 'nodes'):
            logger.error("Invalid CFG: None or missing nodes")
            return False
        if not list(cfg.nodes()):
            logger.error("Empty CFG")
            return False
        return True
    except Exception as e:
        logger.error(f"CFG validation failed: {str(e)}")
        return False

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

def compute_dominance_frontiers(cfg, dominators):
    frontiers = defaultdict(set)
    nodes = list(cfg.nodes())
    
    for node in nodes:
        preds = list(cfg.predecessors(node))
        if len(preds) >= 2:
            for p in preds:
                runner = p
                while runner != list(dominators[node] - {node})[0] if len(dominators[node] - {node}) > 0 else None:
                    frontiers[runner].add(node)
                    if runner not in dominators:
                        break
                    runner_doms = dominators[runner]
                    if not runner_doms:
                        break
                    runner = next(iter(runner_doms - {runner})) if len(runner_doms - {runner}) > 0 else None
                    if runner is None:
                        break
    
    return frontiers

def find_variable_defs(cfg):
    var_defs = defaultdict(set)
    
    for node in cfg.nodes():
        for stmt in node.instrlist:
            # Handle both (instruction, index) and direct instruction formats
            instr = stmt[0] if isinstance(stmt, tuple) else stmt
            
            # Check for assignment patterns
            if hasattr(instr, 'lvar') and hasattr(instr.lvar, 'name') and instr.lvar.name.startswith(':'):
                var_defs[instr.lvar.name].add(node)
            elif hasattr(instr, 'var') and hasattr(instr.var, 'name') and instr.var.name.startswith(':'):
                var_defs[instr.var.name].add(node)
            elif str(instr).startswith(':') and '=' in str(instr):
                var = str(instr).split('=')[0].strip()
                if var.startswith(':'):
                    var_defs[var].add(node)
    
    logger.info(f"Variables found: {list(var_defs.keys())}")
    logger.info(f"Variables needing phi: {[v for v in var_defs if len(var_defs[v]) > 1]}")
    return var_defs

def insert_phi_functions(cfg, dominance_frontier, var_defs):
    phi_insertions = defaultdict(list)
    
    for var, def_blocks in var_defs.items():
        if len(def_blocks) < 2:
            continue
            
        worklist = deque(def_blocks)
        processed = set()
        has_phi = set()
        
        while worklist:
            block = worklist.popleft()
            for frontier in dominance_frontier.get(block, set()):
                if frontier not in has_phi:
                    # Create new phi function
                    phi = PhiFunction(var)
                    
                    # Add values from all predecessors
                    for pred in cfg.predecessors(frontier):
                        phi.add_value(var, pred)
                    
                    # Insert at start of block
                    frontier.instrlist.insert(0, (phi, 0))
                    phi_insertions[var].append(frontier.label())
                    has_phi.add(frontier)
                    
                    if frontier not in processed:
                        worklist.append(frontier)
                        processed.add(frontier)
    
    # Improved logging
    for var, blocks in phi_insertions.items():
        logger.info(f"Inserted Φ({var}) at blocks: {', '.join(blocks)}")
    logger.info(f"Total phi functions inserted: {sum(len(v) for v in phi_insertions.values())}")

    # Debug output of final CFG
    logger.info("\nFinal CFG with Phi Functions:")
    for node in cfg.nodes():
        logger.info(f"\nBlock {node.label()}:")
        for instr in node.instrlist:
            if isinstance(instr[0], PhiFunction):
                logger.info(f"  PHI: {str(instr[0])}")
            else:
                logger.info(f"  {str(instr[0])}")  

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
        
        logger.info(f"=== SSA Completed in {time.time()-start_time:.3f}s ===")
        return cfg
    except Exception as e:
        logger.error(f"SSA failed: {str(e)}", exc_info=True)
        return None