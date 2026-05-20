from django.contrib import admin
from .models import Task, ExtractedEntity, TaskStep, GeneratedMessage, StatusHistory, DigestReport, TaskOutcome


class ExtractedEntityInline(admin.TabularInline):
    model = ExtractedEntity
    extra = 0


class TaskStepInline(admin.TabularInline):
    model = TaskStep
    extra = 0
    ordering = ["order"]


class GeneratedMessageInline(admin.TabularInline):
    model = GeneratedMessage
    extra = 0


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_at"]
    can_delete = False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ["task_code", "intent", "status", "risk_level", "risk_score", "employee_assignment", "created_at"]
    list_filter   = ["status", "risk_level", "intent", "escalation_required"]
    search_fields = ["task_code", "customer_request", "intent"]
    readonly_fields = ["task_code", "created_at", "updated_at"]
    inlines = [ExtractedEntityInline, TaskStepInline, GeneratedMessageInline, StatusHistoryInline]


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display    = ["task", "from_status", "to_status", "changed_at"]
    list_filter     = ["from_status", "to_status"]
    readonly_fields = ["task", "from_status", "to_status", "changed_at"]


@admin.register(DigestReport)
class DigestReportAdmin(admin.ModelAdmin):
    list_display    = ["generated_at", "high_risk_count", "failed_count"]
    readonly_fields = ["generated_at", "high_risk_count", "failed_count", "task_codes"]


@admin.register(TaskOutcome)
class TaskOutcomeAdmin(admin.ModelAdmin):
    list_display    = ["task", "final_assignment", "ai_was_correct", "human_overrode_assignment", "recorded_at"]
    list_filter     = ["ai_was_correct", "human_overrode_assignment"]
    readonly_fields = ["task", "recorded_at"]
