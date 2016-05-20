from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djcelery.models import PeriodicTask

from django.utils import timezone
from django.db.models import DateTimeField
from django.conf import settings

from go_http.send import HttpApiSender as sendHttpApiSender
from south.modelsinspector import add_introspection_rules


# Modelled on https://github.com/jamesmarlowe/django-AutoDateTimeFields
# But with timezone support
class AutoDateTimeField(DateTimeField):

    def pre_save(self, model_instance, add):
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class AutoNewDateTimeField(DateTimeField):

    def pre_save(self, model_instance, add):
        if not add:
            return getattr(model_instance, self.attname)
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class MessageSet(models.Model):

    """ Core details about a set of messages that a user
        can be sent
    """
    short_name = models.CharField(max_length=20)
    notes = models.TextField(verbose_name=u'Notes', null=True, blank=True)
    next_set = models.ForeignKey('self',
                                 null=True,
                                 blank=True)
    default_schedule = models.ForeignKey(PeriodicTask,
                                         related_name='message_sets',
                                         null=False)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.short_name


class Message(models.Model):

    """ A message that a user can be sent
    """
    message_set = models.ForeignKey(MessageSet,
                                    related_name='messages',
                                    null=False)
    sequence_number = models.IntegerField(null=False, blank=False)
    lang = models.CharField(max_length=3, null=False, blank=False)
    content = models.TextField(null=False, blank=False)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "Message %s in %s from %s" % (self.sequence_number, self.lang,
                                             self.message_set.short_name)


class Subscription(models.Model):

    """ Users subscriptions and their status
    """
    user_account = models.CharField(max_length=36, null=False, blank=False)
    contact_key = models.CharField(max_length=36, null=False, blank=False)
    to_addr = models.CharField(max_length=255, null=False, blank=False)
    message_set = models.ForeignKey(MessageSet,
                                    related_name='subscribers',
                                    null=False)
    next_sequence_number = models.IntegerField(default=1, null=False,
                                               blank=False)
    lang = models.CharField(max_length=3, null=False, blank=False)
    active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)
    schedule = models.ForeignKey(PeriodicTask,
                                 related_name='subscriptions',
                                 null=False)
    process_status = models.IntegerField(default=0, null=False, blank=False)

    def __unicode__(self):
        return "%s to %s" % (self.contact_key, self.message_set.short_name)

add_introspection_rules([], ["^subscription\.models\.AutoNewDateTimeField",
                             "^subscription\.models\.AutoDateTimeField"])

# Auth set up stuff to ensure apikeys are created
# ensures endpoints require username and api_key values to access
from django.contrib.auth import get_user_model  # noqa
user_model = get_user_model()


# workaround for https://github.com/toastdriven/django-tastypie/issues/937
@receiver(post_save, sender=user_model)
def create_user_api_key(sender, **kwargs):
    from tastypie.models import create_api_key
    create_api_key(user_model, **kwargs)


@receiver(post_save, sender=Subscription)
def send_optional_first_message(sender, instance, created, **kwargs):
    if created and settings.SUBSCRIPTION_SEND_INITIAL_DELAYED > 0:
        from subscription.tasks import processes_message
        api_client = sendHttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )

        processes_message.apply_async(
            args=[instance.id, api_client],
            countdown=settings.SUBSCRIPTION_SEND_INITIAL_DELAYED)
