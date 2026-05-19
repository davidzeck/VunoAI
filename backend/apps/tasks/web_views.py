from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import Task, GeneratedMessage
from services.task_service import TaskService

task_service = TaskService()


def index(request):
    if request.method == "POST":
        customer_request = request.POST.get("customer_request", "").strip()
        if customer_request:
            task = task_service.initiate(customer_request)
            return redirect("task-detail", task_code=task.task_code)
        messages.error(request, "Please describe the customer request.")
    return render(request, "index.html")


def dashboard(request):
    qs = Task.objects.all().order_by("-created_at")

    status_filter     = request.GET.get("status", "")
    risk_level_filter = request.GET.get("risk_level", "")
    intent_filter     = request.GET.get("intent", "")
    search            = request.GET.get("search", "")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if risk_level_filter:
        qs = qs.filter(risk_level=risk_level_filter)
    if intent_filter:
        qs = qs.filter(intent=intent_filter)
    if search:
        qs = qs.filter(task_code__icontains=search) | qs.filter(customer_request__icontains=search)

    context = {
        "tasks":              qs,
        "status_filter":      status_filter,
        "risk_level_filter":  risk_level_filter,
        "intent_filter":      intent_filter,
        "search":             search,
        "status_choices":     Task.Status.choices,
        "total_count":        Task.objects.count(),
        "pending_count":      Task.objects.filter(status="pending").count(),
        "high_risk_count":    Task.objects.filter(risk_level="high").count(),
    }
    return render(request, "dashboard.html", context)


def task_detail(request, task_code):
    task = get_object_or_404(Task, task_code=task_code)
    whatsapp_msg = task.messages.filter(channel="whatsapp").first()
    email_msg    = task.messages.filter(channel="email").first()
    sms_msg      = task.messages.filter(channel="sms").first()
    is_processing = task.status in ["pending", "in_progress"]

    context = {
        "task":           task,
        "steps":          task.steps.all(),
        "history":        task.history.all(),
        "whatsapp_msg":   whatsapp_msg,
        "email_msg":      email_msg,
        "sms_msg":        sms_msg,
        "is_processing":  is_processing,
        "status_choices": Task.Status.choices,
        "entities":       task.extracted_entities.all(),
    }
    return render(request, "task_detail.html", context)
