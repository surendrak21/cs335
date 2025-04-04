import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
from cfg.ChironCFG import BasicBlock, ChironCFG
import ChironAST.ChironAST as ChironAST

def buildCFG(ir, cfgName="", isSingle=False):
    # === Fix: Clear old BasicBlock state before creating a new CFG ===
    BasicBlock.reset_counter()  # You should define this in BasicBlock to reset label count if needed

    # Create entry and exit blocks
    startBB = BasicBlock('START')
    endBB = BasicBlock('END')

    # === Step 1: Identify leaders ===
    leaderIndices = {0, len(ir)}
    leader2IndicesMap = {startBB: 0, endBB: len(ir)}
    indices2LeadersMap = {0: startBB, len(ir): endBB}

    for idx, item in enumerate(ir):
        if isinstance(item[0], ChironAST.ConditionCommand) or isSingle:
            if idx + 1 < len(ir) and (idx + 1 not in leaderIndices):
                leaderIndices.add(idx + 1)
                thenBranchLeader = BasicBlock(str(idx + 1))
                leader2IndicesMap[thenBranchLeader] = idx + 1
                indices2LeadersMap[idx + 1] = thenBranchLeader
            if idx + item[1] < len(ir) and (idx + item[1] not in leaderIndices):
                leaderIndices.add(idx + item[1])
                elseBranchLeader = BasicBlock(str(idx + item[1]))
                leader2IndicesMap[elseBranchLeader] = idx + item[1]
                indices2LeadersMap[idx + item[1]] = elseBranchLeader

    # === Step 2: Create CFG ===
    cfg = ChironCFG(cfgName)
    for leader in leader2IndicesMap.keys():
        # Clear phi and def/use from previous runs
        leader.phi_functions = []
        leader.defs = set()
        leader.uses = set()
        cfg.add_node(leader)

    # === Step 3: Populate instructions in basic blocks ===
    for currLeader in leader2IndicesMap.keys():
        leaderIdx = leader2IndicesMap[currLeader]
        currIdx = leaderIdx
        while currIdx < len(ir):
            currLeader.append((ir[currIdx][0], currIdx))
            currIdx += 1
            if currIdx in leaderIndices:
                break

    # === Step 4: Add control flow edges ===
    for node in cfg:
        if not node.instrlist:
            continue

        irIdx = node.instrlist[-1][1]
        lastInstr = node.instrlist[-1][0]

        if isinstance(lastInstr, ChironAST.ConditionCommand):
            if not isinstance(lastInstr.cond, ChironAST.BoolFalse):
                thenIdx = irIdx + 1 if (irIdx + 1 < len(ir)) else len(ir)
                thenBB = indices2LeadersMap[thenIdx]
                cfg.add_edge(node, thenBB, label='Cond_True', color='green')

            if not isinstance(lastInstr.cond, ChironAST.BoolTrue):
                elseIdx = irIdx + ir[irIdx][1] if (irIdx + ir[irIdx][1] < len(ir)) else len(ir)
                elseBB = indices2LeadersMap[elseIdx]
                cfg.add_edge(node, elseBB, label='Cond_False', color='red')
        else:
            nextIdx = irIdx + 1 if (irIdx + 1 < len(ir)) else len(ir)
            nextBB = indices2LeadersMap[nextIdx]
            cfg.add_edge(node, nextBB, label='flow_edge', color='blue')

    return cfg

def dumpCFG(cfg, filename="control_flow_graph"):
    """
    Generates and saves a graphical PNG image of the control flow graph.
    """
    try:
        G = cfg.nxgraph
        labels = {node: node.label() for node in cfg}
        G = nx.relabel_nodes(G, labels)
        A = to_agraph(G)
        A.layout('dot')
        A.draw(filename + ".png")
        print(f"CFG image saved as {filename}.png")
    except Exception as e:
        print(f"Error generating CFG image: {e}")
import logging
import os
from collections import defaultdict, deque

# Set up logging
log_file = os.path.join(os.getcwd(), "ssa_output.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class PhiFunction:
    """Represents a φ-function in SSA form."""
    def __init__(self, target):
        self.target = target
        self.values = []  # List of (value, predecessor block) tuples

    def add_value(self, value, block):
        self.values.append((value, block))

    def __str__(self):
        args = ', '.join(f'{v}@{b.name}' for v, b in self.values)
        return f"{self.target} = φ({args})"

def validate_cfg(cfg):
    """Validates the structure of the control flow graph (CFG)."""
    if cfg is None or not hasattr(cfg, 'nodes'):
        logger.error("Invalid CFG: None or missing 'nodes' attribute.")
        return False
    if not list(cfg.nodes()):
        logger.error("CFG is empty.")
        return False
    return True

def compute_dominators(cfg):
    """Computes the dominator sets for each node in the CFG."""
    nodes = list(cfg.nodes())
    entry = next(iter(cfg.nodes()))
    dominators = {node: set(nodes) for node in nodes}
    dominators[entry] = {entry}

    changed = True
    while changed:
        changed = False
        for node in nodes:
            if node == entry:
                continue
            preds = list(cfg.predecessors(node))
            if not preds:
                continue
            new_doms = set.intersection(*(dominators[p] for p in preds))
            new_doms.add(node)
            if new_doms != dominators[node]:
                dominators[node] = new_doms
                changed = True
    return dominators

def compute_dominance_frontiers(cfg, dominators):
    """Computes the dominance frontiers for each node in the CFG."""
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

def find_variable_defs(cfg):
    """Identifies all variable definitions within the CFG."""
    var_defs = defaultdict(set)
    for node in cfg.nodes():
        for instr, idx in node.instrlist:
            if hasattr(instr, 'lvar') and instr.lvar and hasattr(instr.lvar, 'name'):
                var_name = instr.lvar.name
                if var_name.startswith(':'):
                    var_defs[var_name].add(node)
            else:
                logger.warning(f"Instruction at index {idx} is missing a proper lvar.name")
    logger.info(f"Variables found: {list(var_defs.keys())}")
    return var_defs

def insert_phi_functions(cfg, dominance_frontiers, var_defs):
    """Inserts φ-functions into the CFG at appropriate locations."""
    phi_insertions = defaultdict(list)
    for var, defining_blocks in var_defs.items():
        if len(defining_blocks) < 2:
            continue
        worklist = deque(defining_blocks)
        has_phi = set()
        processed = set()
        while worklist:
            block = worklist.popleft()
            for frontier in dominance_frontiers.get(block, set()):
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
        logger.info(f"Inserted φ({var}) at blocks: {', '.join(blocks)}")
    logger.info(f"Total φ-functions inserted: {sum(len(v) for v in phi_insertions.values())}")

def rename_variables(cfg, dominators):
    """Renames variables to ensure each has a unique assignment in SSA form."""
    current_version = defaultdict(int)
    var_stack = defaultdict(list)

    def rename_recursive(block):
        new_instrlist = []
        for instr, idx in block.instrlist:
            if isinstance(instr, PhiFunction):
                new_target = f"{instr.target}_{current_version[instr.target]}"
                current_version[instr.target] += 1
                var_stack[instr.target].append(new_target)
                instr.target = new_target
                new_instrlist.append((instr, idx))
            else:
                if hasattr(instr, 'lvar') and instr.lvar and hasattr(instr.lvar, 'name'):
                    old_var = instr.lvar.name
                    new_var = f"{old_var}_{current_version[old_var]}"
                    current_version[old_var] += 1
                    var_stack[old_var].append(new_var)
                    instr.lvar.name = new_var
                if hasattr(instr, 'rvars'):
                    for rvar in instr.rvars:
                        if hasattr(rvar, 'name'):
                            old_var = rvar.name
                            if var_stack[old_var]:
                                rvar.name = var_stack[old_var][-1]
                new_instrlist.append((instr, idx))

        block.instrlist = new_instrlist
        for succ in cfg.successors(block):
            if block in dominators.get(succ, []):
                rename_recursive(succ)

        for instr, idx in new_instrlist:
            if isinstance(instr, PhiFunction):
                var_stack[instr.target].pop()
            elif hasattr(instr, 'lvar') and instr.lvar and hasattr(instr.lvar, 'name'):
                var_stack[instr.lvar.name].pop()

    entry_block = next(iter(cfg.nodes()))
    rename_recursive(entry_block)

def convert_to_ssa(cfg):
    """Converts the given CFG to SSA form."""
    if not validate_cfg(cfg):
        return
    dominators = compute_dominators(cfg)
    dominance_frontiers = compute_dominance_frontiers(cfg, dominators)
    var_defs = find_variable_defs(cfg)
    insert_phi_functions(cfg, dominance_frontiers, var_defs)
    rename_variables(cfg, dominators)
    logger.info("SSA conversion completed successfully.")
