from django.urls import path

from arches_id_generator.views import GenerateIdView

app_name = "arches_id_generator"

urlpatterns = [
    path("id-generator/generate", GenerateIdView.as_view(), name="generate"),
]
