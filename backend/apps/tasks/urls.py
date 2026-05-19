from django.urls import path
from .views import TaskViewSet

task_list   = TaskViewSet.as_view({"get": "list", "post": "create"})
task_detail = TaskViewSet.as_view({"get": "retrieve"})
task_status = TaskViewSet.as_view({"patch": "update_status"})
task_msgs   = TaskViewSet.as_view({"get": "messages"})

urlpatterns = [
    path("tasks/",                          task_list,   name="api-task-list"),
    path("tasks/<str:task_code>/",          task_detail, name="api-task-detail"),
    path("tasks/<str:task_code>/status/",   task_status, name="api-task-status"),
    path("tasks/<str:task_code>/messages/", task_msgs,   name="api-task-messages"),
]
