

from django.db import models
from django.contrib import admin
from registration.models import ChatContact


class WhatsAppCall(models.Model):
    """Logs every inbound and outbound WhatsApp call."""
    CALL_DIRECTIONS = (('inbound', 'Inbound'), ('outbound', 'Outbound'))
    
    call_id = models.CharField(max_length=255, unique=True, db_index=True, help_text="The unique ID from Meta for this call")
    contact = models.ForeignKey(ChatContact, on_delete=models.SET_NULL, null=True, related_name="calls")
    direction = models.CharField(max_length=10, choices=CALL_DIRECTIONS)
    status = models.CharField(max_length=20, default='initiated', help_text="e.g., ringing, answered, ended, missed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the call was ended or missed")

    def __str__(self):
        return f"{self.direction.capitalize()} call with {self.contact.wa_id} - {self.status}"
class Flows(models.Model):
    """Stores the JSON definition of a flow created in React Flow."""
    name = models.CharField(max_length=255, unique=True, default="Untitled Flow")
    is_active = models.BooleanField(default=True, help_text="Indicates if the flow is currently active and can be triggered.")

    template_name = models.CharField(max_length=250, unique=False, help_text="The template that triggers this flow. Other templates can be used inside.")
    flow_data = models.JSONField(help_text="The entire JSON object from React Flow (nodes and edges).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Flows"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Flow '{self.name}' (Active: {self.is_active})"

class Attribute(models.Model):
    """Represents a custom field, e.g., 'city', 'email', 'order_value'."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
 
class UserFlowSessions(models.Model):
    """Tracks the current position of a contact within a flow."""
    contact = models.OneToOneField(ChatContact, on_delete=models.CASCADE, primary_key=True)
    flow = models.ForeignKey(Flows, on_delete=models.CASCADE)
    current_node_id = models.CharField(max_length=255, help_text="The ID of the user's current node in the flow.")
    updated_at = models.DateTimeField(auto_now=True)

    waiting_for_attribute = models.ForeignKey(
        'Attribute', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    # For waiting for a location reply
    is_waiting_for_location = models.BooleanField(default=False)
    longitude_attribute = models.ForeignKey(
        'Attribute', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='longitude_sessions'
    )
    latitude_attribute = models.ForeignKey(
        'Attribute', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='latitude_sessions'
    )

    # For waiting for an image reply
    waiting_for_image_attribute = models.ForeignKey(
        'Attribute', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='image_sessions'
    )
    waiting_for_flow_completion = models.BooleanField(default=False)
    flow_form_id = models.CharField(max_length=255, null=True, blank=True)
    
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = "User Flow Sessions"

    def __str__(self):
        return f"{self.contact.wa_id} is at {self.current_node_id} in {self.flow.name}"

class WhatsAppFlowForm(models.Model):
    """
    Model to store WhatsApp Flow Forms created via the form builder.
    """
    name = models.CharField(max_length=255, unique=True)
    meta_flow_id = models.CharField(max_length=255, null=True, blank=True)  # Meta's Flow ID
    template_category = models.CharField(max_length=50, default='UTILITY')
    template_body = models.TextField()
    template_button_text = models.CharField(max_length=20, default='Open Form')
    screens_data = models.JSONField()  # Store the screen configuration
    
    # Meta API response data
    flow_status = models.CharField(max_length=50, null=True, blank=True)
    template_name = models.CharField(max_length=255, null=True, blank=True)
    template_status = models.CharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "WhatsApp Flow Form"
        verbose_name_plural = "WhatsApp Flow Forms"


class ContactAttributeValue(models.Model):
    """Stores the actual value of an attribute for a specific contact."""
    contact = models.ForeignKey(ChatContact, on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='contact_values')
    value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('contact', 'attribute')

    def __str__(self):
        return f"{self.contact.wa_id} -> {self.attribute.name}: {self.value}" # Optional: Add security
    
class Flowss(models.Model):
    """Stores the JSON definition of a flow created in React Flow."""
    template_name = models.CharField(max_length=250, unique=False, help_text="The template that triggers this flow. Other templates can be used inside.")
    flow_data = models.JSONField(help_text="The entire JSON object from React Flow (nodes and edges).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flow for template: {self.template_name}"

class UserFlowSessionss(models.Model):
    """Tracks the current position of a contact within a flow."""
    contact = models.OneToOneField(ChatContact, on_delete=models.CASCADE, primary_key=True)
    flow = models.ForeignKey(Flowss, on_delete=models.CASCADE)
    current_node_id = models.CharField(max_length=255, help_text="The ID of the user's current node in the flow.")
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"{self.contact.wa_id} is at {self.current_node_id} in {self.flow.template_name}"

