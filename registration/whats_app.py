import requests
import os
import logging
from django.utils import timezone
from .models import ChatContact, Message
from django.core.files.base import ContentFile
from dotenv import load_dotenv

API_VERSION = 'v19.0'
META_API_URL = f"https://graph.facebook.com/{API_VERSION}"

META_ACCESS_TOKEN ="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
PHONE_NUMBER_ID = "694609297073147"

logger = logging.getLogger(__name__)
# ... keep your existing send_whatsapp_template function ...
def download_media_from_meta(media_id):
    """Downloads media from Meta's servers using a media ID."""
    try:
        url = f"{META_API_URL}/{media_id}/"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        media_info = response.json()
        media_url = media_info.get('url')
        if not media_url:
            return None, None
        media_response = requests.get(media_url, headers=headers)
        media_response.raise_for_status()
        content_type = media_response.headers.get('Content-Type', 'application/octet-stream')
        extension = content_type.split('/')[-1]
        file_name = f"{media_id}.{extension}"
        return file_name, ContentFile(media_response.content)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download media {media_id}: {e}")
        return None, None

def upload_media_to_meta(file):
    """Uploads a file to Meta to get a media ID for sending."""
    try:
        url = f"{META_API_URL}/{PHONE_NUMBER_ID}/media"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        files = {'file': (file.name, file.read(), file.content_type), 'messaging_product': (None, 'whatsapp')}
        response = requests.post(url, headers=headers, files=files)
        return response.json().get('id')
    except Exception as e:
        logger.error(f"Failed to upload media: {e}")
        return None

# --- MESSAGE SENDING ---

def send_whatsapp_message(to_number, payload):
    """Centralized function to send any WhatsApp message via the API."""
    url = f"{META_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error from Meta API: {e.response.json() if e.response else str(e)}")
        return False, e.response.json() if e.response else {'error': str(e)}

def save_outgoing_message(contact, wamid, message_type, text_content="", caption="", raw_data={}):
    """Saves a record of an outgoing message to the database."""
    Message.objects.create(
        contact=contact, wamid=wamid, direction='outbound',
        message_type=message_type, text_content=text_content,
        caption=caption, timestamp=timezone.now(),
        raw_data=raw_data, status='sent'
    )
    contact.last_contact_at = timezone.now()
    contact.save()

def send_whatsapp_text_message(to_number, message_text):
    """
    Sends a simple plain text WhatsApp message.
    """
    access_token ="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"

    phone_id = "694609297073147"
    
    if not all([access_token, phone_id]):
        logger.error("WhatsApp API credentials are not set.")
        return False, {"error": "Server not configured for messages."}

    api_url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text},
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent text message to {to_number}.")
        return True, response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send WhatsApp text to {to_number}: {e}")
        return False, {"error": str(e)}
    
def send_whatsapp_template(to_number, template_name, components):
    """
    Sends a WhatsApp template message using the Meta Graph API.
    """ 
    access_token ="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"

    phone_id = "694609297073147"
    
    if not all([access_token, phone_id]):
        logger.error("WhatsApp API credentials are not set.")
        return False, {"error": "Server not configured for messages."}

    api_url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": components,
        },
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        message_id = response.json().get('messages', [{}])[0].get('id')
        logger.info(f"Successfully sent template '{template_name}' to {to_number}.")
        return True, response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send WhatsApp template to {to_number}: {e}")
        error_details = e.response.json() if e.response else str(e)
        return False, {"error": error_details}