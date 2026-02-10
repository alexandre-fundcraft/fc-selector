from fc_selector.core.ast import nodes
from fc_selector.core.ast.visitor import NodeTransformer
from fc_selector.core.dtos.utils import get_dto_fields


def test_get_dto_fields_none_class():
    assert get_dto_fields(None) == []


def test_get_dto_fields_plain_class_no_annotations():
    class Plain:
        pass

    assert get_dto_fields(Plain) == []


def test_node_transformer_generic_visit_rebuilds_children():
    class Upper(NodeTransformer):
        def visit_String(self, node: nodes.String):
            return nodes.String(val=node.val.upper())

    ast = nodes.Compare(
        comparator=nodes.Eq(),
        left=nodes.Identifier(name="field"),
        right=nodes.String(val="value"),
    )

    transformed = Upper().visit(ast)
    assert isinstance(transformed, nodes.Compare)
    assert isinstance(transformed.right, nodes.String)
    assert transformed.right.val == "VALUE"
