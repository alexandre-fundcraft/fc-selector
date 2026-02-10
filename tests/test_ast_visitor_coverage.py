from fc_selector.core.ast import nodes
from fc_selector.core.ast.visitor import NodeVisitor


def test_node_visitor_generic_visit_traverses_lists_and_nodes():
    class Counter(NodeVisitor):
        def __init__(self):
            self.ids = []
        def visit_Identifier(self, node: nodes.Identifier):
            self.ids.append(node.name)
        # rely on generic_visit for list fields

    ast = nodes.BoolOp(
        op=nodes.And(),
        left=nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="a"),
            right=nodes.String(val="x"),
        ),
        right=nodes.BoolOp(
            op=nodes.Or(),
            left=nodes.Identifier(name="b"),
            right=nodes.Identifier(name="c"),
        ),
    )

    Counter().visit(ast)

    c = Counter()
    c.visit(ast)
    assert set(c.ids) == {"a", "b", "c"}
