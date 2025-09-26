# contact_app/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
# from corsheaders.decorators import cors_exempt       # Import cors_exempt
import json
from .tasks import process_api_request_node
from django.shortcuts import render # Make sure render is imported

# def home_page(request):
#     return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})

# from .models import Flow, Message, 
#  # Make sure these are imported
from registration.models import ChatContact, Message
from .models import Flows as Flow
from .models import UserFlowSessions as UserFlowSession
from .models import Attribute  # <-- Add this import for Attribute model
from .models import ContactAttributeValue  # <-- Add this import for ContactAttributeValue model
from registration.whats_app import send_whatsapp_message, save_outgoing_message, upload_media_for_template_handle
from django.utils import timezone
import os
import mimetypes
import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import logging
from django.http import HttpResponse
logger = logging.getLogger(__name__)

# import requests
# API_VERSION = 'v19.0'
# META_API_URL = f"https://graph.facebook.com/{API_VERSION}"

# PHONE_NUMBER_ID = 705449502657013


# META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
        
# WABA_ID = "1477047197063313"
# contact_app/views.py
# from .utils import extract_json_path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render
from registration.models import ChatContact, Message
from .models import Flows as Flow
from .models import UserFlowSessions as UserFlowSession
from registration.whats_app import send_whatsapp_message, save_outgoing_message
from django.utils import timezone
import logging
import requests

logger = logging.getLogger(__name__)

# API_VERSION = 'v19.0'
# META_API_URL = f"https://graph.facebook.com/{API_VERSION}"
# PHONE_NUMBER_ID = 705449502657013
# META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
# WABA_ID = "1477047197063313"

def home_page(request):
    return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})


# --- Constants ---
API_VERSION = 'v19.0'
META_API_URL = f"https://graph.facebook.com/{API_VERSION}"
PHONE_NUMBER_ID = "694609297073147" # Replace with your Phone Number ID
META_ACCESS_TOKEN = "EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ" # Replace with your Meta Access Token
WABA_ID = "1477047197063313" # Replace with your WABA ID

# --- Core Flow Execution Logic ---

# --- Core Flow Execution Logic ---

def substitute_placeholders(text, user_data):
    """Replace {{variable}} with actual values"""
    if not text:
        return text
    
    import re
    
    def replace_placeholder(match):
        key = match.group(1).strip()
        value = user_data.get(key, f"{{{{ {key} }}}}")
        logger.info(f"DEBUG-SUBSTITUTION: Replacing {{{{ {key} }}}} with '{value}'")
        return str(value)
    
    return re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_placeholder, text)

def extract_json_path(data, path):
    """Extract value from JSON using dot notation"""
    try:
        current = data
        parts = path.split('.')
        for part in parts:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current[part]
        return current
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    

def execute_flow_node(contact, flow, target_node):
    """
    Central helper function to construct a message payload for a given node,
    send it, and manage the user's session.
    """
    target_node_id = target_node.get('id')
    node_type = target_node.get('type')
    node_data = target_node.get('data', {})
    
    payload = {"messaging_product": "whatsapp", "to": contact.wa_id}
    message_type_to_save = node_type
    text_content_to_save = f"Flow Step: {node_type}"

    if node_type == 'templateNode':
        components = []
        if 'metaMediaId' in node_data and node_data['metaMediaId']:
            header_format = node_data.get('headerComponent', {}).get('format', 'IMAGE').lower()
            components.append({"type": "header", "parameters": [{"type": header_format, header_format: {"id": node_data['metaMediaId']}}]})
        body_params = []
        for i in range(1, 10):
            var_key = f'bodyVar{i}'
            if var_key in node_data and node_data[var_key]:
                body_params.append({"type": "text", "text": node_data[var_key]})
        if body_params:
            components.append({"type": "body", "parameters": body_params})
        payload.update({"type": "template", "template": {"name": node_data.get('selectedTemplateName'), "language": {"code": "en"}, "components": components}})
        message_type_to_save = 'template'
        text_content_to_save = f"Sent template: {node_data.get('selectedTemplateName')}"

    elif node_type == 'textNode':
    # Get user attributes for substitution
        user_attributes = {}
        for attr_value in contact.attribute_values.all():
            user_attributes[attr_value.attribute.name] = attr_value.value
        user_attributes['contact_id'] = contact.wa_id
        
        # Get the original text and substitute placeholders
        original_text = node_data.get('text', '...')
        substituted_text = substitute_placeholders(original_text, user_attributes)
        
        logger.info(f"DEBUG-TEXT-NODE: Original: {original_text}")
        logger.info(f"DEBUG-TEXT-NODE: After substitution: {substituted_text}")
        
        payload.update({"type": "text", "text": {"body": substituted_text}})
        message_type_to_save = 'text'
        text_content_to_save = substituted_text
    elif node_type == 'buttonsNode':
        buttons = [{"type": "reply", "reply": {"id": btn.get('text'), "title": btn.get('text')}} for btn in node_data.get('buttons', [])]
        payload.update({"type": "interactive", "interactive": {"type": "button", "body": {"text": node_data.get('text')}, "action": {"buttons": buttons}}})
        text_content_to_save = node_data.get('text')
        
    elif node_type == 'imageNode':
        payload.update({"type": "image", "image": {"id": node_data.get('metaMediaId'), "caption": node_data.get('caption')}})
        message_type_to_save = 'image'
        text_content_to_save = node_data.get('caption') or "Sent an image"
    
   
    elif node_type == 'interactiveImageNode':
        buttons = [{"type": "reply", "reply": {"id": btn.get('text'), "title": btn.get('text')}} for btn in node_data.get('buttons', [])]
        payload.update({"type": "interactive", "interactive": {"type": "button", "header": {"type": "image", "image": {"id": node_data.get('metaMediaId')}}, "body": {"text": node_data.get('bodyText')}, "action": {"buttons": buttons}}})
        text_content_to_save = node_data.get('bodyText')

    elif node_type == 'interactiveListNode':
        sections_data = []
        for section in node_data.get('sections', []):
            rows_data = [{"id": row.get('id'), "title": row.get('title'), "description": row.get('description', '')} for row in section.get('rows', [])]
            sections_data.append({"title": section.get('title'), "rows": rows_data})
        button_text = node_data.get('buttonText') or 'Select an option'
        payload.update({"type": "interactive", "interactive": {"type": "list", "header": {"type": "text", "text": node_data.get('header', '')}, "body": {"text": node_data.get('body', '')}, "footer": {"text": node_data.get('footer', '')}, "action": {"button": button_text, "sections": sections_data}}})
        text_content_to_save = node_data.get('body')
    
    elif node_type == 'mediaNode':
        media_type = node_data.get('mediaType', 'document')
        media_payload = {"id": node_data.get('metaMediaId')}
        if media_type != 'audio' and node_data.get('caption'):
            media_payload['caption'] = node_data.get('caption')
        if media_type == 'document' and node_data.get('filename'):
            media_payload['filename'] = node_data.get('filename')
        payload.update({"type": media_type, media_type: media_payload})
        message_type_to_save = media_type
        text_content_to_save = node_data.get('caption') or f"Sent a {media_type}"
    elif node_type == 'askQuestionNode':
    # Send the question to the user
        question_text = node_data.get('questionText')
        payload.update({"type": "text", "text": {"body": question_text}})
        message_type_to_save = 'text'
        text_content_to_save = question_text
        
        # FIXED: Convert ID to actual Attribute object
        question_attr = None
        if node_data.get('saveAttributeId'):
            try:
                question_attr = Attribute.objects.get(id=node_data.get('saveAttributeId'))
                logger.info(f"DEBUG-QUESTION-NODE: Found attribute object: {question_attr.name}")
            except Attribute.DoesNotExist:
                logger.error(f"DEBUG-QUESTION-NODE: Attribute ID {node_data.get('saveAttributeId')} not found")
        
        # Set the session to a special "waiting" state
        UserFlowSession.objects.update_or_create(
            contact=contact,
            defaults={
                'flow': flow, 
                'current_node_id': target_node_id,
                'waiting_for_attribute': question_attr  # Use object, not ID
            }
        )
        logger.info(f"DEBUG-QUESTION-NODE: Session for {contact.wa_id} is now waiting for attribute {question_attr}")

    # 2. Fix askLocationNode section:
    elif node_type == 'askLocationNode':
        question_text = node_data.get('questionText')
        
        # This is the specific payload for a Location Request message
        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "location_request_message",
                "body": {
                    "text": question_text or "Please share your location"
                },
                "action": {
                    "name": "send_location"
                }
            }
        })
        
        message_type_to_save = 'interactive'
        text_content_to_save = question_text
        
        # FIXED: Convert IDs to actual Attribute objects
        longitude_attr = None
        latitude_attr = None
        
        if node_data.get('longitudeAttributeId'):
            try:
                longitude_attr = Attribute.objects.get(id=node_data.get('longitudeAttributeId'))
                logger.info(f"DEBUG-LOCATION-NODE: Found longitude attribute: {longitude_attr.name}")
            except Attribute.DoesNotExist:
                logger.error(f"DEBUG-LOCATION-NODE: Longitude attribute ID {node_data.get('longitudeAttributeId')} not found")
        
        if node_data.get('latitudeAttributeId'):
            try:
                latitude_attr = Attribute.objects.get(id=node_data.get('latitudeAttributeId'))
                logger.info(f"DEBUG-LOCATION-NODE: Found latitude attribute: {latitude_attr.name}")
            except Attribute.DoesNotExist:
                logger.error(f"DEBUG-LOCATION-NODE: Latitude attribute ID {node_data.get('latitudeAttributeId')} not found")
        
        # Set the session to a special "waiting for location" state
        UserFlowSession.objects.update_or_create(
            contact=contact,
            defaults={
                'flow': flow, 
                'current_node_id': target_node_id,
                'is_waiting_for_location': True,
                'longitude_attribute': longitude_attr,  # Use object, not ID
                'latitude_attribute': latitude_attr,    # Use object, not ID
                'waiting_for_attribute': None # Clear any text attribute waiting state
            }
        )
        logger.info(f"DEBUG-LOCATION-NODE: Session for {contact.wa_id} is now waiting for location. Long: {longitude_attr}, Lat: {latitude_attr}")

    # 3. Fix askForImageNode section:
    elif node_type == 'askForImageNode': # New node type
        question_text = node_data.get('questionText')
        payload.update({"type": "text", "text": {"body": question_text or "Please send an image."}})
        message_type_to_save = 'text'
        text_content_to_save = question_text
        
        # FIXED: Convert ID to actual Attribute object
        image_attr = None
        if node_data.get('saveAttributeId'):
            try:
                image_attr = Attribute.objects.get(id=node_data.get('saveAttributeId'))
                logger.info(f"DEBUG-IMAGE-NODE: Found image attribute: {image_attr.name}")
            except Attribute.DoesNotExist:
                logger.error(f"DEBUG-IMAGE-NODE: Image attribute ID {node_data.get('saveAttributeId')} not found")
        
        UserFlowSession.objects.update_or_create(
            contact=contact,
            defaults={
                'flow': flow,
                'current_node_id': target_node_id,
                'waiting_for_image_attribute': image_attr,  # Use object, not ID
                'waiting_for_attribute': None,
                'is_waiting_for_location': False
            }
        )
        logger.info(f"DEBUG-IMAGE-NODE: Session for {contact.wa_id} is now waiting for image. Attr: {image_attr}")
    
    elif node_type == 'askApiNode':
   
        api_url = node_data.get('apiUrl')
        method = node_data.get('method', 'GET').upper()
        headers = node_data.get('headers', '{}')
        request_body = node_data.get('requestBody', '{}')
        response_mappings = node_data.get('responseMappings', [])
        status_code_attr_id = node_data.get('statusCodeAttributeId')
        
        logger.info(f"DEBUG-API-REQUEST: Making {method} request to {api_url}")
        
        # Get user attributes
        user_attributes = {}
        for attr_value in contact.attribute_values.all():
            user_attributes[attr_value.attribute.name] = attr_value.value
        user_attributes['contact_id'] = contact.wa_id
        
        logger.info(f"DEBUG-API-REQUEST: Available data: {user_attributes}")
        
        # Replace placeholders
        api_url = substitute_placeholders(api_url, user_attributes)
        headers = substitute_placeholders(headers, user_attributes) 
        request_body = substitute_placeholders(request_body, user_attributes)
        
        logger.info(f"DEBUG-API-REQUEST: URL after substitution: {api_url}")
        logger.info(f"DEBUG-API-REQUEST: Body after substitution: {request_body}")
        
        # Prepare request
        request_config = {
            'method': method,
            'url': api_url,
            'timeout': 8
        }
        
        # Parse headers
        try:
            if headers and headers != '{}':
                request_config['headers'] = json.loads(headers)
            else:
                request_config['headers'] = {}
        except json.JSONDecodeError:
            logger.error(f"DEBUG-API-REQUEST: Invalid headers JSON: {headers}")
            request_config['headers'] = {}
        
        # Parse body for non-GET requests
        if method != 'GET' and request_body and request_body != '{}':
            try:
                request_config['json'] = json.loads(request_body)
            except json.JSONDecodeError:
                logger.error(f"DEBUG-API-REQUEST: Invalid body JSON, sending as text")
                request_config['data'] = request_body
        
        # Make API request
        api_success = False
        response_data = None
        status_code = 0
        
        try:
            logger.info(f"DEBUG-API-REQUEST: Sending request...")
            response = requests.request(**request_config)
            status_code = response.status_code
             # Log the raw response
            # Log the raw response
            logger.info(f"DEBUG-API-REQUEST: Raw response status: {status_code}")
            logger.info(f"DEBUG-API-REQUEST: Raw response headers: {dict(response.headers)}")
            logger.info(f"DEBUG-API-REQUEST: Raw response text: {response.text[:500]}...")  # First 500 chars
                
            # Try to parse response as JSON
            try:
                response_data = response.json()
                logger.info(f"DEBUG-API-REQUEST: Parsed JSON response: {json.dumps(response_data, indent=2)}")
      
            except:
                response_data = response.text
                logger.info(f"DEBUG-API-REQUEST: Response is not JSON, using text")
        
            
            api_success = 200 <= status_code < 300
            logger.info(f"DEBUG-API-REQUEST: Response - Status: {status_code}, Success: {api_success}")
            
        except requests.exceptions.Timeout:
            logger.error(f"DEBUG-API-REQUEST: Request timed out")
            status_code = 408
            response_data = {"error": "Request timed out"}
            
        except requests.exceptions.ConnectionError:
            logger.error(f"DEBUG-API-REQUEST: Connection error")
            status_code = 0
            response_data = {"error": "Connection error"}
            
        except Exception as e:
            logger.error(f"DEBUG-API-REQUEST: Request failed: {e}")
            status_code = 0
            response_data = {"error": str(e)}
        
        # Save status code if specified
        if status_code_attr_id:
            try:
                status_attr = Attribute.objects.get(id=status_code_attr_id)
                ContactAttributeValue.objects.update_or_create(
                    contact=contact, 
                    attribute=status_attr,
                    defaults={'value': str(status_code)}
                )
                logger.info(f"DEBUG-API-REQUEST: Saved status code {status_code}")
            except Attribute.DoesNotExist:
                logger.error(f"DEBUG-API-REQUEST: Status code attribute not found")
        
        # Process response mappings
        if api_success and response_mappings and isinstance(response_data, dict):
            for mapping in response_mappings:
                json_path = mapping.get('jsonPath')
                attribute_id = mapping.get('attributeId')
                
                if not json_path or not attribute_id:
                    continue
                
                try:
                    value = extract_json_path(response_data, json_path)
                    if value is not None:
                        attribute = Attribute.objects.get(id=attribute_id)
                        ContactAttributeValue.objects.update_or_create(
                            contact=contact, 
                            attribute=attribute,
                            defaults={'value': str(value)}
                        )
                        logger.info(f"DEBUG-API-REQUEST: Saved '{value}' from '{json_path}' to '{attribute.name}'")
                except Attribute.DoesNotExist:
                    logger.error(f"DEBUG-API-REQUEST: Attribute {attribute_id} not found")
                except Exception as e:
                    logger.error(f"DEBUG-API-REQUEST: Error processing mapping: {e}")
        
        # Find next node
        edges = flow.flow_data.get('edges', [])
        next_handle = 'onSuccess' if api_success else 'onError'
        next_edge = next((e for e in edges if e.get('source') == target_node_id and e.get('sourceHandle') == next_handle), None)
        
        logger.info(f"DEBUG-API-REQUEST: Looking for '{next_handle}' edge: {next_edge}")
        
        # Continue flow
        if next_edge:
            next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
            if next_node:
                logger.info(f"DEBUG-API-REQUEST: Continuing to next node: {next_node.get('id')}")
                UserFlowSession.objects.update_or_create(
                    contact=contact,
                    defaults={'flow': flow, 'current_node_id': target_node_id}
                )
                execute_flow_node(contact, flow, next_node)
            else:
                logger.error(f"DEBUG-API-REQUEST: Next node not found")
                UserFlowSession.objects.filter(contact=contact).delete()
        else:
            logger.info(f"DEBUG-API-REQUEST: No next edge found, ending flow")
            UserFlowSession.objects.filter(contact=contact).delete()
        
        # Don't send WhatsApp message for API node
        return True
    
    elif node_type == 'flowFormNode':
        form_db_id = node_data.get('selectedFormId')
        template_body = node_data.get('templateBody', '')
        button_text = node_data.get('buttonText', 'Open Form')
        
        # if not form_id:
        #     logger.error(f"No form selected for flowFormNode {target_node_id}")
        #     return False
        
        try:
            # Get the form from your database
            from .models import WhatsAppFlowForm  # Adjust import as needed
            flow_form = WhatsAppFlowForm.objects.get(id=form_db_id)
            meta_flow_id = flow_form.meta_flow_id
          
          # Get the ID of the first screen to start the flow
            first_screen_id = "FORM_SCREEN" # A safe default
            if flow_form.screens_data and 'screens_data' in flow_form.screens_data and flow_form.screens_data['screens_data']:
                # --- FIX #2: Access the nested 'screens_data' key ---
                first_screen_id = flow_form.screens_data['screens_data'][0].get('id', first_screen_id)

            # Create the Flow message payload
                payload.update({
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {"type": "text", "text": flow_form.name},
                    "body": {"text": template_body or flow_form.template_body},
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_id": meta_flow_id,
                            "flow_cta": button_text or flow_form.template_button_text,
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": first_screen_id
                            }
                        }
                    }
                }
            })
            
            message_type_to_save = 'interactive'
            text_content_to_save = f"Sent Flow Form: {flow_form.name}"
            
            # Set session to wait for flow completion
            UserFlowSession.objects.update_or_create(
                contact=contact,
                defaults={
                    'flow': flow, 
                    'current_node_id': target_node_id,
                    'waiting_for_flow_completion': True,
                    'flow_form_id': meta_flow_id
                }
            )
            
        except WhatsAppFlowForm.DoesNotExist:
            logger.error(f"Flow form with id {meta_flow_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error creating flow form message: {e}")
            return False
    
    else:
        logger.error(f"Message construction for node type '{node_type}' is not implemented.")
        return False

    success, response_data = send_whatsapp_message(payload)

    if success:
        wamid = response_data['messages'][0]['id']
        save_outgoing_message(contact=contact, wamid=wamid, message_type=message_type_to_save, text_content=text_content_to_save, source_node_id=target_node_id)
        
        if node_type not in ['askQuestionNode', 'askLocationNode', 'askForImageNode','askApiNode','flowFormNode']:
            edges = flow.flow_data.get('edges', [])
            target_has_outputs = any(e for e in edges if e.get('source') == target_node_id)
            if target_has_outputs:
                UserFlowSession.objects.update_or_create(
                    contact=contact,
                    defaults={'flow': flow, 'current_node_id': target_node_id, 'waiting_for_attribute': None}
                )
            else:
                 UserFlowSession.objects.filter(contact=contact).delete()
        return True
    
    logger.error(f"Failed to send message via WhatsApp API. Payload: {json.dumps(payload, indent=2)}")
    logger.error(f"Meta API Response: {response_data}")
    return False


def try_execute_status_trigger(wamid, wa_id):
    """Executes a flow step triggered by a 'read' status update."""
    try:
        message = Message.objects.get(wamid=wamid)
        contact = ChatContact.objects.get(wa_id=wa_id)
        session = UserFlowSession.objects.filter(contact=contact).first()
        
        source_node_id = message.source_node_id
        flow = session.flow if session else None

        if not source_node_id and message.message_type == 'template':
            template_name = message.text_content.replace("Sent template: ", "").strip()
            possible_flow = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at').first()
            if possible_flow:
                flow = possible_flow
                nodes = flow.flow_data.get('nodes', [])
                start_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data', {}).get('selectedTemplateName') == template_name), None)
                if start_node:
                    source_node_id = start_node.get('id')

        if not flow or not source_node_id:
            return False
        
        edges = flow.flow_data.get('edges', [])
        next_edge = next((e for e in edges if e.get('source') == source_node_id and e.get('sourceHandle') == 'onRead'), None)

        if not next_edge:
            return False

        nodes = flow.flow_data.get('nodes', [])
        target_node = next((n for n in nodes if n.get('id') == next_edge.get('target')), None)

        if not target_node:
            return False
            
        return execute_flow_node(contact, flow, target_node)
    except (Message.DoesNotExist, ChatContact.DoesNotExist):
        pass
    except Exception as e:
        logger.error(f"CRITICAL STATUS TRIGGER ERROR: {e}", exc_info=True)
    return False


def try_execute_flow_step(contact, user_input, replied_to_wamid):
    """
    Finds and executes the next step in a flow, with extensive debugging at every stage.
    """
    logger.info(f"--- [START] --- Attempting to execute flow step for contact: {contact.wa_id}")
    logger.info(f"                User Input: '{user_input}', Replied to WAMID: {replied_to_wamid}")

    session = UserFlowSession.objects.filter(contact=contact).first()
    flow = session.flow if session else None
    current_node, next_edge = None, None

    # --- Stage 1: Check for an active session ---
    logger.info("[Stage 1] Checking for an active user session...")
    if session:
        logger.info(f"  [PASS] Active session found. Flow: '{flow.name}', Current Node ID: '{session.current_node_id}'")
        nodes, edges = flow.flow_data.get('nodes', []), flow.flow_data.get('edges', [])
        current_node = next((n for n in nodes if n.get('id') == session.current_node_id), None)
        if current_node:
            logger.info(f"  Found current node in flow data. Type: '{current_node.get('type')}'")
            next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
            if next_edge:
                logger.info(f"  [SUCCESS] Found a valid next edge from current session: '{current_node.get('id')}' -> '{next_edge.get('target')}' via handle '{user_input}'")
            else:
                logger.warning(f"  [FAIL] No edge found from node '{current_node.get('id')}' with handle '{user_input}'.")
        else:
            logger.error(f"  [CRITICAL] Session points to node '{session.current_node_id}', but it was not found in the flow data!")
    else:
        logger.info("  [INFO] No active session found for this contact.")

    # --- Stage 2: If no path, check historical context ---
    if not next_edge:
        logger.info("[Stage 2] No path from session. Checking historical message context...")
        try:
            original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound')
            logger.info(f"  Found replied-to message in DB. Source Node ID: '{original_message.source_node_id}'")
            if original_message.source_node_id:
                if not flow:
                    logger.info("  No flow loaded yet. Searching all active flows for the historical node...")
                    active_flows = Flow.objects.filter(is_active=True)
                    for f in active_flows:
                        if any(n.get('id') == original_message.source_node_id for n in f.flow_data.get('nodes', [])):
                            flow = f
                            logger.info(f"  [PASS] Found historical node in flow '{flow.name}'.")
                            break
                if flow:
                    nodes, edges = flow.flow_data.get('nodes', []), flow.flow_data.get('edges', [])
                    current_node = next((n for n in nodes if n.get('id') == original_message.source_node_id), None)
                    if current_node:
                        next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
                        if next_edge:
                             logger.info(f"  [SUCCESS] Found a valid historical path: '{current_node.get('id')}' -> '{next_edge.get('target')}' via handle '{user_input}'")
                        else:
                            logger.warning(f"  [FAIL] Found historical node, but no edge matches handle '{user_input}'.")
                else:
                    logger.warning("  [FAIL] Historical node ID found, but no active flow contains it.")
            else:
                logger.info("  [INFO] Replied-to message had no source node ID.")
        except Message.DoesNotExist:
            logger.warning("  [FAIL] The replied-to WAMID was not found in the Message database.")

    # --- Stage 3: If still no path, check for a new flow trigger ---
    if not next_edge:
        logger.info("[Stage 3] No historical path found. Checking if this is a trigger for a new flow...")
        try:
            original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
            template_name = original_message.text_content.replace("Sent template: ", "").strip()
            logger.info(f"  Replied-to message is a template: '{template_name}'. Looking for matching flows...")
            possible_flow = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at').first()
            if possible_flow:
                flow = possible_flow
                logger.info(f"  [PASS] Found matching active flow: '{flow.name}'")
                nodes, edges = flow.flow_data.get('nodes', []), flow.flow_data.get('edges', [])
                current_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data',{}).get('selectedTemplateName') == template_name), None)
                if current_node:
                    next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
                    if next_edge:
                         logger.info(f"  [SUCCESS] This is a new flow. Path found: '{current_node.get('id')}' -> '{next_edge.get('target')}' via handle '{user_input}'")
                    else:
                        logger.warning(f"  [FAIL] Found trigger template, but no edge matches handle '{user_input}'.")
                else:
                    logger.error("  [CRITICAL] Flow is supposed to be triggered by this template, but no matching start node was found in its data!")
            else:
                logger.info("  [INFO] No active flow is triggered by this template.")
        except Message.DoesNotExist:
            logger.info("  [INFO] Replied-to message is not a trigger template.")
    
    # --- Stage 4: Final check and execution ---
    logger.info("[Stage 4] Final check before execution...")
    if flow and current_node and next_edge:
        logger.info("  [PASS] All components (flow, current_node, next_edge) are valid. Proceeding to execution.")
        target_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
        if target_node:
            logger.info(f"  Target node found: '{target_node.get('id')}', Type: '{target_node.get('type')}'")
            return execute_flow_node(contact, flow, target_node) # This is where the message is actually sent
        else:
            logger.error(f"  [CRITICAL] Execution failed. The edge points to a target node ID '{next_edge.get('target')}' that does not exist in the flow data.")
            return False
    
    logger.error(f"--- [HALT] --- After all checks, could not determine a valid next step for contact {contact.wa_id} with input '{user_input}'. Flow is stopping.")
    return False


@csrf_exempt
def attribute_list_create_view(request):
    """ API for listing and creating Attributes. """
    if request.method == 'GET':
        attributes = Attribute.objects.all().order_by('name')
        data = [{'id': attr.id, 'name': attr.name, 'description': attr.description} for attr in attributes]
        return JsonResponse(data, safe=False)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        attr = Attribute.objects.create(name=data['name'], description=data.get('description', ''))
        return JsonResponse({'id': attr.id, 'name': attr.name, 'description': attr.description}, status=201)

@csrf_exempt
def attribute_detail_view(request, pk):
    """ API for updating or deleting a specific Attribute. """
    try:
        attr = Attribute.objects.get(pk=pk)
    except Attribute.DoesNotExist:
        return JsonResponse({'error': 'Attribute not found'}, status=404)

    if request.method == 'PUT':
        data = json.loads(request.body)
        attr.name = data.get('name', attr.name)
        attr.description = data.get('description', attr.description)
        attr.save()
        return JsonResponse({'id': attr.id, 'name': attr.name, 'description': attr.description})

    if request.method == 'DELETE':
        attr.delete()
        return JsonResponse({}, status=204)

# --- Webhook and API Views ---
# Add this to your Django views.py file
from .models import WhatsAppFlowForm
from django.utils import timezone
import json


# In contact_app/views.py
from .models import WhatsAppCall # Add this import
from django.views.decorators.http import require_http_methods

# At the top of your views.py file, update your Twilio configuration

import os
from django.conf import settings

# Twilio Configuration
TWILIO_ACCOUNT_SID = 'ACb1492fb21e0c67f4d1f1871e79aa56e7'
TWILIO_AUTH_TOKEN = 'dbf9980f385bc98b1d8948cbfc287df9'
TWILIO_PHONE_NUMBER = '+17375302454'

# Verify credentials are loaded


   # views.py
import json
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import logging

logger = logging.getLogger(__name__)

# Configuration - Add these to your settings.py
ACCESS_TOKEN = 'EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ'
PHONE_NUMBER_ID = '694609297073147'

# Twilio Configuration
TWILIO_ACCOUNT_SID = 'ACb1492fb21e0c67f4d1f1871e79aa56e7'
TWILIO_AUTH_TOKEN = 'dbf9980f385bc98b1d8948cbfc287df9'
TWILIO_PHONE_NUMBER = '+17375302454'
BUSINESS_PHONE_NUMBER = '+919080289501 '


if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    logger.error("Missing Twilio credentials! Check your environment variables or settings.")
    logger.error(f"TWILIO_ACCOUNT_SID: {'Set' if TWILIO_ACCOUNT_SID else 'Missing'}")
    logger.error(f"TWILIO_AUTH_TOKEN: {'Set' if TWILIO_AUTH_TOKEN else 'Missing'}")
    logger.error(f"TWILIO_PHONE_NUMBER: {'Set' if TWILIO_PHONE_NUMBER else 'Missing'}")

# Initialize Twilio client with error handling
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # Test the credentials
    account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    logger.info(f"Twilio client initialized successfully. Account: {account.friendly_name}")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")
    twilio_client = None

import os
@csrf_exempt
@require_http_methods(["POST"])
def initiate_whatsapp_call_view(request):
    """
    API endpoint to initiate a WhatsApp call from the business to a user.
    Expects a JSON payload: {"wa_id": "91xxxxxxxxxx"}
    """
    try:
        data = json.loads(request.body)
        user_wa_id = data.get('wa_id')

        if not user_wa_id:
            return JsonResponse({'status': 'error', 'message': 'wa_id is required.'}, status=400)
        
        contact, _ = ChatContact.objects.get_or_create(wa_id=user_wa_id)
        api_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/calls"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
        payload = {"recipient": user_wa_id}

        logger.info(f"Attempting to initiate WhatsApp call to {user_wa_id}...")
        response = requests.post(api_url, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code >= 400:
            logger.error(f"Meta API Error (Call Initiation): {response_data}")
            return JsonResponse({'status': 'error', 'meta_response': response_data}, status=response.status_code)

        call_id = response_data.get("call_id")
        if call_id:
            # Create a log for the outbound call
            WhatsAppCall.objects.create(
                call_id=call_id,
                contact=contact,
                direction='outbound',
                status='initiated' # The status will be updated by the webhook
            )
            logger.info(f"Successfully initiated call to {user_wa_id}. Call ID: {call_id}")
        
        return JsonResponse({'status': 'success', 'message': 'Call initiated.', 'call_id': call_id})

    except Exception as e:
        logger.error(f"Error in initiate_whatsapp_call_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def initiate_outbound_call(recipient_wa_id):
    """
    Initiate an outbound WhatsApp call to the specified recipient
    """
    if not twilio_client:
        logger.error("[Outbound Call] Twilio client not initialized. Cannot make outbound calls.")
        return False
    
    logger.info(f"[Outbound Call] Attempting to initiate WhatsApp call to {recipient_wa_id}...")
    
    # WhatsApp Calling API endpoint
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/calls"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Generate a unique call ID
    import uuid
    call_id = f"outbound_{uuid.uuid4().hex[:16]}"
    
    # Corrected payload structure for outbound calls
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_wa_id,
        "call_id": call_id,
        "action": "initiate"
    }
    
    try:
        logger.info(f"[Outbound Call] Sending request to WhatsApp API...")
        logger.info(f"[Outbound Call] URL: {url}")
        logger.info(f"[Outbound Call] Payload: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, headers=headers, json=data)
        
        logger.info(f"[Outbound Call] Response Status: {response.status_code}")
        logger.info(f"[Outbound Call] Response Headers: {dict(response.headers)}")
        logger.info(f"[Outbound Call] Response Body: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"[Outbound Call] Successfully initiated outbound call: {response_data}")
            
            # Store the outbound call info
            active_calls[call_id] = {
                'type': 'outbound',
                'recipient': recipient_wa_id,
                'status': 'initiated',
                'twilio_sid': None  # Will be set when Twilio call is created
            }
            
            return True
        else:
            error_data = response.json() if response.content else {}
            logger.error(f"[Outbound Call] Meta API Error: {error_data}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[Outbound Call] Request failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[Outbound Call] Unexpected error: {e}")
        return False


# Complete fix for your calling system

import json
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
ACCESS_TOKEN = 'EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ'
PHONE_NUMBER_ID = '694609297073147'

# Twilio Configuration  
TWILIO_ACCOUNT_SID = 'ACb1492fb21e0c67f4d1f1871e79aa56e7'
TWILIO_AUTH_TOKEN = 'dbf9980f385bc98b1d8948cbfc287df9'
TWILIO_PHONE_NUMBER = '+17375302454'

# FIXED: Clean business phone number (remove spaces and trailing space)
BUSINESS_PHONE_NUMBER = '+919080289501'  # Cleaned from '+91 90802 89501 '

BASE_URL_t = 'https://workregister1-g7pf.onrender.com/register/whatsapp'

# Initialize Twilio client
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    logger.info(f"Twilio client initialized successfully. Account: {account.friendly_name}")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")
    twilio_client = None

# CRITICAL: Ensure active_calls is a dictionary (not a set)
active_calls = {}  # This MUST be a dictionary, not set()

def debug_active_calls():
    """Debug function to ensure active_calls is correct type"""
    global active_calls
    logger.info(f"active_calls type: {type(active_calls)}")
    logger.info(f"active_calls content: {active_calls}")
    
    if not isinstance(active_calls, dict):
        logger.error("CRITICAL: active_calls is not a dictionary! Converting...")
        active_calls = {}
        logger.info("Fixed: active_calls is now a dictionary")
    else:
        logger.info("active_calls is correctly a dictionary")

# Call this on startup
# Add this enhanced status webhook to see exactly what's happening

@csrf_exempt 
@require_http_methods(["POST", "GET"])
def twilio_status_diagnostic(request, whatsapp_call_id):
    """Enhanced status webhook with detailed diagnostics"""
    
    # Log all the data Twilio sends
    logger.info(f"=== TWILIO STATUS DIAGNOSTIC ===")
    logger.info(f"WhatsApp Call ID: {whatsapp_call_id}")
    logger.info(f"Method: {request.method}")
    
    # Get all possible status fields from Twilio
    status_data = {}
    if request.method == 'POST':
        for key, value in request.POST.items():
            status_data[key] = value
    else:
        for key, value in request.GET.items():
            status_data[key] = value
    
    logger.info(f"All Twilio data: {status_data}")
    
    # Extract key fields
    call_status = status_data.get('CallStatus', 'unknown')
    call_sid = status_data.get('CallSid', 'unknown')
    call_duration = status_data.get('CallDuration', '0')
    dial_status = status_data.get('DialCallStatus', 'not_provided')
    direction = status_data.get('Direction', 'unknown')
    
    # Log detailed analysis
    logger.info(f"Call Status Analysis:")
    logger.info(f"  CallStatus: {call_status}")
    logger.info(f"  CallSid: {call_sid}")
    logger.info(f"  Duration: {call_duration} seconds")
    logger.info(f"  DialStatus: {dial_status}")
    logger.info(f"  Direction: {direction}")
    
    # Analyze what went wrong
    if call_status == 'busy':
        logger.warning("CALL BUSY: The destination number is busy or unavailable")
        logger.warning("Possible causes:")
        logger.warning("  1. Phone is actually busy/engaged")
        logger.warning("  2. Phone is turned off")
        logger.warning("  3. Carrier is blocking the call")
        logger.warning("  4. International calling restrictions")
    elif call_status == 'no-answer':
        logger.warning("NO ANSWER: The destination didn't pick up")
    elif call_status == 'failed':
        logger.error("CALL FAILED: Check the number and account settings")
    elif call_status == 'canceled':
        logger.info("CALL CANCELED: Call was terminated before completion")
    elif call_status == 'completed':
        logger.info("CALL COMPLETED: Call was successful")
        if int(call_duration) == 0:
            logger.warning("But duration is 0 - call may not have been answered")
    
    try:
        if call_status in ['completed', 'canceled', 'failed', 'busy', 'no-answer']:
            # Terminate WhatsApp call
            terminate_response = call_whatsapp_api(whatsapp_call_id, 'terminate')
            if terminate_response:
                logger.info(f"Terminated WhatsApp call {whatsapp_call_id}")
            
            # Clean up
            if whatsapp_call_id in active_calls:
                del active_calls[whatsapp_call_id]
                logger.info(f"Cleaned up call {whatsapp_call_id}")
        
        return HttpResponse('OK')
        
    except Exception as e:
        logger.error(f"Status processing error: {e}")
        return HttpResponse('ERROR', status=500)

# Test function to make a direct call and see what happens
def test_business_number_directly():
    """Test calling the business number directly to see the result"""
    try:
        if not twilio_client:
            logger.error("Cannot test - Twilio client not available")
            return
        
        logger.info("=== TESTING BUSINESS NUMBER DIRECTLY ===")
        logger.info(f"Calling {BUSINESS_PHONE_NUMBER} from {TWILIO_PHONE_NUMBER}")
        
        # Make a direct test call
        test_call = twilio_client.calls.create(
            to=BUSINESS_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            twiml='<Response><Say>This is a test call to check connectivity.</Say><Pause length="5"/><Hangup/></Response>',
            status_callback=f"{BASE_URL_t}/twilio-status-test/",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed', 'busy', 'no-answer', 'failed'],
            status_callback_method='POST'
        )
        
        logger.info(f"Test call created: {test_call.sid}")
        logger.info("Check logs in a few seconds to see the result")
        
    except Exception as e:
        logger.error(f"Test call failed: {e}")
        if hasattr(e, 'code'):
            logger.error(f"Twilio Error Code: {e.code}")
        if hasattr(e, 'msg'):
            logger.error(f"Twilio Error Message: {e.msg}")


# Add this endpoint for test call status
@csrf_exempt
@require_http_methods(["POST"])
def twilio_status_test(request):
    """Handle status for test calls"""
    
    status_data = dict(request.POST.items())
    logger.info(f"=== TEST CALL STATUS ===")
    logger.info(f"Status data: {status_data}")
    
    call_status = status_data.get('CallStatus', 'unknown')
    call_duration = status_data.get('CallDuration', '0')
    
    if call_status == 'busy':
        logger.error("❌ BUSINESS NUMBER IS BUSY OR BLOCKED")
        logger.error("Solutions to try:")
        logger.error("  1. Check if the phone is turned on and available")
        logger.error("  2. Try calling from a different number to test")
        logger.error("  3. Contact your business phone provider about international calls")
        logger.error("  4. Check if there are call forwarding settings")
    elif call_status == 'completed' and int(call_duration) > 0:
        logger.info("✅ BUSINESS NUMBER IS WORKING - Call connected successfully")
    elif call_status == 'no-answer':
        logger.warning("⚠️ BUSINESS NUMBER RINGS but no one answered")
    else:
        logger.info(f"Test result: {call_status}, Duration: {call_duration}")
    
    return HttpResponse('OK')

# Alternative solution: Use a different business number for testing
def suggest_alternative_numbers():
    """Suggest using alternative numbers for testing"""
    
    logger.info("=== ALTERNATIVE TESTING SUGGESTIONS ===")
    logger.info("If your business number keeps showing 'busy', try these alternatives:")
    logger.info(f"1. Test with your own Twilio number: {TWILIO_PHONE_NUMBER}")
    logger.info("2. Use a different phone number you have access to")
    logger.info("3. Use a landline number if available")
    logger.info("4. Check with your phone provider about call forwarding settings")
    
    # You can temporarily test with your Twilio number
    logger.info("For immediate testing, you can temporarily change:")
    logger.info(f"   BUSINESS_PHONE_NUMBER = '{TWILIO_PHONE_NUMBER}'")
    logger.info("This will make the system call your Twilio number back")

def generate_twilio_sdp_offer():
    """Generate SDP offer for Twilio WebRTC connection"""
    return """v=0
o=- 4611731400430051336 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111 63 9 0 8 13 110 126
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:4ZcD
a=ice-pwd:2/1muCWoOi3uHTH0tqs1Kh+F
a=ice-options:trickle
a=fingerprint:sha-256 28:E8:97:FC:B8:53:24:B8:1F:AB:C1:29:E3:A0:1E:8B:38:36:C2:14:D7:76:66:83:1A:B4:EA:98:AA:64:15:1C
a=setup:active
a=mid:0
a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level
a=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time
a=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
a=sendrecv
a=msid:- 750e164d-7709-4d6b-b17f-0b9d2e4ca9de
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=rtcp-fb:111 transport-cc
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:63 red/48000/2
a=fmtp:63 111/111
a=rtpmap:9 G722/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:13 CN/8000
a=rtpmap:110 telephone-event/48000
a=rtpmap:126 telephone-event/8000
a=ssrc:1009384203 cname:nKXm1Y4g3wAKu91t
a=ssrc:1009384203 msid:- 750e164d-7709-4d6b-b17f-0b9d2e4ca9de"""

def call_whatsapp_api(call_id, action, sdp=None, callback_data=None):
    """Make API call to WhatsApp Calling API"""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/calls"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "messaging_product": "whatsapp",
        "call_id": call_id,
        "action": action
    }
    
    if sdp and action in ['pre_accept', 'accept']:
        data["session"] = {
            "sdp_type": "answer",
            "sdp": sdp
        }
    
    if callback_data and action == 'accept':
        data["biz_opaque_callback_data"] = callback_data
    
    try:
        logger.info(f"[WhatsApp API] Calling {action} for call {call_id}")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json() if response.content else {}
            logger.error(f"[WhatsApp API] Error response: {error_data}")
            return {"success": False, "error": error_data}
            
    except Exception as e:
        logger.error(f"[WhatsApp API] Error for {action}: {e}")
        return {"success": False, "error": str(e)}

def create_twilio_call_fixed(whatsapp_call_id, from_number):
    """Create Twilio call with proper setup"""
    global active_calls
    
    if not twilio_client:
        logger.error("Twilio client not initialized")
        return None
    
    try:
        # Ensure active_calls is a dict before using it
        if not isinstance(active_calls, dict):
            logger.error("active_calls is not a dict! Converting...")
            active_calls = {}
        
        # Add to active_calls BEFORE creating Twilio call
        active_calls[whatsapp_call_id] = {
            'twilio_sid': None,
            'whatsapp_from': from_number,
            'whatsapp_to': BUSINESS_PHONE_NUMBER,
            'status': 'initiating',
            'created_at': datetime.now().isoformat()
        }
        logger.info(f"Added {whatsapp_call_id} to active_calls")
        
        # Construct callback URLs
        callback_url = f"{BASE_URL_t}/twilio-connect/{whatsapp_call_id}/"
        status_callback_url = f"{BASE_URL_t}/twilio-status/{whatsapp_call_id}/"
        
        logger.info(f"Creating Twilio call:")
        logger.info(f"  From: {TWILIO_PHONE_NUMBER}")
        logger.info(f"  To: {BUSINESS_PHONE_NUMBER}")
        logger.info(f"  Callback: {callback_url}")
        
        # Create the call
        call = twilio_client.calls.create(
            to=BUSINESS_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=callback_url,
            status_callback=status_callback_url,
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
            timeout=60
        )
        
        # Update with Twilio SID
        active_calls[whatsapp_call_id]['twilio_sid'] = call.sid
        active_calls[whatsapp_call_id]['status'] = 'connecting'
        
        logger.info(f"Successfully created Twilio call {call.sid}")
        return call.sid
        
    except Exception as e:
        logger.error(f"Failed to create Twilio call: {e}")
        
        # Clean up on failure
        if whatsapp_call_id in active_calls:
            del active_calls[whatsapp_call_id]
        
        return None

@csrf_exempt 
@require_http_methods(["POST", "GET"])
def twilio_status_fast(request, whatsapp_call_id):
    """Fast-responding status webhook"""
    
    call_status = request.POST.get('CallStatus', 'unknown')
    logger.info(f"Status: {call_status} for {whatsapp_call_id}")
    
    try:
        if call_status in ['completed', 'canceled', 'failed']:
            # Clean up quickly
            call_whatsapp_api(whatsapp_call_id, 'terminate')
            
            if whatsapp_call_id in active_calls:
                del active_calls[whatsapp_call_id]
        
        return HttpResponse('OK')
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return HttpResponse('ERROR', status=500)


# ALTERNATIVE: Direct dial without webhooks
def create_twilio_call_direct(whatsapp_call_id, from_number):
    """Create Twilio call with direct dialing (no webhooks)"""
    global active_calls
    
    if not twilio_client:
        return None
    
    try:
        # Add to active calls
        active_calls[whatsapp_call_id] = {
            'status': 'connecting',
            'created_at': datetime.now().isoformat()
        }
        
        # Create call that directly dials without webhooks
        call = twilio_client.calls.create(
            to=BUSINESS_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            # Use TwiML directly instead of webhook URL
            twiml=f'<Response><Say>Connecting WhatsApp call</Say><Dial timeout="30">{BUSINESS_PHONE_NUMBER}</Dial></Response>',
            status_callback=f"{BASE_URL_t}/twilio-status/{whatsapp_call_id}/",
            status_callback_event=['completed']
        )
        
        active_calls[whatsapp_call_id]['twilio_sid'] = call.sid
        logger.info(f"Created direct call {call.sid}")
        return call.sid
        
    except Exception as e:
        logger.error(f"Direct call failed: {e}")
        if whatsapp_call_id in active_calls:
            del active_calls[whatsapp_call_id]
        return None
    
def handle_calling_webhook_direct(change, contact):
    """Handle calling with direct Twilio dialing"""
    global active_calls
    
    if not isinstance(active_calls, dict):
        active_calls = {}
    
    if change.get('field') == 'calls':
        calls = change.get('value', {}).get('calls', [])
        
        for call in calls:
            call_id = call.get('id')
            event = call.get('event')
            from_number = call.get('from')
            
            logger.info(f"Call {event}: {call_id}")
            
            if event == 'connect':
                # Pre-accept
                sdp_answer = generate_twilio_sdp_offer()
                pre_accept_response = call_whatsapp_api(call_id, 'pre_accept', sdp_answer)
                
                if pre_accept_response and pre_accept_response.get('success'):
                    # Use direct calling instead of webhooks
                    twilio_call_sid = create_twilio_call_direct(call_id, from_number)
                    
                    if twilio_call_sid:
                        # Accept WhatsApp call
                        accept_response = call_whatsapp_api(
                            call_id, 
                            'accept', 
                            sdp_answer,
                            f"twilio_sid:{twilio_call_sid}"
                        )
                        
                        if accept_response and accept_response.get('success'):
                            logger.info(f"SUCCESS: Direct call setup for {call_id}")
                        else:
                            logger.error(f"Failed to accept {call_id}")
            
            elif event == 'terminate':
                logger.info(f"Call terminated: {call_id}")
                if call_id in active_calls:
                    twilio_sid = active_calls[call_id].get('twilio_sid')
                    if twilio_sid:
                        try:
                            twilio_client.calls(twilio_sid).update(status='completed')
                        except:
                            pass
                    del active_calls[call_id]
# Use this fixed function in your webhook
# Replace handle_calling_webhook with handle_calling_webhook_fixed
@csrf_exempt
@require_http_methods(["POST"])
def terminate_call(request):
    """Manually terminate a call"""
    try:
        data = json.loads(request.body)
        call_id = data.get('call_id')
        
        if not call_id:
            return JsonResponse({'error': 'call_id is required'}, status=400)
        
        # Terminate WhatsApp call
        response = call_whatsapp_api(call_id, 'terminate')
        
        # Terminate associated Twilio call
        if call_id in active_calls:
            twilio_sid = active_calls[call_id]['twilio_sid']
            try:
                twilio_client.calls(twilio_sid).update(status='completed')
            except:
                pass
            del active_calls[call_id]
        
        if response and response.get('success'):
            return JsonResponse({'status': 'Call terminated successfully'})
        else:
            return JsonResponse({'error': 'Failed to terminate call'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.error(f"Error terminating call: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
debug_active_calls()


@csrf_exempt
@require_http_methods(["POST", "GET"])
def twilio_connect_fast(request, whatsapp_call_id):
    """Fast-responding webhook to prevent timeouts"""
    
    logger.info(f"Twilio connect: {whatsapp_call_id}")
    
    # Create response immediately
    response = VoiceResponse()
    
    try:
        # Simple, fast response
        response.say("Connecting your WhatsApp call...")
        response.dial(BUSINESS_PHONE_NUMBER, timeout=30)
        
        # Log success
        logger.info(f"Connected call {whatsapp_call_id}")
        
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Connect error: {e}")
        
        # Fast error response
        response = VoiceResponse()
        response.say("Call connection failed.")
        response.hangup()
        
        return HttpResponse(str(response), content_type='text/xml')


# Add a new endpoint to handle dial action results
@csrf_exempt
@require_http_methods(["POST"])
def twilio_dial_action(request, whatsapp_call_id):
    """Handle the result of the dial action"""
    
    logger.info(f"=== TWILIO DIAL ACTION ===")
    logger.info(f"WhatsApp Call ID: {whatsapp_call_id}")
    logger.info(f"POST params: {dict(request.POST)}")
    
    dial_status = request.POST.get('DialCallStatus')
    call_duration = request.POST.get('DialCallDuration', '0')
    
    logger.info(f"Dial Status: {dial_status}")
    logger.info(f"Dial Duration: {call_duration}")
    
    response = VoiceResponse()
    
    if dial_status in ['completed', 'answered']:
        logger.info("Call was successful")
        response.say("Thank you for using our service. Goodbye.")
    else:
        logger.info(f"Call failed with status: {dial_status}")
        response.say("We were unable to connect your call. Please try again later or contact us directly.")
    
    response.hangup()
    return HttpResponse(str(response), content_type='text/xml')


# Add a simple test endpoint to verify your webhooks work
@csrf_exempt
def test_twilio_webhook(request):
    """Test endpoint to verify Twilio can reach your server"""
    
    logger.info(f"=== TWILIO TEST WEBHOOK ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Path: {request.path}")
    logger.info(f"Headers: {dict(request.META)}")
    
    if request.method == 'POST':
        logger.info(f"POST data: {dict(request.POST)}")
    
    response = VoiceResponse()
    response.say("This is a test. Your webhook is working correctly.")
    response.hangup()
    
    logger.info(f"Returning test TwiML: {str(response)}")
    return HttpResponse(str(response), content_type='text/xml')




# Also add this function to test if your business number needs verification
def check_business_number_verification():
    """Check if the business number is verified"""
    try:
        if not twilio_client:
            logger.error("Twilio client not available")
            return
        
        logger.info("=== CHECKING BUSINESS NUMBER VERIFICATION ===")
        
        # Check verified caller IDs
        caller_ids = twilio_client.outgoing_caller_ids.list()
        verified_numbers = [cid.phone_number for cid in caller_ids]
        
        logger.info(f"Verified caller IDs: {verified_numbers}")
        logger.info(f"Business number: {BUSINESS_PHONE_NUMBER}")
        logger.info(f"Is business number verified: {BUSINESS_PHONE_NUMBER in verified_numbers}")
        
        if BUSINESS_PHONE_NUMBER not in verified_numbers:
            logger.warning("🚨 BUSINESS NUMBER NOT VERIFIED 🚨")
            logger.warning("This will cause calls to fail on trial accounts!")
        else:
            logger.info("✅ Business number is properly verified")
    
    except Exception as e:
        logger.error(f"Error checking verification: {e}")

# Call this on startup
check_business_number_verification()

# Alternative simpler approach - just test if we can make a basic call
def test_basic_twilio_call():
    """Test making a basic Twilio call to see if credentials work"""
    try:
        if not twilio_client:
            logger.error("Cannot test - Twilio client not available")
            return
        
        logger.info("=== TESTING BASIC TWILIO CALL ===")
        
        # Try to make a very simple call to your own Twilio number
        test_call = twilio_client.calls.create(
            to=TWILIO_PHONE_NUMBER,  # Call your own Twilio number
            from_=TWILIO_PHONE_NUMBER,  # From the same number
            url=f"{BASE_URL_t}/test-twilio/",  # Simple test webhook
            timeout=10
        )
        
        logger.info(f"✅ Test call created successfully: {test_call.sid}")
        logger.info("This means your Twilio credentials work!")
        
    except Exception as e:
        logger.error(f"❌ Test call failed: {e}")
        logger.error("This indicates an issue with your Twilio setup")


@csrf_exempt
def whatsapp_webhook_view(request):
    """
    Handles all incoming WhatsApp events from Meta.
    This version correctly processes both messages and status updates in any order.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        logger.info(f"====== INCOMING WEBHOOK ======\n{json.dumps(data, indent=2)}")
        if any('flows' in change.get('value', {}) for entry in data.get('entry', []) for change in entry.get('changes', [])):
            logger.info("DEBUG: FLOWS DATA DETECTED IN WEBHOOK!")
        else:
            logger.info("DEBUG: No flows data in this webhook call")
        
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    
                    # --- HANDLE CALLING WEBHOOKS FIRST (NO CONTACT NEEDED) ---
                    if change.get('field') == 'calls':
                        # Create a dummy contact for calling webhook or get from call data
                        # We need to extract contact info from the call data itself
                        calls = value.get('calls', [])
                        for call in calls:
                            from_number = call.get('from')
                            if from_number:
                                contact, _ = ChatContact.objects.get_or_create(wa_id=from_number)
                                handle_calling_webhook_direct(change, contact)
                        continue  # Skip further processing for call webhooks
                    
                    # --- PROCESS MESSAGES ---
                    if 'messages' in value:
                        for msg in value.get('messages', []):
                            contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
                            message_type = msg.get('type')
                            replied_to_wamid = msg.get('context', {}).get('id')
                            user_input = None
                            
                            # Fix the location processing in webhook:
                            if message_type == 'location':
                                location = msg.get('location', {})
                                longitude = location.get('longitude')
                                latitude = location.get('latitude')
                                
                                logger.info(f"DEBUG-LOCATION: Received location from {contact.wa_id}: Long={longitude}, Lat={latitude}")

                                # Check if a session is waiting for this location
                                session = UserFlowSession.objects.filter(contact=contact, is_waiting_for_location=True).first()
                                if session:
                                    logger.info(f"DEBUG-LOCATION: Found session waiting for location: {session}")
                                    
                                    # FIXED: Use the attribute objects directly
                                    # Save longitude attribute
                                    if session.longitude_attribute and longitude is not None:
                                        ContactAttributeValue.objects.update_or_create(
                                            contact=contact, attribute=session.longitude_attribute,
                                            defaults={'value': str(longitude)}
                                        )
                                        logger.info(f"DEBUG-LOCATION: Saved longitude {longitude} to attribute {session.longitude_attribute.name}")
                                        
                                    # Save latitude attribute  
                                    if session.latitude_attribute and latitude is not None:
                                        ContactAttributeValue.objects.update_or_create(
                                            contact=contact, attribute=session.latitude_attribute,
                                            defaults={'value': str(latitude)}
                                        )
                                        logger.info(f"DEBUG-LOCATION: Saved latitude {latitude} to attribute {session.latitude_attribute.name}")
                                    
                                    # Find the next node from the 'onLocationReceived' handle
                                    flow = session.flow
                                    current_node_id = session.current_node_id
                                    edges = flow.flow_data.get('edges', [])
                                    next_edge = next((e for e in edges if e.get('source') == current_node_id and e.get('sourceHandle') == 'onLocationReceived'), None)
                                    
                                    logger.info(f"DEBUG-LOCATION: Looking for next edge from {current_node_id} with handle 'onLocationReceived': {next_edge}")
                                    
                                    # Clear the waiting state
                                    session.is_waiting_for_location = False
                                    session.longitude_attribute = None
                                    session.latitude_attribute = None
                                    session.save()
                                    
                                    if next_edge:
                                        next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
                                        logger.info(f"DEBUG-LOCATION: Found next node: {next_node}")
                                        if next_node:
                                            execute_flow_node(contact, flow, next_node)
                                    else:
                                        logger.info("DEBUG-LOCATION: No next edge found, ending flow")
                                        session.delete()
                                else:
                                    logger.info(f"DEBUG-LOCATION: No session found waiting for location for contact {contact.wa_id}")
                                continue

                            # Fix the image processing in webhook:
                            if message_type == 'image':
                                # Get the session first
                                session = UserFlowSession.objects.filter(contact=contact).first()
                                
                                if session and session.waiting_for_image_attribute:
                                    image_id = msg.get('image', {}).get('id')
                                    logger.info(f"DEBUG-IMAGE: Received image from {contact.wa_id}, ID: {image_id}")
                                    
                                    media_url = get_media_url_from_id(image_id)
                                    if media_url:
                                        ContactAttributeValue.objects.update_or_create(
                                            contact=contact, attribute=session.waiting_for_image_attribute,
                                            defaults={'value': media_url}
                                        )
                                        logger.info(f"DEBUG-IMAGE: Saved image URL {media_url} to attribute {session.waiting_for_image_attribute.name}")
                                    else:
                                        logger.error(f"DEBUG-IMAGE: Failed to get media URL for image ID {image_id}")
                                    
                                    # Find next node from 'onImageReceived' handle
                                    flow = session.flow
                                    edges = flow.flow_data.get('edges', [])
                                    next_edge = next((e for e in edges if e.get('source') == session.current_node_id and e.get('sourceHandle') == 'onImageReceived'), None)
                                    
                                    logger.info(f"DEBUG-IMAGE: Looking for next edge with handle 'onImageReceived': {next_edge}")
                                    
                                    # Clear the waiting state
                                    session.waiting_for_image_attribute = None
                                    session.save()
                                    
                                    if next_edge:
                                        next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
                                        logger.info(f"DEBUG-IMAGE: Found next node: {next_node}")
                                        if next_node:
                                            execute_flow_node(contact, flow, next_node)
                                    else:
                                        logger.info("DEBUG-IMAGE: No next edge found, ending flow")
                                        session.delete()
                                    continue
                                else:
                                    logger.info(f"DEBUG-IMAGE: No session waiting for image for contact {contact.wa_id}")

                            # 5. ADD TEXT PROCESSING FOR askQuestionNode (INSERT BEFORE EXISTING FLOW LOGIC):
                            if message_type == 'text':
                                user_input = msg.get('text', {}).get('body')
                                logger.info(f"DEBUG-TEXT: Received text message: '{user_input}' from {contact.wa_id}")
                                
                                # FIRST: Check if there's a session waiting for text input (askQuestionNode)
                                session = UserFlowSession.objects.filter(contact=contact, waiting_for_attribute__isnull=False).first()
                                
                                if session and session.waiting_for_attribute:
                                    logger.info(f"DEBUG-QUESTION: Found session waiting for text input. Attribute: {session.waiting_for_attribute.name}")
                                    
                                    # Save the answer to the specified attribute
                                    ContactAttributeValue.objects.update_or_create(
                                        contact=contact, 
                                        attribute=session.waiting_for_attribute,
                                        defaults={'value': user_input}
                                    )
                                    logger.info(f"DEBUG-QUESTION: Successfully saved answer '{user_input}' to attribute '{session.waiting_for_attribute.name}'")
                                    
                                    # Find next node from 'onAnswer' handle
                                    flow = session.flow
                                    edges = flow.flow_data.get('edges', [])
                                    next_edge = next((e for e in edges if e.get('source') == session.current_node_id and e.get('sourceHandle') == 'onAnswer'), None)
                                    
                                    logger.info(f"DEBUG-QUESTION: Looking for next edge with handle 'onAnswer': {next_edge}")
                                    
                                    # Clear the waiting state
                                    session.waiting_for_attribute = None
                                    session.save()
                                    logger.info(f"DEBUG-QUESTION: Cleared waiting_for_attribute state")
                                    
                                    if next_edge:
                                        next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
                                        logger.info(f"DEBUG-QUESTION: Found next node: {next_node.get('id') if next_node else 'None'}")
                                        if next_node:
                                            execute_flow_node(contact, flow, next_node)
                                        else:
                                            logger.error(f"DEBUG-QUESTION: Next node not found for target: {next_edge.get('target')}")
                                            session.delete()
                                    else:
                                        logger.info("DEBUG-QUESTION: No next edge found, ending flow")
                                        session.delete()
                                    continue  # Important: Skip further processing for this message
                                
                                else:
                                    logger.info(f"DEBUG-QUESTION: No session waiting for text input from {contact.wa_id}")

                            elif message_type == 'button':
                                user_input = msg.get('button', {}).get('text')
                            elif message_type == 'interactive':
                                interactive = msg.get('interactive', {})
                                if interactive.get('type') == 'list_reply': 
                                    user_input = interactive.get('list_reply', {}).get('id')
                                elif interactive.get('type') == 'button_reply': 
                                    user_input = interactive.get('button_reply', {}).get('title')
                                elif interactive.get('type') == 'nfm_reply':
                                    logger.info(f"DEBUG-FLOW-NFM: Received nfm_reply from {contact.wa_id}")
                                    
                                    # Enhanced debug logging first
                                    enhanced_webhook_debug_logging(data)
                                    
                                    # Process the nfm_reply
                                    success = process_nfm_reply_in_webhook(contact, interactive)
                                    
                                    if success:
                                        logger.info(f"DEBUG-FLOW-NFM: Successfully processed flow completion")
                                        continue  # Skip further processing
                                    else:
                                        logger.error(f"DEBUG-FLOW-NFM: Failed to process flow completion")
                                        continue
                                elif interactive.get('type') == 'call_permission_reply':
                                    call_permission = interactive.get('call_permission_reply', {})
                                    if call_permission.get('response') == 'accept':
                                        logger.info(f"Received call permission from {contact.wa_id}. Triggering outbound call NOW.")
                                        # THIS IS THE MISSING STEP:
                                        initiate_outbound_call(contact.wa_id)
                                    else:
                                        logger.warning(f"User {contact.wa_id} denied call permission.")
                                    continue 

                            logger.info(f"DEBUG-FLOW: Extracted user_input='{user_input}' and replied_to_wamid='{replied_to_wamid}'")
                            flow_handled = False
                            if user_input and replied_to_wamid:
                                flow_handled = try_execute_flow_step(contact, user_input, replied_to_wamid)
                            elif user_input:
                                logger.info(f"User sent input '{user_input}' without replying to a flow message. No action taken.")
                                pass
                                # Go to the next message
                            if flow_handled:
                                logger.info("DEBUG-FLOW: Flow was successfully handled. Skipping fallback logic.")
                                continue

                    # --- PROCESS STATUS UPDATES ---
                    if 'statuses' in value:
                        for status in value.get('statuses', []):
                            if status.get('status') == 'read':
                                try_execute_status_trigger(status.get('id'), status.get('recipient_id'))

        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
            
    return JsonResponse({"status": "success"}, status=200)




def get_media_url_from_id(media_id):
    """Uses the Meta API to get a permanent URL for a media object."""
    url = f"{META_API_URL}/{media_id}/"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('url')
    except requests.exceptions.RequestException as e:
        logger.error(f"Could not retrieve media URL for ID {media_id}: {e}")
        return None
    
from .models import WhatsAppFlowForm, Attribute, ContactAttributeValue # Add necessary imports

def handle_flow_completion(contact, response_data):
    """
    Parses the submitted Flow data and saves it to the contact's attributes.
    """
    logger.info(f"=== FLOW COMPLETION DEBUG START ===")
    logger.info(f"Contact: {contact.wa_id}")
    logger.info(f"Response data: {response_data}")
    
    # Find the user's current session to know which flow was just completed
    session = UserFlowSession.objects.filter(contact=contact, waiting_for_flow_completion=True).first()
    logger.info(f"Session found: {session}")
    
    if session:
        logger.info(f"Session flow_form_id: {session.flow_form_id}")
        logger.info(f"Session current_node_id: {session.current_node_id}")
        logger.info(f"Session flow name: {session.flow.name if session.flow else 'None'}")
    
    if not session:
        logger.warning("No session found waiting for flow completion. Cannot map attributes.")
        return

    try:
        # Get the flow form from our database to find its structure
        flow_form = WhatsAppFlowForm.objects.get(meta_flow_id=session.flow_form_id)
        
        # FIXED: Create proper mapping from component ID to attribute
        attribute_map = {}
        screens_data = flow_form.screens_data
        
        # Handle nested structure properly
        if isinstance(screens_data, dict) and 'screens_data' in screens_data:
            screens_list = screens_data['screens_data']
        else:
            screens_list = screens_data if isinstance(screens_data, list) else []

        # Build mapping from component ID to attribute name
        for screen in screens_list:
            for component in screen.get('components', []):
                component_id = component.get('id')
                component_label = component.get('label')
                
                # Map component ID to its label (which should match attribute name)
                if component_id and component_label:
                    attribute_map[component_id] = component_label
                    logger.info(f"Mapped component '{component_id}' to attribute '{component_label}'")

        logger.info(f"Complete attribute map: {attribute_map}")

        # Process the user's submitted data
        saved_count = 0
        for component_id, user_value in response_data.items():
            attribute_name = attribute_map.get(component_id)
            
            if not attribute_name:
                logger.warning(f"No mapping found for component_id '{component_id}'. Skipping.")
                continue

            try:
                # Find the attribute in our database (case-insensitive search)
                attribute_to_save = Attribute.objects.get(name__iexact=attribute_name)
                
                # Handle different data types
                if isinstance(user_value, (list, dict)):
                    value_to_save = json.dumps(user_value)
                else:
                    value_to_save = str(user_value)
                
                # Save the user's submitted value
                ContactAttributeValue.objects.update_or_create(
                    contact=contact,
                    attribute=attribute_to_save,
                    defaults={'value': value_to_save}
                )
                
                logger.info(f"✓ Saved attribute '{attribute_name}' with value '{value_to_save}' for contact {contact.wa_id}")
                saved_count += 1

            except Attribute.DoesNotExist:
                logger.warning(f"Attribute '{attribute_name}' not found in database. Creating it automatically.")
                
                # Auto-create the attribute if it doesn't exist
                try:
                    new_attribute = Attribute.objects.create(
                        name=attribute_name,
                        description=f"Auto-created from form: {flow_form.name}"
                    )
                    
                    value_to_save = json.dumps(user_value) if isinstance(user_value, (list, dict)) else str(user_value)
                    
                    ContactAttributeValue.objects.create(
                        contact=contact,
                        attribute=new_attribute,
                        value=value_to_save
                    )
                    
                    logger.info(f"✓ Created and saved new attribute '{attribute_name}' with value '{value_to_save}'")
                    saved_count += 1
                    
                except Exception as create_error:
                    logger.error(f"Failed to auto-create attribute '{attribute_name}': {create_error}")
                
            except Exception as save_error:
                logger.error(f"Error saving attribute '{attribute_name}': {save_error}")
                
        logger.info(f"Successfully saved {saved_count} attributes from flow completion")
        
        # Find the next node in the visual flow
        flow = session.flow
        current_node_id = session.current_node_id
        edges = flow.flow_data.get('edges', [])

        logger.info(f"=== LOOKING FOR NEXT NODE ===")
        logger.info(f"Current node ID: {current_node_id}")
        logger.info(f"Total edges in flow: {len(edges)}")

        # Look for 'onSuccess' handle first, then fallback to single unnamed edge
        next_edge = next((e for e in edges if e.get('source') == current_node_id and e.get('sourceHandle') == 'onSuccess'), None)
        
        if not next_edge:
            source_edges = [e for e in edges if e.get('source') == current_node_id]
            if len(source_edges) == 1:
                logger.info(f"No 'onSuccess' handle found, using single available edge")
                next_edge = source_edges[0]
        
        # Clear the session BEFORE continuing to next node
        session.delete()
        logger.info("✓ Flow session cleared")

        if next_edge:
            next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
            if next_node:
                logger.info(f"✓ Continuing to next node: {next_node.get('id')}")
                execute_flow_node(contact, flow, next_node)
            else:
                logger.warning(f"Next node with ID {next_edge.get('target')} not found in flow data")
        else:
            logger.info(f"✓ Flow completed successfully. No next node found for {current_node_id}")

    except WhatsAppFlowForm.DoesNotExist:
        logger.error(f"Flow form with meta_flow_id '{session.flow_form_id}' not found in database")
    except Exception as e:
        logger.error(f"Error in handle_flow_completion: {e}", exc_info=True)
    
    logger.info(f"=== FLOW COMPLETION DEBUG END ===")
# In your Django views.py, add this endpoint:

@csrf_exempt
def debug_flow_completion(request):
    """Debug endpoint to test flow completion manually"""
    if request.method == 'POST':
        data = json.loads(request.body)
        wa_id = data.get('wa_id')
        response_data = data.get('response_data')
        
        contact = ChatContact.objects.get(wa_id=wa_id)
        handle_flow_completion(contact, response_data)
        
        return JsonResponse({'status': 'success'})
# FIXED: Webhook handler for nfm_reply
def process_nfm_reply_in_webhook(contact, interactive_data):
    """
    Extract and process nfm_reply data from webhook
    """
    logger.info(f"DEBUG-FLOW-NFM: Processing nfm_reply from {contact.wa_id}")
    
    nfm_reply = interactive_data.get('nfm_reply', {})
    response_json_str = nfm_reply.get('response_json', '{}')
    
    logger.info(f"DEBUG-FLOW-NFM: Raw response_json_str = {response_json_str}")
    
    try:
        # Parse the JSON response
        response_json = json.loads(response_json_str)
        logger.info(f"DEBUG-FLOW-NFM: Parsed response_json = {json.dumps(response_json, indent=2)}")
        
        # Call the flow completion handler
        handle_flow_completion(contact, response_json)
        logger.info(f"DEBUG-FLOW-NFM: Successfully processed flow completion")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"DEBUG-FLOW-NFM: Failed to parse response_json: {e}")
        logger.error(f"DEBUG-FLOW-NFM: Raw string was: {repr(response_json_str)}")
        return False
        
    except Exception as e:
        logger.error(f"DEBUG-FLOW-NFM: Error processing nfm_reply: {e}", exc_info=True)
        return False


# ENHANCED: Debug logging for webhook
def enhanced_webhook_debug_logging(data):
    """
    Enhanced logging to debug webhook structure
    """
    logger.info(f"====== ENHANCED WEBHOOK DEBUG ======")
    logger.info(f"Full webhook data: {json.dumps(data, indent=2)}")
    
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            
            # Log all available keys in the value object
            logger.info(f"Available keys in 'value': {list(value.keys())}")
            
            # Check for messages
            if 'messages' in value:
                for i, msg in enumerate(value['messages']):
                    logger.info(f"Message {i}: type='{msg.get('type')}', keys={list(msg.keys())}")
                    
                    if msg.get('type') == 'interactive':
                        interactive = msg.get('interactive', {})
                        logger.info(f"Interactive type: '{interactive.get('type')}'")
                        logger.info(f"Interactive keys: {list(interactive.keys())}")
                        
                        if interactive.get('type') == 'nfm_reply':
                            nfm_reply = interactive.get('nfm_reply', {})
                            logger.info(f"NFM Reply keys: {list(nfm_reply.keys())}")
                            logger.info(f"Response JSON raw: {repr(nfm_reply.get('response_json'))}")


# INTEGRATION: Updated webhook section for nfm_reply
def handle_nfm_reply_in_webhook(msg, contact):
    """
    Replace the existing nfm_reply handling in your webhook with this
    """
    interactive = msg.get('interactive', {})
    
    if interactive.get('type') == 'nfm_reply':
        logger.info(f"DEBUG-FLOW-NFM: Received nfm_reply from {contact.wa_id}")
        
        # Enhanced debug logging
        enhanced_webhook_debug_logging({'entry': [{'changes': [{'value': {'messages': [msg]}}]}]})
        
        # Process the nfm_reply
        success = process_nfm_reply_in_webhook(contact, interactive)
        
        if success:
            logger.info(f"DEBUG-FLOW-NFM: Successfully processed nfm_reply")
        else:
            logger.error(f"DEBUG-FLOW-NFM: Failed to process nfm_reply")
        
        return True  # Indicate this message was handled
    
    return False  # Not an nfm_reply




from django.shortcuts import get_object_or_404
def flow_form_detail_api(request, form_id):
    """
    Get detailed information about a specific form.
    """
    try:
        form = get_object_or_404(WhatsAppFlowForm, id=form_id)
        
        screens_data = form.screens_data
        if isinstance(screens_data, str):
            try:
                screens_data = json.loads(screens_data)
            except:
                screens_data = []
        
        form_data = {
            'id': str(form.id),
            'name': form.name,
            'template_body': form.template_body,
            'template_button_text': form.template_button_text,
            'template_category': form.template_category,
            'screens_data': screens_data,
            'meta_flow_id': form.meta_flow_id,
            'flow_status': form.flow_status,
            'template_status': form.template_status,
            'created_at': form.created_at.isoformat() if form.created_at else None,
            'updated_at': form.updated_at.isoformat() if form.updated_at else None
        }
        
        return JsonResponse({
            'status': 'success',
            'form': form_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching form detail: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
def update_flow_api(request, flow_id):
    """API endpoint to update an existing flow."""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            flow = Flow.objects.get(id=flow_id)
            
            # Update fields if provided
            if 'name' in data:
                flow.name = data['name']
            if 'template_name' in data:
                flow.template_name = data['template_name']
            if 'flow' in data:
                flow.flow_data = data['flow']
            if 'is_active' in data:
                flow.is_active = data['is_active']
            
            flow.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Flow updated successfully'
            })
        except Flow.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Flow not found'}, status=404)
        except Exception as e:
            logger.error(f"Error updating flow {flow_id}: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def update_flow_status_api(request, flow_id):
    """API endpoint to toggle the active status of a flow."""
    if request.method == 'POST':
        try:
            flow = Flow.objects.get(pk=flow_id)
            data = json.loads(request.body)
            flow.is_active = data.get('is_active', flow.is_active)
            flow.save()
            return JsonResponse({'status': 'success', 'message': 'Status updated.'})
        except Flow.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)



# In your views.py
from .models import WhatsAppFlowForm # Make sure this is imported












def get_whatsapp_forms_api(request):
    """
    API endpoint that returns all saved WhatsApp Flows from the local database.
    This is the single source of truth for your React Flow Builder.
    """
    try:
        forms = WhatsAppFlowForm.objects.all().order_by('-created_at')
        
        forms_data = []
        for form in forms:
            # We map the model fields to the keys the React frontend expects
            forms_data.append({
                'name': form.name,
                'id': form.id,
                'flow_id': form.meta_flow_id,
                'structure': form.screens_data, # Contains the full structure
                
                # We include all other fields for the detailed preview
                'template_category': form.template_category,
                'template_body': form.template_body,
                'template_button_text': form.template_button_text,
                'flow_status': form.flow_status,
                'template_name': form.template_name,
                'template_status': form.template_status,
                'created_at': form.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return JsonResponse({'status': 'success', 'forms': forms_data})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



def get_flow_details_api_view(request, flow_id):
    """
    API endpoint that fetches the full details of a single WhatsApp Flow from Meta.
    """
    try:
        # Query your new model
        forms = WhatsAppFlowForm.objects.all().order_by('-created_at')
        
        forms_data = []
        for form in forms:
            # We map the model fields to the keys the React frontend expects
            forms_data.append({
                'name': form.name,
                'flow_id': form.meta_flow_id,
                'structure': form.screens_data, # This now contains the full structure
            })

        # The key here is "forms" which your React FlowBuilder expects
        return JsonResponse({'status': 'success', 'forms': forms_data})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
# ... (keep all your other imports: JsonResponse, csrf_exempt, models, etc.)
import logging
logger = logging.getLogger(__name__)

from .models import Flows as Flow


def debug_flow_data(flow_id):
    """Debug utility function to check flow structure."""
    try:
        flow = Flow.objects.get(pk=flow_id)
        print(f"--- Debugging Flow: '{flow.name}' (ID: {flow.id}) ---")
        
        flow_data = flow.flow_data
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        
        if not nodes:
            print("This flow has no nodes.")
            return

        print("\nNODES:")
        for node in nodes:
            print(f"- Node ID: {node.get('id')}, Type: {node.get('type')}")
            
        if not edges:
            print("\nThis flow has no edges.")
            return
            
        print("\nEDGES (Connections):")
        for edge in edges:
            print(f"- From Node '{edge.get('source')}' --> To Node '{edge.get('target')}' (Using handle: '{edge.get('sourceHandle')}')")
            
        # Mismatch Check
        print("\nCHECKING FOR MISMATCHES...")
        all_node_ids = {n.get('id') for n in nodes}
        mismatches_found = False
        for edge in edges:
            if edge.get('source') not in all_node_ids:
                print(f"  [!!] MISMATCH FOUND: Edge source '{edge.get('source')}' does not match any known Node ID.")
                mismatches_found = True
            if edge.get('target') not in all_node_ids:
                print(f"  [!!] MISMATCH FOUND: Edge target '{edge.get('target')}' does not match any known Node ID.")
                mismatches_found = True
        
        if not mismatches_found:
            print("  No ID mismatches found between nodes and edges.")
            
    except Flow.DoesNotExist:
        print(f"Error: Flow with ID {flow_id} not found.")


def get_whatsapp_templates_api(request):
    """API endpoint to fetch approved WhatsApp templates for the React frontend."""
    try:
        url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,components,status"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_templates = response.json().get('data', [])
        
        templates_data = []
        for t in all_templates:
            if t.get('status') == 'APPROVED':
                buttons = []
                template_components = t.get('components', [])

                # --- THIS IS THE CORRECTED LOGIC ---
                for comp in template_components:
                    # First, find the component with type 'BUTTONS'
                    if comp.get('type') == 'BUTTONS':
                        # Then, loop through the 'buttons' array inside it
                        for btn in comp.get('buttons', []):
                            # Check the type of the INDIVIDUAL button
                            if btn.get('type') == 'QUICK_REPLY':
                                # If it's a quick reply, add it to our list
                                buttons.append({'text': btn.get('text')})

                templates_data.append({
                    'name': t.get('name'),
                    'components': template_components,
                    'buttons': buttons
                })
        
        return JsonResponse(templates_data, safe=False)
    except Exception as e:
        logger.error(f"Failed to fetch templates for API: {e}")
        return JsonResponse({"error": "Could not load templates."}, status=500)


def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    data = [{
        'id': f.id, 
        'name': f.name, 
        'template_name': f.template_name, 
        'updated_at': f.updated_at.isoformat() if f.updated_at else None,
        'created_at': f.created_at.isoformat() if f.created_at else None,
        'is_active': f.is_active
    } for f in flows]
    return JsonResponse(data, safe=False)



@csrf_exempt
def save_flow_api(request):
    """API endpoint to save a new flow definition from the React frontend."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            flow_name = data.get('name')
            trigger_template_name = data.get('template_name')
            flow_data = data.get('flow')
            
            if not all([flow_name, flow_data]):
                return JsonResponse({'status': 'error', 'message': 'Missing flow name or flow data.'}, status=400)

            # Create new flow
            flow_obj = Flow.objects.create(
                name=flow_name,
                template_name=trigger_template_name,
                flow_data=flow_data,
                is_active=True
            )
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Flow created successfully.',
                'flow_id': flow_obj.id
            })
        except Exception as e:
            logger.error(f"Error saving flow: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

# --- UPDATE THIS VIEW ---
def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    # Add the new is_active field to the response
    data = [{
        'id': f.id, 
        'name': f.name, 
        'template_name': f.template_name, 
        'updated_at': f.updated_at,
        'is_active': f.is_active # <-- NEW
    } for f in flows]
    return JsonResponse(data, safe=False)

# --- ADD THESE THREE NEW VIEWS ---
def get_flow_detail_api(request, flow_id):
    """API endpoint to get the full data for a single flow for editing."""
    try:
        flow = Flow.objects.get(pk=flow_id)
        data = {
            'id': flow.id,
            'name': flow.name,
            'template_name': flow.template_name,
            'flow_data': flow.flow_data,
            'is_active': flow.is_active,
            'created_at': flow.created_at.isoformat() if flow.created_at else None,
            'updated_at': flow.updated_at.isoformat() if flow.updated_at else None,
        }
        return JsonResponse({'status': 'success', 'flow': data})
    except Flow.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching flow {flow_id}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def delete_flow_api(request, flow_id):
    """API endpoint to delete a flow."""
    if request.method == 'DELETE':
        try:
            flow = Flow.objects.get(pk=flow_id)
            flow.delete()
            return JsonResponse({'status': 'success', 'message': 'Flow deleted successfully.'})
        except Flow.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting flow {flow_id}: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


import requests
import mimetypes # Add this import if not already present
from django.core.files.uploadedfile import InMemoryUploadedFile # Add this import

@csrf_exempt
def upload_media_to_meta_api(request):
    """
    API endpoint to upload any media file (image, video, document, etc.) 
    directly to Meta's WhatsApp Business API and return the Meta Media ID.
    """
    if request.method == 'POST':
        # The key for the file in the form data should be 'media'
        if 'media' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'No media file provided.'}, status=400)

        media_file: InMemoryUploadedFile = request.FILES['media']
        
        # Determine the file's content type (e.g., 'image/jpeg', 'application/pdf')
        content_type, _ = mimetypes.guess_type(media_file.name)
        if not content_type:
            return JsonResponse({'status': 'error', 'message': 'Could not determine the file type.'}, status=400)

        upload_url = f"{META_API_URL}/{PHONE_NUMBER_ID}/media"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        }
        files = {
            'file': (media_file.name, media_file.read(), content_type),
            'type': (None, content_type),  # Important for Meta API
            'messaging_product': (None, 'whatsapp'),
        }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()  # Raise an exception for HTTP errors (like 4xx or 5xx)
            meta_response = response.json()
            
            media_id = meta_response.get('id')
            if media_id:
                logger.info(f"Media uploaded to Meta, Media ID: {media_id}")
                return JsonResponse({'status': 'success', 'media_id': media_id})
            else:
                logger.error(f"Meta upload response missing media ID: {meta_response}")
                return JsonResponse({'status': 'error', 'message': 'Meta did not return a media ID.'}, status=500)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading media to Meta: {e}. Response: {e.response.text if e.response else 'No response.'}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Failed to upload media to Meta: {e}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error in upload_media_to_meta_api: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
@csrf_exempt
def upload_media_to_meta_api(request):
    """
    API endpoint to upload any media file (image, video, document, etc.) 
    directly to Meta's WhatsApp Business API and return the Meta Media ID.
    """
    if request.method == 'POST':
        # The key for the file in the form data should be 'media'
        if 'media' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'No media file provided.'}, status=400)

        media_file: InMemoryUploadedFile = request.FILES['media']
        
        # Determine the file's content type (e.g., 'image/jpeg', 'application/pdf')
        content_type, _ = mimetypes.guess_type(media_file.name)
        if not content_type:
            return JsonResponse({'status': 'error', 'message': 'Could not determine the file type.'}, status=400)

        upload_url = f"{META_API_URL}/{PHONE_NUMBER_ID}/media"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        }
        files = {
            'file': (media_file.name, media_file.read(), content_type),
            'type': (None, content_type),  # Important for Meta API
            'messaging_product': (None, 'whatsapp'),
        }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()  # Raise an exception for HTTP errors (like 4xx or 5xx)
            meta_response = response.json()
            
            media_id = meta_response.get('id')
            if media_id:
                logger.info(f"Media uploaded to Meta, Media ID: {media_id}")
                return JsonResponse({'status': 'success', 'media_id': media_id})
            else:
                logger.error(f"Meta upload response missing media ID: {meta_response}")
                return JsonResponse({'status': 'error', 'message': 'Meta did not return a media ID.'}, status=500)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading media to Meta: {e}. Response: {e.response.text if e.response else 'No response.'}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Failed to upload media to Meta: {e}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error in upload_media_to_meta_api: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def upload_image_to_meta_api(request):
    """
    API endpoint to upload an image file directly to Meta's WhatsApp Business API
    and return the Meta Media ID.
    """
    if request.method == 'POST':
        if 'image' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'No image file provided.'}, status=400)

        image_file: InMemoryUploadedFile = request.FILES['image']
        
        # Determine content type (e.g., image/jpeg, image/png)
        content_type, _ = mimetypes.guess_type(image_file.name)
        if not content_type or not content_type.startswith('image/'):
            return JsonResponse({'status': 'error', 'message': 'Invalid file type. Only images are allowed.'}, status=400)

        upload_url = f"{META_API_URL}/{PHONE_NUMBER_ID}/media"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        }
        files = {
            'file': (image_file.name, image_file.read(), content_type),
            'type': (None, content_type), # Important for Meta API
            'messaging_product': (None, 'whatsapp'),
        }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status() # Raise an exception for HTTP errors
            meta_response = response.json()
            
            media_id = meta_response.get('id')
            if media_id:
                logger.info(f"Image uploaded to Meta, Media ID: {media_id}")
                return JsonResponse({'status': 'success', 'media_id': media_id})
            else:
                logger.error(f"Meta upload response missing media ID: {meta_response}")
                return JsonResponse({'status': 'error', 'message': 'Meta did not return a media ID.'}, status=500)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading image to Meta: {e}. Response: {response.text if 'response' in locals() else 'No response.'}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Failed to upload image to Meta: {e}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error in upload_image_to_meta_api: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)