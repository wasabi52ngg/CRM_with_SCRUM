IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
CHAT_UPLOAD_MAX_BYTES = 10 * 1024 * 1024


def is_chat_image(file_field) -> bool:
    if not file_field:
        return False
    name = (getattr(file_field, "name", "") or "").lower()
    return name.endswith(IMAGE_EXTENSIONS)


def chat_upload_too_large(uploaded) -> bool:
    return bool(uploaded and uploaded.size > CHAT_UPLOAD_MAX_BYTES)


def request_message_upload_to(instance, filename: str) -> str:
    return f"chat/requests/{instance.request_id}/{filename}"


def task_comment_upload_to(instance, filename: str) -> str:
    return f"chat/tasks/{instance.task_id}/{filename}"


def attachment_api_fields(file_field, request) -> dict:
    if not file_field:
        return {
            "attachment_url": "",
            "attachment_name": "",
            "attachment_is_image": False,
        }
    return {
        "attachment_url": request.build_absolute_uri(file_field.url),
        "attachment_name": file_field.name.rsplit("/", 1)[-1],
        "attachment_is_image": is_chat_image(file_field),
    }
