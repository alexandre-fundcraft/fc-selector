import sys

import django
from django.conf import settings

# Setup minimal django
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
            "fc_selector",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    )
    django.setup()

try:
    from fc_selector.django.drf.viewsets import ODataModelViewSet

    print("✓ Tots els components de DRF s'han importat correctament des de la nova estructura modular.")

    # Verificar que ODataModelViewSet hereta del que toca (via la nova estructura)
    print(f"✓ ODataModelViewSet hereta de: {[c.__name__ for c in ODataModelViewSet.__mro__[:3]]}")

except Exception as e:
    print(f"✗ Error d'importació: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
