from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.services import notify

from .models import Consultation


@receiver(post_save, sender=Consultation)
def consultation_saved(sender, instance, created, **kwargs):
    """Сигнал: после сохранения консультации отправляем уведомления."""
    url = instance.get_absolute_url()
    if created:
        notify(instance.vet.user, f"Новая запись: {instance.animal.name}, "
                                  f"{timezone.localtime(instance.scheduled_at):%d.%m %H:%M}", url)
    elif instance.status == Consultation.Status.DONE:
        notify(instance.farmer.user, f"Врач завершил консультацию по «{instance.animal.name}»: "
                                     f"{instance.diagnosis}", url)
    elif instance.status == Consultation.Status.CANCELLED:
        notify(instance.vet.user, f"Запись по «{instance.animal.name}» отменена", url)
