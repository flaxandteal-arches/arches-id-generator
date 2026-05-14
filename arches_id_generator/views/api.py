from django.contrib.auth.mixins import LoginRequiredMixin

from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_id_generator.models import IdSequence
from arches_id_generator.utils.validation import validate_key


class IdSequenceView(LoginRequiredMixin, APIBase):
    """Read or seed an IdSequence by key. Refuses edits once the sequence
    has been used (start_number != next_number).
    """

    def get(self, request, key):
        sequence = IdSequence.objects.filter(pk=key).first()
        if not sequence:
            return JSONErrorResponse(
                "IdSequence not found for the given key.",
                status=404,
            )
        return JSONResponse(sequence)

    def post(self, request, key):
        try:
            validate_key(key)
        except ValueError as exc:
            return JSONErrorResponse(str(exc), status=400)

        request_json = JSONDeserializer().deserialize(request.body)
        start_number = request_json.get("start_number", 1)

        sequence = IdSequence.objects.filter(pk=key).first()

        if sequence:
            if sequence.start_number != sequence.next_number:
                return JSONErrorResponse(
                    "IdSequence cannot be edited because it has already been used.",
                    status=400,
                )
            sequence.start_number = start_number
            sequence.next_number = start_number
            sequence.save(update_fields=["start_number", "next_number", "updated_at"])
            return JSONResponse(sequence)

        sequence = IdSequence.objects.create(
            pk=key,
            start_number=start_number,
            next_number=start_number,
        )
        return JSONResponse(sequence)
