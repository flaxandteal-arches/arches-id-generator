from django.urls import path

from arches_id_generator.views.api import IdSequenceView


urlpatterns = [
    path(
        "api/id-sequence/<str:key>",
        IdSequenceView.as_view(),
        name="api-id-sequence",
    ),
]
