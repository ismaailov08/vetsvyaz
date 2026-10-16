from .models import Notification


def notify(user, text, url=""):
    """Создать уведомление пользователю (колокольчик в шапке сайта)."""
    return Notification.objects.create(user=user, text=text[:255], url=url)
