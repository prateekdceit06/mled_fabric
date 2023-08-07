
def build_tree(master_config):
    # create empty tree dictionary
    tree = {}

    # loop over layers
    for layer in master_config['layers']:
        # loop over nodes in the layer
        for node in layer['nodes']:
            # if a node has a parent, add the node as a child of the parent
            if node['parent']:
                if node['parent'] not in tree:
                    tree[node['parent']] = []
                tree[node['parent']].append(node['name'])
            # if a node has no parent and is not already in the tree, add it with no children
            if not node['parent'] and node['name'] not in tree:
                tree[node['name']] = []

    return tree


def find_root_node(tree):
    # find the root node (node with no parent)
    for node in tree:
        if not any(node in children for children in tree.values()):
            root_node = node
            break
    return root_node


def print_tree(node_name, tree, indent=0):
    if indent == 0:
        print(node_name)
    else:
        print('   ' * (indent - 1) + '+--' + node_name)
    for child_name in tree.get(node_name, []):
        print_tree(child_name, tree, indent + 1)
