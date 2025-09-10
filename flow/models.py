

from django.db import models
from registration.models import ChatContact

class Flows(models.Model):
    """Stores the JSON definition of a flow created in React Flow."""
    template_names = models.CharField(max_length=250, unique=False, help_text="The template that triggers this flow. Other templates can be used inside.")
    flow_data = models.JSONField(help_text="The entire JSON object from React Flow (nodes and edges).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flow for template: {self.template_name}"

class UserFlowSessions(models.Model):
    """Tracks the current position of a contact within a flow."""
    contact = models.OneToOneField(ChatContact, on_delete=models.CASCADE, primary_key=True)
    flow = models.ForeignKey(Flows, on_delete=models.CASCADE)
    current_node_id = models.CharField(max_length=255, help_text="The ID of the user's current node in the flow.")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.contact.wa_id} is at {self.current_node_id} in {self.flow.template_name}"
