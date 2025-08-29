import requests
import os
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_template(to_number, template_name, image_url, components):
    """
    Sends a WhatsApp template message using the Meta Graph API.
    """
    access_token = os.environ.get('META_ACCESS_TOKEN')
    phone_id = os.environ.get('META_PHONE_ID')
    
    if not all([access_token, phone_id]):
        logger.error("WhatsApp API credentials are not set.")
        return False, {"error": "Server not configured for messages."}

    api_url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    
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
            "language": {"code": "en_US"},
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