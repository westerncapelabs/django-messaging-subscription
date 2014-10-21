# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("djcelery", "0004_v30_changes"),
    )

    def forwards(self, orm):
        # Adding model 'MessageSet'
        db.create_table(u'subscription_messageset', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('next_set', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['subscription.MessageSet'], null=True, blank=True)),
            ('created_at', self.gf('subscription.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('subscription.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'subscription', ['MessageSet'])

        # Adding model 'Message'
        db.create_table(u'subscription_message', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('message_set', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages', to=orm['subscription.MessageSet'])),
            ('sequence_number', self.gf('django.db.models.fields.IntegerField')()),
            ('lang', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('subscription.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('subscription.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'subscription', ['Message'])

        # Adding model 'Subscription'
        db.create_table(u'subscription_subscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_account', self.gf('django.db.models.fields.CharField')(max_length=36)),
            ('contact_key', self.gf('django.db.models.fields.CharField')(max_length=36)),
            ('to_addr', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('message_set', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscribers', to=orm['subscription.MessageSet'])),
            ('next_sequence_number', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('lang', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('completed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_at', self.gf('subscription.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('subscription.models.AutoDateTimeField')(blank=True)),
            ('schedule', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriptions', to=orm['djcelery.PeriodicTask'])),
            ('process_status', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'subscription', ['Subscription'])


    def backwards(self, orm):
        # Deleting model 'MessageSet'
        db.delete_table(u'subscription_messageset')

        # Deleting model 'Message'
        db.delete_table(u'subscription_message')

        # Deleting model 'Subscription'
        db.delete_table(u'subscription_subscription')


    models = {
        u'djcelery.crontabschedule': {
            'Meta': {'ordering': "[u'month_of_year', u'day_of_month', u'day_of_week', u'hour', u'minute']", 'object_name': 'CrontabSchedule'},
            'day_of_month': ('django.db.models.fields.CharField', [], {'default': "u'*'", 'max_length': '64'}),
            'day_of_week': ('django.db.models.fields.CharField', [], {'default': "u'*'", 'max_length': '64'}),
            'hour': ('django.db.models.fields.CharField', [], {'default': "u'*'", 'max_length': '64'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'minute': ('django.db.models.fields.CharField', [], {'default': "u'*'", 'max_length': '64'}),
            'month_of_year': ('django.db.models.fields.CharField', [], {'default': "u'*'", 'max_length': '64'})
        },
        u'djcelery.intervalschedule': {
            'Meta': {'ordering': "[u'period', u'every']", 'object_name': 'IntervalSchedule'},
            'every': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        u'djcelery.periodictask': {
            'Meta': {'object_name': 'PeriodicTask'},
            'args': ('django.db.models.fields.TextField', [], {'default': "u'[]'", 'blank': 'True'}),
            'crontab': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djcelery.CrontabSchedule']", 'null': 'True', 'blank': 'True'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exchange': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djcelery.IntervalSchedule']", 'null': 'True', 'blank': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'default': "u'{}'", 'blank': 'True'}),
            'last_run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'queue': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_run_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'subscription.message': {
            'Meta': {'object_name': 'Message'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('subscription.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'message_set': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['subscription.MessageSet']"}),
            'sequence_number': ('django.db.models.fields.IntegerField', [], {}),
            'updated_at': ('subscription.models.AutoDateTimeField', [], {'blank': 'True'})
        },
        u'subscription.messageset': {
            'Meta': {'object_name': 'MessageSet'},
            'created_at': ('subscription.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'next_set': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['subscription.MessageSet']", 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'updated_at': ('subscription.models.AutoDateTimeField', [], {'blank': 'True'})
        },
        u'subscription.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contact_key': ('django.db.models.fields.CharField', [], {'max_length': '36'}),
            'created_at': ('subscription.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'message_set': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscribers'", 'to': u"orm['subscription.MessageSet']"}),
            'next_sequence_number': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'process_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriptions'", 'to': u"orm['djcelery.PeriodicTask']"}),
            'to_addr': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_at': ('subscription.models.AutoDateTimeField', [], {'blank': 'True'}),
            'user_account': ('django.db.models.fields.CharField', [], {'max_length': '36'})
        }
    }

    complete_apps = ['subscription']