# mlm_tree_demo.py
# pip install networkx anytree

import networkx as nx

# ---------- 1) MLM Tree (Sponsor -> Member) ----------
G = nx.DiGraph()

# Example binary placements:
# root = rocky001
placements = [
    ("rocky001", "rocky002", "L"),
    ("rocky001", "rocky003", "R"),
    ("rocky002", "rocky004", "L"),
    ("rocky002", "rocky005", "R"),
    ("rocky003", "rocky006", "L"),
    ("rocky003", "rocky007", "R"),
    ("rocky004", "rocky008", "L"),
]

# Add edges with side info (L/R)
for sponsor, member, side in placements:
    G.add_edge(sponsor, member, side=side)

ROOT = "rocky001"

# ---------- 2) Helpers ----------
def get_children(node: str):
    """Return (left_child, right_child) by checking edge attribute 'side'."""
    left = right = None
    for child in G.successors(node):
        side = G.edges[node, child].get("side")
        if side == "L":
            left = child
        elif side == "R":
            right = child
    return left, right

def count_descendants(start_node: str) -> int:
    """Count all descendants under a node (all levels)."""
    if not start_node:
        return 0
    return len(nx.descendants(G, start_node))

def member_level(member: str) -> int:
    """Level from ROOT (ROOT=0). If not connected, return -1."""
    try:
        return nx.shortest_path_length(G, ROOT, member)
    except nx.NetworkXNoPath:
        return -1

def eligibility(left_cnt: int, right_cnt: int) -> bool:
    """1:2 or 2:1 lifetime eligibility rule."""
    return (left_cnt >= 2 and right_cnt >= 1) or (left_cnt >= 1 and right_cnt >= 2)

# ---------- 3) Print summary for each member ----------
print("AUTO_ID | Level | LeftCnt | RightCnt | Eligible(1:2 or 2:1)")
print("-" * 62)

for m in sorted(G.nodes()):
    l_child, r_child = get_children(m)
    left_cnt = count_descendants(l_child)
    right_cnt = count_descendants(r_child)
    elig = eligibility(left_cnt, right_cnt)

    print(f"{m:7} | {member_level(m):5} | {left_cnt:7} | {right_cnt:8} | {elig}")

# ---------- 4) (Optional) AnyTree pretty print ----------
try:
    from anytree import Node
    from anytree import RenderTree

    # Build AnyTree nodes
    nodes = {}
    for n in G.nodes():
        nodes[n] = Node(n)

    # Attach parents based on edges
    for parent, child in G.edges():
        nodes[child].parent = nodes[parent]

    print("\n--- TREE VIEW (AnyTree) ---")
    for pre, _, node in RenderTree(nodes[ROOT]):
        print(pre + node.name)

except Exception as e:
    print("\n(AnyTree print skipped) Reason:", e)

