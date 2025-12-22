"""
Tests for ODataSelector field aliases functionality.
"""




class TestAliasResolution:
    """Tests for alias resolution methods."""

    def test_resolve_alias_simple(self):
        """Test resolving a simple alias."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                    'lastName': 'last_name',
                }

        selector = TestSelector()
        assert selector._resolve_alias('firstName') == 'first_name'
        assert selector._resolve_alias('lastName') == 'last_name'
        assert selector._resolve_alias('id') == 'id'  # No alias

    def test_resolve_alias_with_relation(self):
        """Test resolving alias that references related field."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'authorName': 'author__username',
                    'authorEmail': 'author__email',
                }

        selector = TestSelector()
        assert selector._resolve_alias('authorName') == 'author__username'
        assert selector._resolve_alias('authorEmail') == 'author__email'

    def test_resolve_alias_reverse(self):
        """Test reverse alias resolution (internal -> alias)."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                    'authorName': 'author__username',
                }

        selector = TestSelector()
        assert selector._resolve_alias_reverse('first_name') == 'firstName'
        assert selector._resolve_alias_reverse('author__username') == 'authorName'
        assert selector._resolve_alias_reverse('id') == 'id'  # No alias


class TestSelectAliasResolution:
    """Tests for $select alias resolution."""

    def test_resolve_aliases_in_select_simple(self):
        """Test resolving aliases in $select."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                    'lastName': 'last_name',
                    'createdAt': 'created_at',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_select('id,firstName,lastName')
        assert result == 'id,first_name,last_name'

    def test_resolve_aliases_in_select_with_relations(self):
        """Test resolving relation aliases in $select."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'authorName': 'author__username',
                    'authorEmail': 'author__email',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_select('id,title,authorName,authorEmail')
        assert result == 'id,title,author__username,author__email'

    def test_resolve_aliases_in_select_no_aliases(self):
        """Test $select with no aliases defined."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None

        selector = TestSelector()
        result = selector._resolve_aliases_in_select('id,title,content')
        assert result == 'id,title,content'


class TestFilterAliasResolution:
    """Tests for $filter alias resolution."""

    def test_resolve_aliases_in_filter_simple(self):
        """Test resolving aliases in simple filter."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_filter("firstName eq 'John'")
        assert result == "first_name eq 'John'"

    def test_resolve_aliases_in_filter_with_relation(self):
        """Test resolving relation aliases in filter."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'authorName': 'author__username',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_filter("authorName eq 'john'")
        assert result == "author__username eq 'john'"

    def test_resolve_aliases_in_filter_complex(self):
        """Test resolving aliases in complex filter with AND/OR."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'authorName': 'author__username',
                    'createdAt': 'created_at',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_filter(
            "authorName eq 'john' and createdAt gt 2024-01-01"
        )
        assert "author__username eq 'john'" in result
        assert "created_at gt 2024-01-01" in result

    def test_resolve_aliases_in_filter_preserves_string_values(self):
        """Test that aliases inside string values are not replaced."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'name': 'full_name',
                }

        selector = TestSelector()
        # 'name' inside the string should NOT be replaced
        result = selector._resolve_aliases_in_filter("title eq 'My name is John'")
        assert result == "title eq 'My name is John'"

    def test_resolve_aliases_in_filter_no_partial_match(self):
        """Test that partial field names are not replaced."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'name': 'full_name',
                }

        selector = TestSelector()
        # 'username' should NOT be affected by 'name' alias
        result = selector._resolve_aliases_in_filter("username eq 'john'")
        assert result == "username eq 'john'"


class TestOrderByAliasResolution:
    """Tests for $orderby alias resolution."""

    def test_resolve_aliases_in_orderby_simple(self):
        """Test resolving aliases in $orderby."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'createdAt': 'created_at',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_orderby('createdAt desc')
        assert result == 'created_at desc'

    def test_resolve_aliases_in_orderby_multiple(self):
        """Test resolving multiple aliases in $orderby."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'createdAt': 'created_at',
                    'authorName': 'author__username',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_orderby('createdAt desc,authorName asc')
        assert result == 'created_at desc,author__username asc'

    def test_resolve_aliases_in_orderby_no_direction(self):
        """Test resolving aliases without direction specified."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'createdAt': 'created_at',
                }

        selector = TestSelector()
        result = selector._resolve_aliases_in_orderby('createdAt')
        assert result == 'created_at'


class TestQueryStringAliasResolution:
    """Tests for full query string alias resolution."""

    def test_resolve_aliases_in_query_string_all_params(self):
        """Test resolving aliases in full query string."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                    'createdAt': 'created_at',
                    'authorName': 'author__username',
                }

        selector = TestSelector()
        query = "$select=id,firstName&$filter=authorName eq 'john'&$orderby=createdAt desc"
        result = selector._resolve_aliases_in_query_string(query)

        assert '$select=id,first_name' in result
        assert "$filter=author__username eq 'john'" in result
        assert '$orderby=created_at desc' in result

    def test_resolve_aliases_preserves_other_params(self):
        """Test that non-alias parameters are preserved."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                }

        selector = TestSelector()
        query = "$select=firstName&$top=10&$skip=5"
        result = selector._resolve_aliases_in_query_string(query)

        assert '$select=first_name' in result
        assert '$top=10' in result
        assert '$skip=5' in result


class TestRelatedFieldsExtraction:
    """Tests for extracting related fields from aliases."""

    def test_get_related_fields_from_aliases(self):
        """Test extracting related field names from alias values."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'authorName': 'author__username',
                    'authorEmail': 'author__email',
                    'categoryName': 'category__name',
                    'firstName': 'first_name',  # Not a relation
                }

        selector = TestSelector()
        related = selector._get_related_fields_from_aliases([
            'authorName', 'authorEmail', 'categoryName', 'firstName'
        ])

        assert 'author' in related
        assert 'category' in related
        assert 'first_name' not in related  # Not a relation
        assert len(related) == 2

    def test_get_related_fields_empty(self):
        """Test with no relation aliases."""
        from fc_selector.django.selector import ODataSelector

        class TestSelector(ODataSelector):
            class Meta:
                model = None
                field_aliases = {
                    'firstName': 'first_name',
                    'lastName': 'last_name',
                }

        selector = TestSelector()
        related = selector._get_related_fields_from_aliases(['firstName', 'lastName'])
        assert len(related) == 0
