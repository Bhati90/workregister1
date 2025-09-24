# contact_app/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
# from corsheaders.decorators import cors_exempt       # Import cors_exempt
import json
from .tasks import process_api_request_node
from django.shortcuts import render # Make sure render is imported

# def home_page(request):
#     return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})

# from .models import Flow, Message, ChatContact # Make sure these are imported
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
PHONE_NUMBER_ID = "705449502657013" # Replace with your Phone Number ID
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


def handle_flow_response(request_body):
    """
    Handle incoming Flow responses from Meta.
    This is called when a user completes or cancels a Flow form.
    """
    try:
        data = json.loads(request_body)
        
        # Flow responses come in a different format
        flow_token = data.get('flow_token', '')
        response_json = data.get('response_json', {})
        action = data.get('action', '')
        
        logger.info(f"DEBUG-FLOW-RESPONSE: Received flow response")
        logger.info(f"Flow token: {flow_token}")
        logger.info(f"Action: {action}")
        logger.info(f"Response data: {json.dumps(response_json, indent=2)}")
        
        # Extract contact info from flow_token
        # Format: flow_{wa_id}_{node_id}_{timestamp}
        token_parts = flow_token.split('_')
        if len(token_parts) >= 4:
            wa_id = token_parts[1]
            node_id = token_parts[2]
            
            try:
                contact = ChatContact.objects.get(wa_id=wa_id)
                session = UserFlowSession.objects.filter(
                    contact=contact,
                    waiting_for_flow_completion=True
                ).first()
                
                if not session:
                    logger.warning(f"No session found waiting for flow completion for {wa_id}")
                    return
                
                flow = session.flow
                current_node_id = session.current_node_id
                
                # Determine the outcome
                next_handle = None
                if action == 'COMPLETE':
                    next_handle = 'onComplete'
                    # Save form data to attributes
                    save_flow_form_data(contact, session.flow_form_id, response_json)
                elif action == 'CANCEL':
                    next_handle = 'onError'
                elif action == 'TIMEOUT':
                    next_handle = 'onTimeout'
                else:
                    next_handle = 'onError'
                
                logger.info(f"DEBUG-FLOW-RESPONSE: Using handle '{next_handle}'")
                
                # Clear the waiting state
                session.waiting_for_flow_completion = False
                session.flow_form_id = None
                session.save()
                
                # Find next node
                edges = flow.flow_data.get('edges', [])
                next_edge = next((e for e in edges if e.get('source') == current_node_id and e.get('sourceHandle') == next_handle), None)
                
                if next_edge:
                    next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
                    if next_node:
                        logger.info(f"DEBUG-FLOW-RESPONSE: Continuing to next node: {next_node.get('id')}")
                        execute_flow_node(contact, flow, next_node)
                    else:
                        logger.error(f"DEBUG-FLOW-RESPONSE: Next node not found")
                        session.delete()
                else:
                    logger.info(f"DEBUG-FLOW-RESPONSE: No next edge found, ending flow")
                    session.delete()
                    
            except ChatContact.DoesNotExist:
                logger.error(f"Contact {wa_id} not found")
            except Exception as e:
                logger.error(f"Error processing flow response: {e}")
        else:
            logger.error(f"Invalid flow token format: {flow_token}")
            
    except Exception as e:
        logger.error(f"Error handling flow response: {e}")

def save_flow_form_data(contact, flow_form_id, response_data):
    """
    Save the flow form response data to contact attributes.
    """
    try:
        from .models import WhatsAppFlowForm
        flow_form = WhatsAppFlowForm.objects.get(id=flow_form_id)
        
        logger.info(f"DEBUG-FLOW-SAVE: Saving form data for {contact.wa_id}")
        logger.info(f"Response data: {json.dumps(response_data, indent=2)}")
        
        # The response_data contains the user's answers
        # Format is typically: {"component_id": "value", ...}
        
        for screen in flow_form.screens_data:
            for component in screen.get('components', []):
                component_id = component.get('id')
                component_label = component.get('label', '')
                
                if component_id in response_data:
                    value = response_data[component_id]
                    
                    # Create or get attribute based on component label/id
                    attribute_name = f"form_{flow_form.name}_{component_label}".lower().replace(' ', '_')
                    attribute, created = Attribute.objects.get_or_create(
                        name=attribute_name,
                        defaults={'description': f'Form field: {component_label}'}
                    )
                    
                    # Handle different value types
                    if isinstance(value, list):
                        value_str = ', '.join(str(v) for v in value)
                    else:
                        value_str = str(value)
                    
                    # Save the value
                    ContactAttributeValue.objects.update_or_create(
                        contact=contact,
                        attribute=attribute,
                        defaults={'value': value_str}
                    )
                    
                    logger.info(f"DEBUG-FLOW-SAVE: Saved '{value_str}' to attribute '{attribute_name}'")
        
        logger.info(f"DEBUG-FLOW-SAVE: Successfully saved all form data")
        
    except Exception as e:
        logger.error(f"Error saving flow form data: {e}")

# OPTIONAL: Add a test endpoint for the API Request node
@csrf_exempt
def test_api_request(request):
    """Test endpoint for API Request node functionality"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Extract request details
            api_url = data.get('apiUrl')
            method = data.get('method', 'GET').upper()
            headers = data.get('headers', '{}')
            request_body = data.get('requestBody', '{}')
            
            # Prepare request
            request_config = {
                'method': method,
                'url': api_url,
                'timeout': 10
            }
            
            # Parse headers
            try:
                if headers:
                    request_config['headers'] = json.loads(headers)
            except json.JSONDecodeError:
                request_config['headers'] = {}
            
            # Parse body for non-GET requests
            if method != 'GET' and request_body:
                try:
                    request_config['json'] = json.loads(request_body)
                except json.JSONDecodeError:
                    request_config['data'] = request_body
            
            # Make request
            response = requests.request(**request_config)
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            
            return JsonResponse({
                'success': True,
                'status': response.status_code,
                'data': response_data,
                'headers': dict(response.headers)
            })
            
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# def extract_json_path(data, path):
   
#     try:
#         current = data
#         parts = path.split('.')
        
#         for part in parts:
#             if part.isdigit():
#                 # Handle array index
#                 current = current[int(part)]
#             else:
#                 # Handle object key
#                 current = current[part]
                
#         return current
#     except (KeyError, IndexError, TypeError, ValueError):
#         return None


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

@csrf_exempt
def test_echo_endpoint(request):
    """Echo endpoint for testing API requests - returns exactly what it receives"""
    
    # Log the incoming request
    logger.info(f"ECHO-ENDPOINT: Received {request.method} request")
    logger.info(f"ECHO-ENDPOINT: Headers: {dict(request.headers)}")
    
    if request.method == 'POST':
        try:
            # Parse the request body
            raw_body = request.body.decode('utf-8')
            logger.info(f"ECHO-ENDPOINT: Raw body: {raw_body}")
            
            data = json.loads(raw_body)
            logger.info(f"ECHO-ENDPOINT: Parsed JSON: {data}")
            
            # Return comprehensive response
            response_data = {
                "success": True,
                "message": "Echo endpoint received your request",
                "received_data": data,
                "request_info": {
                    "method": request.method,
                    "content_type": request.headers.get('Content-Type', 'not specified'),
                    "timestamp": str(timezone.now()),
                    "body_length": len(raw_body)
                },
                "headers_received": dict(request.headers),
                "echo_test": "This confirms your API request node is working!"
            }
            
            logger.info(f"ECHO-ENDPOINT: Sending response: {response_data}")
            return JsonResponse(response_data, status=200)
            
        except json.JSONDecodeError as e:
            logger.error(f"ECHO-ENDPOINT: Invalid JSON: {e}")
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON in request body",
                "received_raw": request.body.decode('utf-8')
            }, status=400)
            
        except Exception as e:
            logger.error(f"ECHO-ENDPOINT: Unexpected error: {e}")
            return JsonResponse({
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }, status=500)
    
    elif request.method == 'GET':
        # Handle GET requests for basic testing
        return JsonResponse({
            "success": True,
            "message": "Echo endpoint is working",
            "method": "GET",
            "timestamp": str(timezone.now()),
            "test_url": request.build_absolute_uri()
        })
    
    else:
        # Handle other HTTP methods
        return JsonResponse({
            "success": False,
            "error": f"Method {request.method} not supported",
            "supported_methods": ["GET", "POST"]
        }, status=405)

# Add this to your urls.py file (in the urlpatterns list):
# path('echo/', test_echo_endpoint, name='test_echo'),

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
                    
                    # --- CORRECTED LOGIC: Process messages and statuses independently ---
                    
                    # 1. Check for and process any incoming messages
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
 # Stop further processing
    
                            elif message_type == 'button':
                                user_input = msg.get('button', {}).get('text')
                            elif message_type == 'interactive':
                                interactive = msg.get('interactive', {})
                                if interactive.get('type') == 'list_reply': user_input = interactive.get('list_reply', {}).get('id')
                                elif interactive.get('type') == 'button_reply': user_input = interactive.get('button_reply', {}).get('title')
                            # elif message_type == 'text': user_input = msg.get('text', {}).get('body')
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
                    # 2. Check for and process any status updates
                    # 2. Check for and process any status updates
                    if 'flows' in value:
                        logger.info(f"DEBUG-WEBHOOK: Found 'flows' section in webhook")
                        for flow_data in value.get('flows', []):
                            logger.info(f"DEBUG-WEBHOOK: Processing flow data: {json.dumps(flow_data, indent=2)}")
                            try:
                                response_json_str = flow_data.get('response_json', '{}')
                                contact_wa_id = flow_data.get('from')
                                
                                logger.info(f"DEBUG-WEBHOOK: contact_wa_id = {contact_wa_id}")
                                logger.info(f"DEBUG-WEBHOOK: response_json_str = {response_json_str}")
                                
                                response_json = json.loads(response_json_str)
                                
                                if contact_wa_id and response_json:
                                    contact, _ = ChatContact.objects.get_or_create(wa_id=contact_wa_id)
                                    logger.info(f"DEBUG-WEBHOOK: About to call handle_flow_completion for {contact.wa_id}")
                                    
                                    # Call the function
                                    handle_flow_completion(contact, response_json)
                                    logger.info(f"DEBUG-WEBHOOK: Successfully called handle_flow_completion")
                                else:
                                    logger.error(f"DEBUG-WEBHOOK: Missing contact_wa_id or empty response_json")
                                    
                            except Exception as e:
                                logger.error(f"DEBUG-WEBHOOK: Error processing flow data: {e}", exc_info=True)
                    else:
                        logger.info(f"DEBUG-WEBHOOK: No 'flows' key found in webhook data")
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
        # This is where we create the mapping. We'll map the component LABEL to the attribute NAME.
        # This is more readable than using component_id.
        attribute_map = {}
        # Handle both possible data structures
        screens_data = flow_form.screens_data
        if isinstance(screens_data, dict) and 'screens_data' in screens_data:
            screens_list = screens_data['screens_data']
        else:
            screens_list = screens_data if isinstance(screens_data, list) else []

        for screen in screens_list:
            for component in screen.get('components', []):
                # For now, let's assume the component label is the same as the attribute name
                # e.g., A component labeled "Full Name" saves to an attribute named "Full Name"
                attribute_map[component['id']] = component['label']

        logger.info(f"Using attribute map for flow '{flow_form.name}': {attribute_map}")

        # Now, iterate through the user's submitted data
        for component_id, user_value in response_data.items():
            attribute_name = attribute_map.get(component_id)
            if not attribute_name:
                continue # Skip if we don't have a mapping for this component

            try:
                # Find the attribute in our database
                attribute_to_save = Attribute.objects.get(name__iexact=attribute_name)
                
                # Save the user's submitted value
                ContactAttributeValue.objects.update_or_create(
                    contact=contact,
                    attribute=attribute_to_save,
                    defaults={'value': str(user_value)}
                )
                logger.info(f"Saved attribute '{attribute_name}' with value '{user_value}' for contact {contact.wa_id}")

            except Attribute.DoesNotExist:
                logger.warning(f"Attribute '{attribute_name}' not found in database. Cannot save value.")
                
        # The flow is complete, so we can now find the next node in the visual flow
        # The flow is complete, so we can now find the next node in the visual flow
        flow = session.flow
        current_node_id = session.current_node_id
        edges = flow.flow_data.get('edges', [])

        logger.info(f"=== LOOKING FOR NEXT NODE ===")
        logger.info(f"Current node ID: {current_node_id}")
        logger.info(f"Total edges in flow: {len(edges)}")
        logger.info(f"All edges from current node: {[e for e in edges if e.get('source') == current_node_id]}")

        # First, try to find an edge specifically from the 'onSuccess' handle
        next_edge = next((e for e in edges if e.get('source') == current_node_id and e.get('sourceHandle') == 'onSuccess'), None)
        logger.info(f"Found 'onSuccess' edge: {next_edge}")
        # If not found, and there's only ONE possible exit, take that path as a fallback.
        if not next_edge:
            source_edges = [e for e in edges if e.get('source') == current_node_id]
            if len(source_edges) == 1:
                logger.info(f"No 'onSuccess' handle found for node {current_node_id}, but found a single unnamed exit edge. Proceeding.")
                next_edge = source_edges[0]
        # --- END OF IMPROVEMENT ---
        
        # IMPORTANT: Clear the user's session AFTER finding the next step
        session.delete()
        logger.info("Flow session cleared.")

        if next_edge:
            next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
            if next_node:
                logger.info(f"Continuing to next node: {next_node.get('id')}")
                # This is your existing function that sends the next message
                execute_flow_node(contact, flow, next_node)
            else:
                logger.warning(f"Next node with ID {next_edge.get('target')} not found in flow data.")
        else:
            logger.info(f"Flow completed. No next node found for {current_node_id}.")

    except Exception as e:
        logger.error(f"Error in handle_flow_completion: {e}", exc_info=True)# API endpoint to fetch available forms for the fronten


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




# In your views.py
from .models import WhatsAppFlowForm # Make sure this is imported

#
# >>> THIS IS THE ONLY VIEW YOU NEED TO GET THE LIST OF FLOWS <<<
#
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

#
# >>> YOU CAN DELETE get_flow_details_api_view AS IT IS NO LONGER NEEDED <<<
#
# In your views.py
# In your views.py
# In your views.py

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

# ... (keep your whatsapp_webhook_view and other views)
# Add this to flow/views.py for debugging purposes
from .models import Flows as Flow

def debug_flow_data(flow_id):
    """
    A utility function to print the structure of a flow's data to find mismatches.
    Run this in the Django shell: python manage.py shell
    """
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

# ... (keep all your other views like save_flow_api etc.)
# ... (keep all your other views like save_flow_api etc.)
# NEW API VIEW 2: To save the flow from React


def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    data = [{'id': f.id, 'name': f.name, 'template_name': f.template_name, 'updated_at': f.updated_at} for f in flows]
    return JsonResponse(data, safe=False)


# contact_app/views.py

# ...

@csrf_exempt
def save_flow_api(request):
    """API endpoint to save or update a flow definition from the React frontend."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            flow_name = data.get('name')
            # The 'template_name' is still useful for identifying the trigger
            trigger_template_name = data.get('template_name')
            flow_data = data.get('flow')
            
            if not all([flow_name, flow_data]):
                return JsonResponse({'status': 'error', 'message': 'Missing flow name or flow data.'}, status=400)

            # --- CHANGE THIS LOGIC ---
            # Use the flow's name as the unique identifier to update or create
            flow_obj, created = Flow.objects.update_or_create(
                name=flow_name,
                defaults={
                    'template_name': trigger_template_name, # Save the trigger template
                    'flow_data': flow_data
                }
            )
            # --- END OF CHANGE ---
            
            status_message = "Flow created." if created else "Flow updated."
            return JsonResponse({'status': 'success', 'message': status_message})
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
        # Return all the data the frontend needs to rebuild the canvas
        data = {
            'id': flow.id,
            'name': flow.name,
            'flow_data': flow.flow_data,
            'is_active': flow.is_active,
        }
        return JsonResponse(data)
    except Flow.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)

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