from apps.notifications.models import Notification


def send_notification(recipient_id: int, verb: str, data: dict = None):
    Notification.objects.create(
        recipient_id=recipient_id,
        verb=verb,
        data=data or {},
    )


def notify_moderation_result(user_id: int, status: str, modality: str):
    verb = f'Your {modality} content was {status.lower()} by moderation.'
    send_notification(user_id, verb, {'status': status, 'modality': modality})
