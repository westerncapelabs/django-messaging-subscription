from tastypie import fields
from tastypie.resources import ModelResource, ALL
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from subscription.models import Subscription, MessageSet
from djcelery.models import PeriodicTask


class PeriodicTaskResource(ModelResource):

    class Meta:
        queryset = PeriodicTask.objects.all()
        resource_name = 'periodic_task'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()


class MessageSetResource(ModelResource):

    class Meta:
        queryset = MessageSet.objects.all()
        resource_name = 'message_set'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()


class SubscriptionResource(ModelResource):
    schedule = fields.ToOneField(PeriodicTaskResource, 'schedule')
    message_set = fields.ToOneField(MessageSetResource, 'message_set')

    class Meta:
        queryset = Subscription.objects.all()
        resource_name = 'subscription'
        list_allowed_methods = ['post', 'get', 'put', 'patch']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'to_addr': ALL,
            'user_account': ALL
        }
