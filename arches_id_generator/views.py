import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View

from arches_id_generator.services.generator import generate_id

@method_decorator(login_required, name="dispatch")
class GenerateIdView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest("Invalid JSON body")

        sequence_key = payload.get("sequence_key")
        template = payload.get("template")

        if not sequence_key or not template:
            return HttpResponseBadRequest(
                "Both 'sequence_key' and 'template' are required"
            )

        try:
            value = generate_id(sequence_key, template)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))

        return JsonResponse({"id": value})