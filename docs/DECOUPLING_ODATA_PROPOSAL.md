# Proposta d'Arquitectura: Desacoblament de Selectors i OData

## Estat Actual
Actualment, el sistema de `Selectors` està fortament acoblat al protocol OData. Per realitzar consultes, el programador ha de construir expressions en format string d'OData, fins i tot quan treballa internament des del codi Python.

**Exemple d'acoblament:**
```python
selector = BlogPostSelector()
query = ODataQueryBuilder().filter("status eq 'published'") # <-- String OData
if author_id:
    query.and_filter(f"author/id eq {author_id}") # <-- String OData
return selector.get_many(query)
```

## El Problema
1. **Reutilització limitada:** No es pot fer servir el selector fàcilment des de tasques en segon pla (Celery), scripts CLI o altres protocols (GraphQL, RPC) sense "parlar" OData.
2. **Dependència del Parser:** Qualsevol canvi en la gramàtica d'OData afecta la lògica interna de l'aplicació.
3. **Violació del DIP:** La capa de domini/negoci (Selector) depèn d'una implementació d'infraestructura (OData).

## Proposta de Solució: Patró Repository + Adapter

Separar la lògica en dues capes clarament diferenciades.

### 1. Capa de Repositori (Pur Python/Django)
Aquesta capa no sap res d'OData. Accepta objectes `Q` de Django, diccionaris o arguments tipats.

```python
class BlogPostRepository:
    def get_many(self, filters=None, select_fields=None, order_by=None):
        queryset = BlogPost.objects.all()
        # Lògica pura de Django
        if filters: queryset = queryset.filter(filters)
        if select_fields: queryset = queryset.only(*select_fields)
        return queryset
```

### 2. Capa d'Adaptador OData (Infraestructura)
Aquesta capa és l'única que coneix OData. La seva feina és traduir el protocol OData a les crides del repositori.

```python
class ODataSelector(BaseSelector): # Actua com a adaptador
    def query_as_dtos(self, query_string: str):
        # 1. Parseja OData -> AST
        # 2. Transforma AST -> Django Q
        # 3. Crida al Repositori intern
        pass
```

## Beneficis
- **Flexibilitat:** El mateix `Repository` pot alimentar una API OData, una API REST estàndard i un script d'administració.
- **Mantenibilitat:** Podem canviar o actualitzar el parser d'OData sense tocar la lògica de base de dades.
- **Testabilitat:** Podem fer tests unitaris del Repositori sense la sobrecàrrega del parser.

---
*Document creat el 22 de desembre de 2025 per a discussió futura.*
