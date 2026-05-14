from arches_id_generator.template import render
from arches_id_generator.utils.validation import validate_key


def generate_id(sequence_key, template_string, exists_check_fn=None):
    """Validate the key and render the template into a concrete ID string."""
    validate_key(sequence_key)
    return render(
        template_string,
        scope_key=sequence_key,
        exists_check_fn=exists_check_fn,
    )
