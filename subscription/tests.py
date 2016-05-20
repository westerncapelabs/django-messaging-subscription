"""
Tests for Subscription Application
"""
from tastypie.test import ResourceTestCase
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from subscription.models import MessageSet, Message, Subscription
from subscription.tasks import (ingest_csv,
                                vumi_fire_metric, process_message_queue,
                                processes_message)
from djcelery.models import PeriodicTask
from requests_testadapter import TestAdapter, TestSession
from go_http.send import LoggingSender, HttpApiSender
from StringIO import StringIO
import json
import logging


class SubscriptionResourceTest(ResourceTestCase):
    fixtures = ["test"]

    def setUp(self):
        super(SubscriptionResourceTest, self).setUp()

        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
                                             'testuser@example.com',
                                             self.password)
        self.api_key = self.user.api_key.key

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_data_loaded(self):
        self.assertEqual({
            "tasks": 6
        }, {
            "tasks": PeriodicTask.objects.all().count()
        })

    def test_get_list_unauthorzied(self):
        self.assertHttpUnauthorized(self.api_client.get(
                                    '/api/v1/subscription/',
                                    format='json'))

    def test_api_keys_created(self):
        self.assertEqual(True, self.api_key is not None)

    def test_get_list_json(self):
        resp = self.api_client.get('/api/v1/subscription/',
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 3)

    def test_get_filtered_list_json(self):
        data = {
            "contact_key": "82309423098",
            "lang": "en",
            "message_set": "/api/v1/message_set/3/",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/1/",
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)

        filter_data = {
            "user_account": json_item['user_account'],
            "to_addr": json_item['to_addr']
        }

        resp = self.api_client.get('/api/v1/subscription/',
                                   data=filter_data,
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 2)

    def test_get_filtered_list_denied_json(self):
        data = {
            "contact_key": "82309423098",
            "lang": "en",
            "message_set": "/api/v1/message_set/3/",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/1/",
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)

        # print json_item

        filter_data = {
            "user_account": json_item['user_account'],
            "to_addr": json_item['to_addr'],
            "lang": "en"
        }

        resp = self.api_client.get('/api/v1/subscription/',
                                   data=filter_data,
                                   format='json',
                                   authentication=self.get_credentials())
        json_item = json.loads(resp.content)
        self.assertHttpBadRequest(resp)
        self.assertEqual("The 'lang' field does not allow filtering.",
                         json_item["error"])

    def test_post_subscription_with_non_existent_schedule_ref(self):
        data = {
            "active": True,
            "completed": False,
            "contact_key": "82309423098",
            "lang": "en",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/10/",  # Non existent task
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)
        self.assertHttpBadRequest(response)
        self.assertEqual("Could not find the provided object via resource URI "
                         "'/api/v1/periodic_task/10/'.", json_item["error"])

    def test_post_subscription_good(self):
        data = {
            "contact_key": "82309423098",
            "lang": "en",
            "message_set": "/api/v1/message_set/3/",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/1/",
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)
        self.assertEqual("82309423098", json_item["contact_key"])
        self.assertEqual(True, json_item["active"])
        self.assertEqual(False, json_item["completed"])
        self.assertEqual("en", json_item["lang"])
        self.assertEqual("/api/v1/message_set/3/", json_item["message_set"])
        self.assertEqual(1, json_item["next_sequence_number"])
        self.assertEqual("/api/v1/periodic_task/1/", json_item["schedule"])
        self.assertEqual("+271234", json_item["to_addr"])
        self.assertEqual("80493284823", json_item["user_account"])


class TestUploadCSV(TestCase):

    fixtures = ["test"]

    MSG_HEADER = (
        "message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,\
        ss,safe,st,safe,nso,safe,nr,safe\r\n")
    MSG_LINE_CLEAN_1 = (
        "1,hello,0,hello1,0,hell2,0,,0,,0,,0,,0,,0,,0,,0,hello3,0\r\n")
    MSG_LINE_CLEAN_2 = (
        "2,goodbye,0,goodbye1,0,goodbye2,0,,0,,0,,0,,0,,0,,0,,0,goodbye3,\
        0\r\n")
    MSG_LINE_DIRTY_1 = (
        "A,sequence_number_is_text,0,goodbye1,0,goodbye2,0,,0,,0,,0,,0,,0,,\
        0,,0,goodbye3,0\r\n")

    def setUp(self):
        self.admin = User.objects.create_superuser(
            'test', 'test@example.com', "pass123")
        # Start with clean
        Message.objects.all().delete()

    def test_upload_view_not_logged_in_blocked(self):
        response = self.client.get(reverse("csv_uploader"))
        self.assertEqual(response.template_name, "admin/login.html")

    def test_upload_view_logged_in(self):
        self.client.login(username="test", password="pass123")

        response = self.client.get(reverse("csv_uploader"))
        self.assertIn("Upload CSV", response.content)

    def test_upload_csv_clean(self):
        message_set = MessageSet.objects.get(short_name="standard")
        clean_sample = self.MSG_HEADER + \
            self.MSG_LINE_CLEAN_1 + self.MSG_LINE_CLEAN_2
        uploaded = StringIO(clean_sample)
        ingest_csv(uploaded, message_set)
        imported_en = Message.objects.filter(sequence_number="1", lang="en")[0]
        self.assertEquals(imported_en.content, "hello")
        imported_af = Message.objects.filter(sequence_number="1", lang="af")[0]
        self.assertEquals(imported_af.content, "hello1")
        imported_nr = Message.objects.filter(sequence_number="1", lang="nr")[0]
        self.assertEquals(imported_nr.content, "hello3")
        imported_en = Message.objects.filter(sequence_number="2", lang="en")[0]
        self.assertEquals(imported_en.content, "goodbye")
        imported_af2 = Message.objects.filter(sequence_number="2",
                                              lang="af")[0]
        self.assertEquals(imported_af2.content, "goodbye1")
        imported_nr2 = Message.objects.filter(sequence_number="2",
                                              lang="nr")[0]
        self.assertEquals(imported_nr2.content, "goodbye3")

    def test_upload_csv_dirty(self):
        message_set = MessageSet.objects.get(short_name="standard")
        dirty_sample = self.MSG_HEADER + \
            self.MSG_LINE_CLEAN_1 + self.MSG_LINE_DIRTY_1
        uploaded = StringIO(dirty_sample)
        ingest_csv(uploaded, message_set)
        imported_en = Message.objects.filter(sequence_number="1", lang="en")[0]
        self.assertEquals(imported_en.content, "hello")
        imported_en_dirty = Message.objects.filter(lang="en")
        self.assertEquals(len(imported_en_dirty), 1)


class TestEnsureCleanSubscriptions(TestCase):

    fixtures = ["initial_data", "test"]

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg, levelno=logging.INFO):
        [log] = self.handler.logs
        self.assertEqual(log.msg, msg)
        self.assertEqual(log.levelno, levelno)

    def test_data_loaded(self):
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 3)

    # def test_ensure_one_subscription(self):
    #     results = ensure_one_subscription.delay()
    #     self.assertEqual(results.get(), 1)

    def test_fire_metric(self):
        vumi_fire_metric.delay(metric="subscription.duplicates", value=1,
                               agg="last", sender=self.sender)

        self.check_logs("Metric: 'subscription.duplicates' [last] -> 1")


class TestMessageQueueProcessor(TestCase):

    fixtures = ["test", "test_subsend"]

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        # management.call_command(
        #     'loaddata', 'test_subsend.json', verbosity=0)
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg):
        if type(self.handler.logs) != list:
            [logs] = self.handler.logs
        else:
            logs = self.handler.logs
        for log in logs:
            if log.msg == msg:
                return True
        return False

    def test_data_loaded(self):
        messagesets = MessageSet.objects.all()
        self.assertEqual(len(messagesets), 10)
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 6)

    def test_multisend(self):
        schedule = 6
        result = process_message_queue.delay(schedule, self.sender)
        self.assertEquals(result.get(), 3)
        # self.assertEquals(1, 2)

    def test_multisend_none(self):
        schedule = 2
        result = process_message_queue.delay(schedule, self.sender)
        self.assertEquals(result.get(), 0)

    def test_send_message_1_en_accelerated(self):
        subscription = Subscription.objects.get(pk=1)
        result = processes_message.delay(subscription.id, self.sender)
        self.assertEqual(result.get(), {
            "message_id": result.get()["message_id"],
            "to_addr": "+271234",
            "content": "Message 1 on accelerated",
        })
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.next_sequence_number, 2)
        self.assertEquals(subscriber_updated.process_status, 0)

    def test_next_message_2_post_send_en_accelerated(self):
        subscription = Subscription.objects.get(pk=1)
        result = processes_message.delay(subscription.id, self.sender)
        self.assertTrue(result.successful())
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.next_sequence_number, 2)

    def test_set_completed_post_send_en_accelerated_2(self):
        subscription = Subscription.objects.get(pk=1)
        subscription.next_sequence_number = 2
        subscription.save()
        result = processes_message.delay(subscription.id, self.sender)
        self.assertTrue(result.successful())
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.completed, True)
        self.assertEquals(subscriber_updated.active, False)

    def test_new_subscription_created_post_send_en_accelerated_2(self):
        subscription = Subscription.objects.get(pk=1)
        subscription.next_sequence_number = 2
        subscription.save()
        result = processes_message.delay(subscription.id, self.sender)
        self.assertTrue(result.successful())
        # Check another added and old still there
        all_subscription = Subscription.objects.all()
        self.assertEquals(len(all_subscription), 7)
        # Check new subscription is for baby1
        new_subscription = Subscription.objects.get(pk=7)
        self.assertEquals(new_subscription.message_set.pk, 4)
        self.assertEquals(new_subscription.to_addr, "+271234")
        # make sure the new sub is on a different schedule
        periodictask = PeriodicTask.objects.get(pk=2)
        self.assertEquals(new_subscription.schedule, periodictask)
        # Check finished_messages metric not fired
        self.assertEquals(
            False,
            self.check_logs("Metric: 'sum.finished_messages' [sum] -> 1"))
        self.assertEquals(
            True,
            self.check_logs("Metric: u'sum.accelerated_completed' [sum] -> 1"))

    def test_no_new_subscription_created_post_send_en_baby_2(self):
        subscription = Subscription.objects.get(pk=4)
        result = processes_message.delay(subscription.id, self.sender)
        self.assertTrue(result.successful())
        # Check no new subscription added
        all_subscription = Subscription.objects.all()
        self.assertEquals(len(all_subscription), 6)
        # Check old one now inactive and complete
        subscriber_updated = Subscription.objects.get(pk=4)
        self.assertEquals(subscriber_updated.completed, True)
        self.assertEquals(subscriber_updated.active, False)
        # Check finished_messages metric fired
        self.assertEquals(
            True,
            self.check_logs("Metric: 'sum.finished_messages' [sum] -> 1"))
        self.assertEquals(
            True,
            self.check_logs("Metric: u'sum.baby2_completed' [sum] -> 1"))

    def test_send_3_part_message_1_en_subscription(self):
        subscription = Subscription.objects.get(pk=6)
        result = processes_message.delay(subscription.id, self.sender)
        self.assertEqual(result.get(), [{
            "message_id": result.get()[0]["message_id"],
            "to_addr": "+271113",
            "content": "Message 1 on subscription PT1",
        }, {
            "message_id": result.get()[1]["message_id"],
            "to_addr": "+271113",
            "content": "Message 1 on subscription PT2",
        }, {
            "message_id": result.get()[2]["message_id"],
            "to_addr": "+271113",
            "content": "Message 1 on subscription PT3",
        }])
        subscriber_updated = Subscription.objects.get(pk=6)
        self.assertEquals(subscriber_updated.next_sequence_number, 2)
        self.assertEquals(subscriber_updated.process_status, 0)


class RecordingAdapter(TestAdapter):

    """ Record the request that was handled by the adapter.
    """
    request = None

    def send(self, request, *args, **kw):
        self.request = request
        return super(RecordingAdapter, self).send(request, *args, **kw)


class TestHttpApiSender(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            api_url="http://example.com/api/v1/go/http_api_nostream",
            conversation_token="conv-token", session=self.session)

    def test_default_session(self):
        import requests
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertTrue(isinstance(sender.session, requests.Session))

    def test_default_api_url(self):
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertEqual(sender.api_url,
                         "https://go.vumi.org/api/v1/go/http_api_nostream")

    def check_request(self, request, method, data=None, headers=None):
        self.assertEqual(request.method, method)
        if data is not None:
            self.assertEqual(json.loads(request.body), data)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)

    def test_send_text(self):
        adapter = RecordingAdapter(json.dumps({"message_id": "id-1"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", adapter)

        result = self.sender.send_text("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": "id-1",
        })
        self.check_request(
            adapter.request, 'PUT',
            data={"content": "Hello!", "to_addr": "to-addr-1"},
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_fire_metric(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.1, "max"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_fire_metric_default_agg(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.2, "last"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class TestLoggingSender(TestCase):

    def setUp(self):
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg, levelno=logging.INFO):
        [log] = self.handler.logs
        self.assertEqual(log.msg, msg)
        self.assertEqual(log.levelno, levelno)

    def test_send_text(self):
        result = self.sender.send_text("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
        })
        self.check_logs("Message: 'Hello!' sent to 'to-addr-1'")

    def test_fire_metric(self):
        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [max] -> 5.1")

    def test_fire_metric_default_agg(self):
        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [last] -> 5.2")
