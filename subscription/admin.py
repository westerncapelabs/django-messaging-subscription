from django.contrib import admin
from subscription.models import MessageSet, Message, Subscription


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["contact_key", "to_addr", "message_set",
                    "next_sequence_number", "lang", "active",
                    "completed", "created_at", "updated_at",
                    "schedule", "process_status"]
    search_fields = ["contact_key", "to_addr"]


admin.site.register(MessageSet)
admin.site.register(Message)
admin.site.register(Subscription, SubscriptionAdmin)
