from django.urls import path
from .views import TaskViewSet

task_list        = TaskViewSet.as_view({"get": "list",    "post": "create"})
task_detail      = TaskViewSet.as_view({"get": "retrieve"})
task_status      = TaskViewSet.as_view({"patch": "update_status"})
task_msgs        = TaskViewSet.as_view({"get": "messages"})
task_send        = TaskViewSet.as_view({"post": "send_message"})
task_calibration = TaskViewSet.as_view({"get": "calibration"})
task_digest      = TaskViewSet.as_view({"get": "digest"})
task_digest_gen  = TaskViewSet.as_view({"post": "generate_digest"})

urlpatterns = [
    path("tasks/",                                  task_list,        name="api-task-list"),
    path("tasks/reports/calibration/",             task_calibration, name="api-task-calibration"),
    path("tasks/reports/digest/",                  task_digest,      name="api-task-digest"),
    path("tasks/reports/digest/generate/",         task_digest_gen,  name="api-task-digest-generate"),
    path("tasks/<str:task_code>/",                  task_detail,      name="api-task-detail"),
    path("tasks/<str:task_code>/status/",           task_status,      name="api-task-status"),
    path("tasks/<str:task_code>/messages/",         task_msgs,        name="api-task-messages"),
    path("tasks/<str:task_code>/messages/send/",    task_send,        name="api-task-send"),
]
