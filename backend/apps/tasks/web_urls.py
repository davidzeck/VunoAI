from django.urls import path
from . import web_views

urlpatterns = [
    path("",                         web_views.index,       name="index"),
    path("dashboard/",               web_views.dashboard,   name="dashboard"),
    path("tasks/<str:task_code>/",   web_views.task_detail, name="task-detail"),
]
