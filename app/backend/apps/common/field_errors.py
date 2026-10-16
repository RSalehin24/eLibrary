from collections.abc import Mapping


def error_messages(value):
    if isinstance(value, Mapping):
        return [
            f"{field}: {message}"
            for field, child in value.items()
            for message in error_messages(child)
        ]
    if isinstance(value, (list, tuple)):
        return [message for child in value for message in error_messages(child)]
    return [str(value)]


def normalized_field_errors(detail):
    fields = detail if isinstance(detail, Mapping) else {"non_field_errors": detail}
    return {field: error_messages(value) for field, value in fields.items()}
