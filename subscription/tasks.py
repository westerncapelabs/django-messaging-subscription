from celery import task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from go_http import HttpApiSender
from go_http.send import HttpApiSender as sendHttpApiSender
import csv
from subscription.models import Message, Subscription
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
    cursor.execute("UPDATE subscription_subscription SET active = False WHERE id NOT IN \
              (SELECT MAX(id) as id FROM subscription_subscription GROUP BY to_addr)")
    affected = cursor.rowcount
    vumi_fire_metric.delay(metric="subscription.duplicates", value=affected, agg="last")
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
        standard_logger.error('Soft time limit exceed processing metric fire to Vumi HTTP API via Celery', exc_info=True)


@task()
def process_message_queue(schedule, sender=None):
    # Get all active and incomplete subscribers for schedule
    subscribers = Subscription.objects.filter(
        schedule=schedule, active=True, completed=False, process_status=0).all()

    # Make a reusable session to Vumi
    if sender is None:
        sender = sendHttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )
        # sender = LoggingSender('go_http.test')
            # Fire off message processor for each
    for subscriber in subscribers:
        subscriber.process_status = 1 # In Proceses
        subscriber.save()
        processes_message.delay(subscriber, sender)
    return subscribers.count()


@task()
def processes_message(subscriber, sender):
    try:
        # Get next message
        try:
            message = Message.objects.get(
                message_set=subscriber.message_set, lang=subscriber.lang,
                sequence_number=subscriber.next_sequence_number)
            # Send message
            response = sender.send_text(subscriber.to_addr, message.content)
            # Post process moving to next message, next set or finished
            # Get set max
            set_max = Message.objects.all().aggregate(Max('sequence_number'))["sequence_number__max"]
            # Compare user position to max
            if subscriber.next_sequence_number == set_max:
                # Mark current as completed
                subscriber.completed = True
                subscriber.active = False
                subscriber.process_status = 2 # Completed
                subscriber.save()
                # If next set defined create new subscription
                message_set = subscriber.message_set
                if message_set.next_set:
                    # clone existing minus PK as recommended in
                    # https://docs.djangoproject.com/en/1.6/topics/db/queries/#copying-model-instances
                    subscriber.pk = None
                    subscriber.process_status = 0 # Ready
                    subscriber.active = True
                    subscriber.completed = False
                    subscriber.next_sequence_number = 1
                    subscription = subscriber
                    subscription.message_set = message_set.next_set
                    subscription.save()
            else:
                # More in this set so interate by one
                subscriber.next_sequence_number = subscriber.next_sequence_number + 1
                subscriber.process_status = 0 # Ready
                subscriber.save()
            return response
        except ObjectDoesNotExist:
            subscriber.process_status = -1 # Errored
            subscriber.save()
            celery_logger.error('Missing subscription message', exc_info=True)
    except SoftTimeLimitExceeded:
        celery_logger.error('Soft time limit exceed processing message to Vumi HTTP API via Celery', exc_info=True)
