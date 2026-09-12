"""Observable contracts from openspec/changes/fix-audit-findings."""

from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit
from xml.etree import ElementTree

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from rest_framework.test import APIRequestFactory

from example.blog.dto_serializers import AuthorDTOSerializer
from example.blog.models import Author, BlogPost
from example.blog.selectors.blog_post import AuthorDTO, UserDTO
from example.blog.viewsets_fluent import AuthorViewSet
from fc_selector.core import QueryBuilder
from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.exceptions import QueryError
from fc_selector.core.filters import Expand, Field
from fc_selector.django.drf.serializers import ODataDTOSerializer
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin, build_odata_response
from fc_selector.django.hybrid_values_builder import HybridValuesBuilder
from fc_selector.django.selector import ODataSelector
from fc_selector.django.views.metadata import ODataMetadataRegistry, ODataMetadataView
from fc_selector.protocols.odata.parsers.query import parse_odata_query
from tests.integration.support.models import (
    ODataChildModel,
    ODataFKTarget,
    ODataM2MTarget,
    ODataModelWithFK,
    ODataModelWithRelations,
)
from tests.test_hybrid_values_builder import (
    ChildDTO,
    FKSelector,
    FKTargetDTO,
    M2MTargetDTO,
    ModelWithFKDTO,
    ParentWithRelationsDTO,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def rows():
    target = ODataFKTarget.objects.create(name="Target", code="T")
    return [ODataModelWithFK.objects.create(title=f"Row{i}", value=i, target=target) for i in range(3)]


@pytest.fixture
def parents():
    result = []
    tags = [ODataM2MTarget.objects.create(name=name) for name in ["A", "Z"]]
    for i in range(2):
        parent = ODataModelWithRelations.objects.create(title=f"Parent{i}")
        for score in range(3):
            ODataChildModel.objects.create(parent=parent, label=f"Child{i}-{score}", score=score)
        parent.tags.add(*tags)
        result.append(parent)
    return result


class ParentSelector(ODataSelector):
    class Meta:
        model = ODataModelWithRelations
        dto_class = ParentWithRelationsDTO
        expandable_fields = {"children": ChildDTO, "tags": M2MTargetDTO, "target": FKTargetDTO}


class SmallSelector(FKSelector):
    class Meta(FKSelector.Meta):
        default_limit = 1
        max_limit = 2


class RowSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = ModelWithFKDTO


class RowViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    selector_class = SmallSelector
    serializer_class = RowSerializer
    odata_entity_set_name = "rows"
    authentication_classes = []
    permission_classes = []


def test_mixed_filter_composition_and_pk(rows):
    selector = FKSelector()
    query = QueryBuilder().where(Field("value").ge(0)).and_filter(f"id eq {rows[1].pk}")
    assert [r.id for r in selector.get_many(query)] == [rows[1].pk]
    query.filter("value eq 2")
    assert [r.value for r in selector.get_many(query)] == [2]
    query = QueryBuilder().where(Field("value").eq(0)).or_filter("value eq 2")
    assert {r.value for r in selector.get_many(query)} == {0, 2}
    query = QueryBuilder().where(Field("value").ge(0))
    assert selector.get_by_pk(rows[1].pk, query).id == rows[1].pk
    assert len(selector.get_many(query)) == 3  # lookup must not mutate caller's builder


@pytest.mark.parametrize("literal", ["A+B", "A&B", "A%2BB", "O'Brien"])
def test_url_literal_preserved(rows, literal):
    rows[0].title = literal
    rows[0].save()
    raw = urlencode({"$filter": "title eq '" + literal.replace("'", "''") + "'"})
    assert len(FKSelector().query_as_dtos(raw)) == 1
    assert len(FKSelector().get_many(QueryBuilder(raw))) == 1


def test_builder_nested_options():
    raw = "$expand=children($select=label;$filter=score gt 0;$top=1;$expand=category($select=name)),tags"
    assert QueryBuilder(raw).build().expand == parse_odata_query(raw).expand


@pytest.mark.parametrize("raw,expected", [("", 1), ("$skip=0", 1), ("$top=3", 2), ("$top=0", 0)])
def test_collection_limits(rows, raw, expected):
    s = SmallSelector()
    assert len(s.query_as_dtos(raw)) == expected
    assert len(s.query_as_dicts(raw)) == expected
    assert len(s.get_many(QueryBuilder(raw))) == expected
    assert len(s.get_many_dicts(QueryBuilder(raw))) == expected
    assert s.count_by(QueryBuilder().top(1)) == 3


@pytest.mark.parametrize("mode", [True, False])
@pytest.mark.parametrize("query", ["$select=value", "$filter=value eq 1", "$orderby=rank", "$expand=second_target"])
def test_field_policies(rows, mode, query):
    class Restricted(FKSelector):
        class Meta(FKSelector.Meta):
            values_mode = mode
            allowed_fields = ["id", "title", "target"]
            non_filterable_fields = ["value"]
            non_sortable_fields = ["value"]
            field_aliases = {"rank": "value"}
            expandable_fields = {"target": FKTargetDTO}

    with pytest.raises(QueryError):
        Restricted().query_as_dtos(query)


def test_filter_policy_independent_of_select(rows):
    class Restricted(FKSelector):
        class Meta(FKSelector.Meta):
            filterable_fields = ["title"]

    with pytest.raises(QueryError):
        Restricted().query_as_dtos("$filter=value eq 1")


def test_sensitive_serialization():
    class SensitiveSerializer(ODataDTOSerializer):
        class Meta:
            dto_class = UserDTO
            extra_kwargs = {"email": {"write_only": True}}

    assert dict(SensitiveSerializer(UserDTO(password="fake", email="private")).data) == {}
    assert "password" not in AuthorDTOSerializer(AuthorDTO(user=UserDTO(password="fake"))).data["user"]


def test_dto_exclusions_apply_at_root_and_nested():
    @dataclass
    class SecretDTO(BaseODataDTO):
        _excluded_fields = {"secret"}
        secret: str = "fake"
        name: str = "public"

    class SecretSerializer(ODataDTOSerializer):
        class Meta:
            dto_class = SecretDTO

    assert dict(SecretSerializer(SecretDTO()).data) == {"name": "public"}
    assert SecretSerializer()._dto_to_dict(SecretDTO()) == {"name": "public"}


def test_object_permissions_receive_model(rows):
    class Deny(BasePermission):
        def has_object_permission(self, request, view, obj):
            assert isinstance(obj, ODataModelWithFK)
            return False

    class DeniedView(RowViewSet):
        permission_classes = [Deny]

    response = DeniedView.as_view({"get": "retrieve"})(APIRequestFactory().get("/rows/1/"), pk=rows[0].pk)
    assert response.status_code == 403


def test_view_scope_and_count(rows):
    class ScopedView(RowViewSet):
        def get_queryset(self):
            return ODataModelWithFK.objects.filter(value__gt=0)

        def filter_queryset(self, queryset):
            return queryset.filter(value=2)

    f = APIRequestFactory()
    response = ScopedView.as_view({"get": "list"})(f.get("/rows/?$count=true"))
    assert [row["value"] for row in response.data["value"]] == [2]
    assert response.data["@odata.count"] == 1
    response = ScopedView.as_view({"get": "retrieve"})(f.get("/rows/1/"), pk=rows[0].pk)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "raw",
    [
        "$filter=title eq",
        "$orderby=missing",
        "$filter=unknown_func(title)",
        "$top=-1",
        "$expand=target(",
        "$expand=target($top=1)",
    ],
)
@pytest.mark.parametrize("action", ["list", "retrieve"])
def test_api_invalid_input_is_400(rows, raw, action):
    response = RowViewSet.as_view({"get": action})(APIRequestFactory().get("/rows/?" + raw), pk=rows[0].pk)
    assert response.status_code == 400


@pytest.mark.parametrize("mode", [True, False])
def test_expansion_projection_pagination_and_order(parents, mode):
    s = ParentSelector()
    s.values_mode = mode
    raw = "$select=title&$expand=children($select=label;$orderby=score desc;$top=1;$skip=1),tags($orderby=name desc)"
    results = s.query_as_dtos(raw)
    for i, dto in enumerate(results):
        assert dto.id is UNSET
        assert [c.label for c in dto.children] == [f"Child{i}-1"]
        assert [t.name for t in dto.tags] == ["Z", "A"]
    dicts = s.query_as_dicts(raw)
    assert all(isinstance(row, dict) and "id" not in row for row in dicts)


def test_hybrid_children_without_pk(parents):
    rows = ParentSelector().query_as_dicts("$select=title&$expand=children")
    assert all(len(row["children"]) == 3 and "id" not in row for row in rows)


def test_fluent_expand_and_standard_query_count(rows):
    s = FKSelector()
    s.values_mode = False
    query = QueryBuilder().expand(Expand("target").select("name"))
    assert s.get_one(query).target.name == "Target"
    with CaptureQueriesContext(connection) as ctx:
        results = s.query_as_dtos("$expand=target")
    assert len(results) == 3
    assert len(ctx) == 1


def test_pagination_links_match_limits():
    request = APIRequestFactory().get("/rows/")
    raw = urlencode({"$filter": "title eq 'A&B'", "$top": 10})
    response = build_odata_response(request, [{}, {}], raw, "rows", selector=SmallSelector())
    parsed = parse_qs(urlsplit(response["@odata.nextLink"]).query)
    assert parsed["$skip"] == ["2"]
    assert parsed["$filter"] == ["title eq 'A&B'"]
    assert "@odata.nextLink" not in build_odata_response(request, [], "$top=0", "rows")


def test_metadata_uses_dto_aliases_and_exclusions():
    @dataclass
    class PublicDTO(BaseODataDTO):
        _excluded_fields = {"value"}
        id: int = UNSET
        label: str = UNSET
        value: int = UNSET

    class PublicSelector(FKSelector):
        class Meta(FKSelector.Meta):
            dto_class = PublicDTO
            field_aliases = {"label": "title"}
            allowed_fields = ["id", "label", "value"]
            expandable_fields = {}

    old = ODataMetadataRegistry.get_selectors()
    try:
        ODataMetadataRegistry.clear()
        ODataMetadataRegistry.register("public", PublicSelector)
        response = ODataMetadataView().get(APIRequestFactory().get("/$metadata"))
        root = ElementTree.fromstring(response.content)
        ns = {"edm": "http://docs.oasis-open.org/odata/ns/edm"}
        fields = {p.attrib["Name"] for p in root.findall(".//edm:Property", ns)}
        assert fields == {"id", "label"}
    finally:
        ODataMetadataRegistry.clear()
        for name, selector in old.items():
            ODataMetadataRegistry.register(name, selector)


def test_default_projection_respects_allowed_fields(rows):
    class Restricted(FKSelector):
        class Meta(FKSelector.Meta):
            allowed_fields = ["id", "title"]

    for raw in ["", "$select=*"]:
        assert Restricted().query_as_dtos(raw)[0].value is UNSET
        assert "value" not in Restricted().query_as_dicts(raw)[0]


def test_sortable_alias_positive_policy(rows):
    class Aliased(FKSelector):
        class Meta(FKSelector.Meta):
            field_aliases = {"rank": "value"}
            sortable_fields = ["rank"]

    assert [r.value for r in Aliased().query_as_dtos("$orderby=rank desc")] == [2, 1, 0]


def test_nested_serializer_policy():
    class ChildSerializer(ODataDTOSerializer):
        class Meta:
            dto_class = UserDTO
            exclude = ["email"]

    class ParentSerializer(AuthorDTOSerializer):
        class Meta(AuthorDTOSerializer.Meta):
            nested_serializers = {UserDTO: ChildSerializer}

    assert ParentSerializer(AuthorDTO(user=UserDTO(email="private", username="public"))).data["user"] == {
        "username": "public"
    }


def test_anonymous_example_does_not_expose_password():
    user = User.objects.create(username="audit", password="fake-password-hash")
    Author.objects.create(user=user)
    response = AuthorViewSet.as_view({"get": "list"})(APIRequestFactory().get("/odata/authors/?$expand=user"))
    assert response.status_code == 200
    assert "password" not in response.data["value"][0]["user"]


def test_fluent_string_conversion_cannot_silently_drop_conditions():
    query = QueryBuilder().where(Field("value").eq(1))
    for convert in (query.to_dict, query.build_query_string):
        with pytest.raises(ValueError, match="build"):
            convert()


def test_direct_hybrid_builder_limits_each_parent(parents):
    intent = parse_odata_query("$select=title&$expand=children($orderby=score desc;$top=1)")
    builder = HybridValuesBuilder(expandable_fields=ParentSelector.Meta.expandable_fields)
    results = builder.execute(ODataModelWithRelations.objects.all(), intent, ParentWithRelationsDTO)
    assert [[child.score for child in row.children] for row in results] == [[2], [2]]


@pytest.mark.parametrize("mode", [True, False])
def test_forward_nested_filter(rows, mode):
    selector = FKSelector()
    selector.values_mode = mode
    assert selector.query_as_dtos("$expand=target($filter=code eq 'absent')")[0].target is None


@pytest.mark.parametrize("mode", [True, False])
def test_nested_allowed_projection(parents, mode):
    class Restricted(ParentSelector):
        class Meta(ParentSelector.Meta):
            values_mode = mode
            expandable_fields = {"children": {"dto_class": ChildDTO, "allowed_fields": ["label"]}}

    assert all(
        child.score is UNSET for parent in Restricted().query_as_dtos("$expand=children") for child in parent.children
    )


def test_orderby_nested_negative_policy(rows):
    class Restricted(FKSelector):
        class Meta(FKSelector.Meta):
            non_sortable_fields = ["target/code"]

    with pytest.raises(QueryError):
        Restricted().query_as_dtos("$orderby=target/code")


def test_pk_lookup_is_not_a_client_filter(rows):
    class Restricted(FKSelector):
        class Meta(FKSelector.Meta):
            filterable_fields = ["title"]

    assert Restricted().get_by_pk(rows[1].pk).id == rows[1].pk


def test_dotted_alias_projection_and_filter(rows):
    @dataclass
    class PublicDTO(BaseODataDTO):
        id: int = UNSET
        display: str = UNSET

    class Aliased(FKSelector):
        class Meta(FKSelector.Meta):
            dto_class = PublicDTO
            field_aliases = {"display": "target.name"}
            allowed_fields = ["id", "display"]

    result = Aliased().query_as_dtos("$select=display&$filter=display eq 'Target'")
    assert [dto.display for dto in result] == ["Target"] * 3


@dataclass
class DeepUserDTO(BaseODataDTO):
    username: str = UNSET


@dataclass
class DeepAuthorDTO(BaseODataDTO):
    user: DeepUserDTO = UNSET


@dataclass
class DeepPostDTO(BaseODataDTO):
    author: DeepAuthorDTO = UNSET


@pytest.mark.parametrize("mode", [True, False])
def test_deep_forward_expand_preserves_shape_and_query_count(mode):
    user = User.objects.create(username="deep")
    author = Author.objects.create(user=user)
    for i in range(3):
        BlogPost.objects.create(author=author, title=f"Post{i}", slug=f"post-{i}")

    class DeepSelector(ODataSelector):
        class Meta:
            model = BlogPost
            dto_class = DeepPostDTO
            expandable_fields = {"author": DeepAuthorDTO}
            values_mode = mode

    with CaptureQueriesContext(connection) as ctx:
        results = DeepSelector().query_as_dtos("$expand=author($expand=user($select=username))")
    assert [row.author.user.username for row in results] == ["deep"] * 3
    assert len(ctx) == 2
