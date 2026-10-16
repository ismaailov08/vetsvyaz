def unread(request):
    """Добавляет в каждый шаблон число непрочитанных уведомлений."""
    if request.user.is_authenticated:
        return {"unread_count": request.user.notifications.filter(is_read=False).count()}
    return {"unread_count": 0}
