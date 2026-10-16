from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications",
                             verbose_name="получатель")
    text = models.CharField("текст", max_length=255)
    url = models.CharField("ссылка", max_length=200, blank=True)
    is_read = models.BooleanField("прочитано", default=False)
    created = models.DateTimeField("время", auto_now_add=True)

    class Meta:
        verbose_name = "уведомление"
        verbose_name_plural = "уведомления"
        ordering = ["-created"]

    def __str__(self):
        return self.text
