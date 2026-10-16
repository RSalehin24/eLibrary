from rest_framework.exceptions import ValidationError


def reject_unknown_fields(serializer):
    reject_unknown_input(serializer, serializer.initial_data)


def reject_unknown_input(serializer, data):
    if not isinstance(data, dict):
        return
    unknown = set(data) - set(serializer.fields)
    if unknown:
        raise ValidationError({field: "Unknown field." for field in unknown})
