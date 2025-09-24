from django.db import models
from django.utils import timezone
class ChatContact(models.Model):
    """ Represents a single WhatsApp user you are communicating with. """
    wa_id = models.CharField(max_length=50, unique=True, help_text="The user's WhatsApp ID (their phone number).")
    name = models.CharField(max_length=100, blank=True, null=True, help_text="The user's WhatsApp profile name.")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # CHANGED: Use default instead of auto_now. auto_now updates every time you save the model.
    # This should only be updated when a new message comes in.
    last_contact_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name or self.wa_id

# Create your models here.
class Flow(models.Model):
    """Stores the JSON definition of a flow created in React Flow."""
    template_names = models.CharField(max_length=250, unique=False, help_text="The template that triggers this flow. Other templates can be used inside.")
    flow_data = models.JSONField(help_text="The entire JSON object from React Flow (nodes and edges).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flow for template: {self.template_names}"

class WhatsAppForm(models.Model):
    """Stores the structure of a dynamically created WhatsApp form."""
    name = models.CharField(max_length=100, unique=True, help_text="A unique name for the form.")
    structure = models.JSONField(help_text="The JSON structure of the form fields.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Message(models.Model):
    """ Represents a single message, either incoming or outgoing. """
    
    class MessageDirection(models.TextChoices):
        INBOUND = 'inbound', 'Inbound'
        OUTBOUND = 'outbound', 'Outbound'

    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        DOCUMENT = 'document', 'Document'
        STICKER = 'sticker', 'Sticker'
        CONTACT = 'contact', 'Contact' # Added for clarity
        REACTION = 'reaction', 'Reaction'
        UNKNOWN = 'unknown', 'Unknown'
        
    class MessageStatus(models.TextChoices):
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'
        FAILED = 'failed', 'Failed'
    
    contact = models.ForeignKey(ChatContact, on_delete=models.CASCADE, related_name='messages')
    wamid = models.CharField(max_length=255, unique=True, help_text="The unique WhatsApp Message ID from Meta.")
    direction = models.CharField(max_length=10, choices=MessageDirection.choices)
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.UNKNOWN)
    is_view_once = models.BooleanField(
    default=False,
    help_text="True if this message is a one-time view media."
    )

    # --- Content fields ---
    text_content = models.TextField(blank=True, null=True, help_text="Content for text messages or placeholders for media.")
    caption = models.TextField(blank=True, null=True, help_text="Caption for media messages.")
    media_file = models.FileField(upload_to='whatsapp_media/', blank=True, null=True,max_length=500, help_text="Locally saved media file.")
    
    # --- New field to handle replies ---
    replied_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='replies',
        help_text="The message this message is a reply to."
    )

    reaction = models.CharField(
    max_length=50,
    blank=True,
    null=True,
    help_text="Reaction emoji (e.g. 👍, ❤️)."
   )
    delivery_status = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., sent, delivered, read")
    source_node_id = models.CharField(max_length=255, null=True, blank=True, help_text="The ID of the flow node that sent this message.")
    
    
    timestamp = models.DateTimeField(help_text="Timestamp from the WhatsApp message.")
    media_id = models.CharField(max_length=255, blank=True, null=True)
    # CHANGED: Increased max_length to store reactions like "Reacted with 👍"
    status = models.CharField(max_length=50, choices=MessageStatus.choices, blank=True, null=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_phone = models.CharField(max_length=50, null=True, blank=True)
    
    raw_data = models.JSONField(help_text="The raw, complete webhook payload from Meta for debugging.",null=True, 
        blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.direction.capitalize()} message {self.id} to/from {self.contact.wa_id}"
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    