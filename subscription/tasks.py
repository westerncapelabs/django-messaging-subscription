from celery import task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from go_http import HttpApiSender
from go_http.send import HttpApiSender as sendHttpApiSender
import csv
from .models import Message, Subscription
from django.conf import settings
from django.db import IntegrityError, transaction, connection
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist
import logging

standard_logger = logging.getLogger(__name__)
celery_logger = get_task_logger(__name__)


@task()
def ingest_csv(csv_data, message_set):
    """ Expecting data in the following format:
    message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,ss,safe,st,safe,nso,safe,nr,safe
    """
    records = csv.DictReader(csv_data)
    for line in records:
        for key in line:
            # Ignore non-content keys and empty keys
            if key not in ["message_id", "safe"] and line[key] != "":
                try:
                    with transaction.atomic():
                        message = Message()
                        message.message_set = message_set
                        message.sequence_number = line["message_id"]
                        message.lang = key
                        message.content = line[key]
                        message.save()
                except (IntegrityError, ValueError) as e:
                    message = None
                    # crappy CSV data
                    standard_logger.error(e)


@task()
def ensure_one_subscription():
    """
    Fixes issues caused by upstream failures
    that lead to users having multiple active subscriptions
    Runs daily
    """
    cursor = connection.cursor()
    cursor.execute("UPDATE subscription_subscription SET active = False \
                    WHERE id NOT IN \
                   (SELECT MAX(id) as id FROM \
                    subscription_subscription GROUP BY to_addr)")
    affected = cursor.rowcount
    vumi_fire_metric.delay(
        metric="subscription.duplicates", value=affected, agg="last")
    return affected


@task()
def vumi_fire_metric(metric, value, agg, sender=None):
    try:
        if sender is None:
            sender = HttpApiSender(
                account_key=settings.VUMI_GO_ACCOUNT_KEY,
                conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
                conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
            )
        sender.fire_metric(metric, value, agg=agg)
        return sender
    except SoftTimeLimitExceeded:
        standard_logger.error(
            'Soft time limit exceed processing metric fire to Vumi \
            HTTP API via Celery',
            exc_info=True)


@task()
def process_message_queue(schedule, sender=None):
    # Get all active and incomplete subscriptions for schedule
    subscriptions = Subscription.objects.filter(
        schedule=schedule, active=True, completed=False,
        process_status=0).all()

    # Make a reusable session to Vumi
    if sender is None:
        sender = sendHttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )
        # sender = LoggingSender('go_http.test')
        # Fire off message processor for each
    for subscription in subscriptions:
        subscription.process_status = 1  # In Proceses
        subscription.save()
        processes_message.delay(subscription.id, sender)
    return subscriptions.count()


@task()
def processes_message(subscription_id, sender):
    try:
        # Get next message
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            message = Message.objects.get(
                message_set=subscription.message_set, lang=subscription.lang,
                sequence_number=subscription.next_sequence_number)
            # Send messages
            messages = message.content.split(
                settings.SUBSCRIPTION_MULTIPART_BOUNDARY)
            if len(messages) == 1:
                response = sender.send_text(
                    subscription.to_addr, message.content)
            else:
                response = []
                for text in messages:
                    response.append(
                        sender.send_text(subscription.to_addr, text.strip()))
            # Post process moving to next message, next set or finished
            # Get set max
            set_max = Message.objects.filter(
                message_set=subscription.message_set
            ).aggregate(Max('sequence_number'))["sequence_number__max"]
            # Compare user position to max
            if subscription.next_sequence_number == set_max:
                # Mark current as completed
                subscription.completed = True
                subscription.active = False
                subscription.process_status = 2  # Completed
                subscription.save()
                # fire completed metric
                vumi_fire_metric.delay(
                    metric="sum.%s_completed" %
                    (subscription.message_set.short_name, ),
                    value=1, agg="sum", sender=sender)
                # If next set defined create new subscription
                message_set = subscription.message_set
                if message_set.next_set:
                    # clone existing minus PK as recommended in
                    # https://docs.djangoproject.com/en/1.6/topics/db/queries/#copying-model-instances
                    subscription.pk = None
                    subscription.process_status = 0  # Ready
                    subscription.active = True
                    subscription.completed = False
                    subscription.next_sequence_number = 1
                    subscription_new = subscription
                    subscription_new.message_set = message_set.next_set
                    subscription_new.schedule = (
                        message_set.next_set.default_schedule)
                    subscription_new.save()
                else:
                    vumi_fire_metric.delay(
                        metric="sum.finished_messages",
                        value=1, agg="sum", sender=sender)
            else:
                # More in this set so interate by one
                subscription.next_sequence_number = \
                    subscription.next_sequence_number + 1
                subscription.process_status = 0  # Ready
                subscription.save()
            return response
        except ObjectDoesNotExist:
            subscription.process_status = -1  # Errored
            subscription.save()
            celery_logger.error('Missing subscription message', exc_info=True)
    except SoftTimeLimitExceeded:
        celery_logger.error(
            'Soft time limit exceed processing message to Vumi \
            HTTP API via Celery',
            exc_info=True)
