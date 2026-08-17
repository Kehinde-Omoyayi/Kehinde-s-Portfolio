from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Project, Dashboard, Certificate, Publication, Recommendation

import logging

logger = logging.getLogger(__name__)

def _log(activity_type, message, url="", obj=None):
    logger.info("[%s] %s", activity_type.upper(), message)

@receiver(post_save, sender=Project)
def log_project_activity(sender, instance, created, **kwargs):
    if created:
        _log("project", instance.name, instance.get_absolute_url(), instance)


@receiver(post_save, sender=Dashboard)
def log_dashboard(sender, instance, created, **kwargs):
    if created and instance.is_published:
        _log("dashboard", f"Published new dashboard: {instance.title}", instance.get_absolute_url(), instance)


@receiver(post_save, sender=Certificate)
def log_certificate(sender, instance, created, **kwargs):
    if created and instance.is_visible:
        _log("certificate", f"Earned new certificate: {instance.title}", "", instance)


@receiver(post_save, sender=Publication)
def log_research(sender, instance, created, **kwargs):
    if created and instance.is_published:
        _log("research", f"Published research paper: {instance.title}", instance.get_absolute_url(), instance)


@receiver(post_save, sender=Recommendation)
def log_recommendation(sender, instance, created, **kwargs):
    if created and instance.is_visible:
        _log("recommendation", f"Received a new recommendation from {instance.name}", "", instance)