# registration/tasks.py

from celery import shared_task
from django.core.files.storage import default_storage
from .models import ChatContact
from .whats_app import send_whatsapp_message, save_outgoing_message, upload_media_to_meta
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_scheduled_template_campaign(recipients, template_name, params, media_file_path=None):
    """
    A Celery task to send a WhatsApp template campaign to a list of recipients.
    """
    logger.info(f"Starting scheduled campaign for template: {template_name}")

    media_id = None
    if media_file_path:
        # If there's a file, open it from storage and upload to Meta
        if default_storage.exists(media_file_path):
            with default_storage.open(media_file_path, 'rb') as f:
                media_id = upload_media_to_meta(f)
            # Clean up the temporary file after uploading
            default_storage.delete(media_file_path)
        else:
            logger.error(f"Media file not found at path: {media_file_path}")
    
    for wa_id in recipients:
        try:
            contact = ChatContact.objects.get(wa_id=wa_id)
            personalized_params = [p.replace("$name", contact.name or "") for p in params]
            
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "template",
                "template": {"name": template_name, "language": {"code": "en"}}
            }

            components = []
            if media_id:
                components.append({"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]})
            if personalized_params:
                components.append({"type": "body", "parameters": [{"type": "text", "text": p} for p in personalized_params]})
            if components:
                payload['template']['components'] = components
            
            success, response_data = send_whatsapp_message(payload)
            if success:
                save_outgoing_message(
                    contact=contact,
                    wamid=response_data['messages'][0]['id'],
                    message_type='template',
                    text_content=f"Sent scheduled template: {template_name}"
                )
                logger.info(f"Successfully sent scheduled message to {wa_id}")
            else:
                logger.error(f"Failed to send scheduled message to {wa_id}. Response: {response_data}")
        except Exception as e:
            logger.error(f"Error processing recipient {wa_id}: {e}", exc_info=True)

    return f"Campaign for template '{template_name}' completed."