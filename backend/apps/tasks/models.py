from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING     = "pending",     "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED   = "completed",   "Completed"
        FAILED      = "failed",      "Failed"
        REJECTED    = "rejected",    "Rejected"

    task_code           = models.CharField(max_length=20, unique=True, db_index=True)
    customer_request    = models.TextField()
    intent              = models.CharField(max_length=50, blank=True)
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    risk_score          = models.IntegerField(null=True, blank=True)
    risk_level          = models.CharField(max_length=10, blank=True)
    risk_flags          = models.JSONField(default=list)
    risk_explanation    = models.JSONField(default=list)
    escalation_required = models.BooleanField(default=False)
    entities            = models.JSONField(default=dict)
    urgency_level       = models.CharField(max_length=10, blank=True)
    ai_confidence       = models.FloatField(null=True, blank=True)
    employee_assignment = models.CharField(max_length=100, blank=True)
    clarification_note  = models.TextField(blank=True)
    error_detail        = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_code} — {self.intent or 'pending'}"


class ExtractedEntity(models.Model):
    task         = models.ForeignKey(Task, related_name="extracted_entities", on_delete=models.CASCADE)
    entity_key   = models.CharField(max_length=100)
    entity_value = models.TextField()

    def __str__(self):
        return f"{self.entity_key}: {self.entity_value}"


class TaskStep(models.Model):
    task        = models.ForeignKey(Task, related_name="steps", on_delete=models.CASCADE)
    order       = models.PositiveIntegerField()
    description = models.TextField()
    completed   = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Step {self.order}: {self.description[:60]}"


class GeneratedMessage(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL    = "email",    "Email"
        SMS      = "sms",      "SMS"

    task       = models.ForeignKey(Task, related_name="messages", on_delete=models.CASCADE)
    channel    = models.CharField(max_length=20, choices=Channel.choices)
    content    = models.TextField()
    recipient  = models.CharField(max_length=200, blank=True)
    sent_at    = models.DateTimeField(null=True, blank=True)
    send_error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.task.task_code} — {self.channel}"


class StatusHistory(models.Model):
    task        = models.ForeignKey(Task, related_name="history", on_delete=models.CASCADE)
    from_status = models.CharField(max_length=20)
    to_status   = models.CharField(max_length=20)
    changed_at  = models.DateTimeField(auto_now_add=True)
    note        = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.task.task_code}: {self.from_status} → {self.to_status}"


class DigestReport(models.Model):
    generated_at    = models.DateTimeField(auto_now_add=True)
    high_risk_count = models.IntegerField(default=0)
    failed_count    = models.IntegerField(default=0)
    task_codes      = models.JSONField(default=list)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Digest {self.generated_at:%Y-%m-%d %H:%M} — {self.high_risk_count} high-risk"


class TaskOutcome(models.Model):
    task                      = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="outcome")
    recorded_at               = models.DateTimeField(auto_now_add=True)
    human_overrode_assignment = models.BooleanField(default=False)
    final_assignment          = models.CharField(max_length=100)
    ai_was_correct            = models.BooleanField(null=True)
    override_note             = models.TextField(blank=True)

    def __str__(self):
        return f"{self.task.task_code} outcome — correct={self.ai_was_correct}"
