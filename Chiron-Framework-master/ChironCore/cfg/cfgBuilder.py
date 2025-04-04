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
