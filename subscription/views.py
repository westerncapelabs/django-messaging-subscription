# Create your views here.

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, render, redirect
from django.template import RequestContext
from django.contrib import messages
from django.core.context_processors import csrf
from django.http import HttpResponse

from forms import CSVUploader

from celery_app.tasks import add
from celery.result import AsyncResult


@staff_member_required
def uploader(request, page_name):
    if request.method == "POST":
        form = CSVUploader(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request,
                             "CSV has been uploaded for processing",
                             extra_tags="success")
            context = {"form": form}
        else:
            for errors_key, error_value in form.errors.iteritems():
                messages.error(request,
                               "%s: %s" % (errors_key, error_value),
                               extra_tags="danger")
            context = {"form": form}
        context.update(csrf(request))

        return render_to_response("custom_admin/upload.html", context,
                                  context_instance=RequestContext(request))
    else:
        form = CSVUploader()
        context = {"form": form}
        context.update(csrf(request))
        return render_to_response("custom_admin/upload.html", context,
                                  context_instance=RequestContext(request))


def create_task(request):
    if request.method == 'POST':
        task = add.delay(request.POST['x'], request.POST['y'])
        print task
        return redirect('task_result', task_id=task.task_id)
    return render(request, 'create_task.html', {})


def task_result(request, task_id):
    result = AsyncResult(task_id)
    if result.ready():
        return HttpResponse('Result is: %s' % (result.result,))
    else:
        return HttpResponse('Result is not ready yet!')
