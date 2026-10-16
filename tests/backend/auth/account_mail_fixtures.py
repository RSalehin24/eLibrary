from uuid import uuid4


def invite_values():
    return {
        "operation_id": str(uuid4()),
        "email": "NEW-Reader@Library.test",
        "full_name": "আমন্ত্রিত পাঠক",
        "totp_required": True,
    }
