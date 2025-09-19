# contact_app/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
# from corsheaders.decorators import cors_exempt       # Import cors_exempt
import json

from django.shortcuts import render # Make sure render is imported

# def home_page(request):
#     return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})

# from .models import Flow, Message, ChatContact # Make sure these are imported
from registration.models import ChatContact, Message
from .models import Flows as Flow
from .models import UserFlowSessions as UserFlowSession
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

API_VERSION = 'v19.0'
META_API_URL = f"https://graph.facebook.com/{API_VERSION}"
PHONE_NUMBER_ID = 705449502657013
META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
WABA_ID = "1477047197063313"

def home_page(request):
    return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})

@csrf_exempt
def whatsapp_webhook_view(request):
    """Handles all incoming WhatsApp events, prioritizing dynamic flows."""
    logger.info("====== WEBHOOK URL HAS BEEN HIT ======")
    
    if request.method == 'POST':
        logger.info("====== Webhook is a POST request. Attempting to read body. ======")
        
        data = json.loads(request.body)
        logger.info(f"====== INCOMING WEBHOOK BODY ======\n{json.dumps(data, indent=2)}")
        
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    if 'messages' in value:
                        for msg in value.get('messages', []):
                            contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
                            contact.last_contact_at = timezone.now()
                            contact.save()
                            
                            message_type = msg.get('type')
                            replied_to_wamid = msg.get('context', {}).get('id')
                            user_input = None
                            
                            # Extract user input based on message type
                            if message_type == 'text':
                                user_input = msg.get('text', {}).get('body')
                            elif message_type == 'button':
                                user_input = msg.get('button', {}).get('text')
                            elif message_type == 'interactive':
                                interactive = msg.get('interactive', {})
                                interactive_type = interactive.get('type')
                                
                                if interactive_type == 'button_reply':
                                    user_input = interactive.get('button_reply', {}).get('title')
                                elif interactive_type == 'list_reply':
                                    # Handle list selection
                                    list_reply = interactive.get('list_reply', {})
                                    user_input = list_reply.get('id')  # This is the row ID we set
                                    logger.info(f"List selection received: {user_input}")
                            
                            logger.info(f"DEBUG-FLOW: Extracted user_input='{user_input}' and replied_to_wamid='{replied_to_wamid}'")
                            
                            flow_handled = False
                            if user_input and replied_to_wamid:
                                flow_handled = try_execute_flow_step(contact, user_input, replied_to_wamid)
                            elif user_input:
                                logger.info(f"User sent input '{user_input}' without replying to a flow message. No action taken.")
                                
                            if flow_handled:
                                logger.info("DEBUG-FLOW: Flow was successfully handled. Skipping fallback logic.")
                                continue
                            
                    elif 'statuses' in value:
                        for status_update in value.get('statuses', []):
                            if status_update.get('status') == 'read':
                                wamid = status_update.get('id')
                                wa_id = status_update.get('recipient_id')
                                logger.info(f"Received 'read' status for message {wamid} from user {wa_id}.")
                                try_execute_status_trigger(wamid, wa_id)

    
        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
        
        return JsonResponse({"status": "success"}, status=200)

def try_execute_status_trigger(wamid, wa_id):
    """
    Executes a flow step triggered by a 'read' status update.
    """
    try:
        message = Message.objects.get(wamid=wamid)
        contact = ChatContact.objects.get(wa_id=wa_id)
        session = UserFlowSession.objects.filter(contact=contact).first()
        
        source_node_id = message.source_node_id
        flow = None
        
        # --- NEW FALLBACK LOGIC ---
        # If the source_node_id is missing, it might be the initial trigger template.
        if not source_node_id and message.message_type == 'template':
            logger.info(f"Message {wamid} has no source node. Checking if it's a trigger template.")
            template_name = message.text_content.replace("Sent template: ", "").strip()
            # Find the flow that this template triggers
            possible_flow = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at').first()
            if possible_flow:
                flow = possible_flow
                nodes = flow.flow_data.get('nodes', [])
                # Find the starting template node in that flow
                start_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data', {}).get('selectedTemplateName') == template_name), None)
                if start_node:
                    source_node_id = start_node.get('id')
                    logger.info(f"Identified trigger template. Deduced source node ID: {source_node_id}")

        # If a session exists, use its flow.
        elif session:
            flow = session.flow

        if not flow or not source_node_id:
            logger.warning("Could not determine a flow or source node for this status trigger. Halting.")
            return False
        
        edges = flow.flow_data.get('edges', [])
        # Find the edge connected to the "onRead" handle
        next_edge = next((e for e in edges if e.get('source') == source_node_id and e.get('sourceHandle') == 'onRead'), None)

        if not next_edge:
            logger.info(f"No 'onRead' trigger found for node {source_node_id}.")
            return False

        nodes = flow.flow_data.get('nodes', [])
        target_node_id = next_edge.get('target')
        target_node = next((n for n in nodes if n.get('id') == target_node_id), None)

        if not target_node:
            logger.error(f"'onRead' edge points to a non-existent target node ID: {target_node_id}")
            return False
            
        logger.info(f"Executing 'onRead' trigger from node {source_node_id} to {target_node_id}.")
        # Re-use the main flow execution logic to send the message and update the session
        return execute_flow_node(contact, flow, target_node)

    except (Message.DoesNotExist, ChatContact.DoesNotExist):
        logger.warning(f"Could not find message or contact for status update (wamid: {wamid})")
        return False
    except Exception as e:
        logger.error(f"CRITICAL STATUS TRIGGER ERROR: {e}", exc_info=True)
        return False


def execute_flow_node(contact, flow, target_node):
    """
    Helper function to construct and send a message for a given target node
    and update the user's session. Now includes all node types.
    """
    target_node_id = target_node.get('id')
    node_type = target_node.get('type')
    node_data = target_node.get('data', {})
    
    payload = {
        "messaging_product": "whatsapp",
        "to": contact.wa_id
    }
    message_type_to_save = node_type
    text_content_to_save = f"Flow Step: {node_type}"

    # Build the payload based on the node type
    if node_type == 'textNode':
        payload = {"type": "text", "text": {"body": node_data.get('text', '...')}}
        message_type_to_save = 'text'
        text_content_to_save = node_data.get('text', '...')
    
    elif node_type == 'templateNode':
        # This logic is for sending a template *during* a flow, not starting one.
        components = []
        if 'headerUrl' in node_data and node_data['headerUrl']:
            # Assuming image for simplicity, extend as needed for video/document
            components.append({"type": "header", "parameters": [{"type": "image", "image": {"link": node_data['headerUrl']}}]})
        
        body_params = []
        for i in range(1, 10):
            var_key = f'bodyVar{i}'
            if var_key in node_data and node_data[var_key]:
                body_params.append({"type": "text", "text": node_data[var_key]})
        
        if body_params:
            components.append({"type": "body", "parameters": body_params})

        payload = {
            "type": "template",
            "template": {
                "name": node_data.get('selectedTemplateName'),
                "language": {"code": "en"},
                "components": components
            }
        }
        message_type_to_save = 'template'
        text_content_to_save = f"Sent template: {node_data.get('selectedTemplateName')}"

    elif node_type == 'buttonsNode':
        buttons = [{"type": "reply", "reply": {"id": btn.get('text'), "title": btn.get('text')}} for btn in node_data.get('buttons', [])]
        payload = {"type": "interactive", "interactive": {"type": "button", "body": {"text": node_data.get('text')}, "action": {"buttons": buttons}}}
        text_content_to_save = node_data.get('text')
        
    elif node_type == 'interactiveListNode':
        sections_data = []
        for section in node_data.get('sections', []):
            rows_data = [{"id": row.get('id'), "title": row.get('title'), "description": row.get('description', '')} for row in section.get('rows', [])]
            sections_data.append({"title": section.get('title'), "rows": rows_data})

        payload = {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": node_data.get('header', '')},
                "body": {"text": node_data.get('body', '')},
                "footer": {"text": node_data.get('footer', '')},
                "action": {"button": node_data.get('buttonText', 'Select'), "sections": sections_data}
            }
        }
        text_content_to_save = node_data.get('body')
    
    else:
        logger.error(f"Message construction for node type '{node_type}' is not implemented in execute_flow_node.")
        return False

    # Send the message
    success, response_data = send_whatsapp_message(payload)

    if success:
        wamid = response_data['messages'][0]['id']
        save_outgoing_message(
            contact=contact, wamid=wamid, message_type=message_type_to_save, 
            text_content=text_content_to_save, source_node_id=target_node_id
        )
        
        edges = flow.flow_data.get('edges', [])
        target_has_outputs = any(e for e in edges if e.get('source') == target_node_id)
        
        session = UserFlowSession.objects.filter(contact=contact).first()
        if target_has_outputs:
            UserFlowSession.objects.update_or_create(
                contact=contact,
                defaults={'flow': flow, 'current_node_id': target_node_id}
            )
            logger.info(f"Session for {contact.wa_id} set to node '{target_node_id}'")
        elif session:
            session.delete()
            logger.info(f"Flow ended for {contact.wa_id}. Session deleted.")
        return True
    
    # This part is important for debugging
    logger.error(f"Failed to send message via WhatsApp API. Payload: {json.dumps(payload, indent=2)}")
    logger.error(f"Meta API Response: {response_data}")
    return False


def try_execute_flow_step(contact, user_input, replied_to_wamid):
    """
    This function now finds the correct next step and passes it to the
    centralized execute_flow_node function.
    """
    # ... (all of your existing logic to find the flow, current_node, and next_edge)
    # This includes the session check, historical branching, and new flow trigger logic.
    session = UserFlowSession.objects.filter(contact=contact).first()
    flow = session.flow if session else None
    current_node = None
    next_edge = None

    if session:
        nodes = flow.flow_data.get('nodes', [])
        current_node = next((n for n in nodes if n.get('id') == session.current_node_id), None)
        if current_node:
            edges = flow.flow_data.get('edges', [])
            next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)

    if not next_edge:
        try:
            original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound')
            historical_node_id = original_message.source_node_id
            if historical_node_id:
                if not flow:
                    active_flows = Flow.objects.filter(is_active=True)
                    for f in active_flows:
                        if any(n.get('id') == historical_node_id for n in f.flow_data.get('nodes', [])):
                            flow = f
                            break
                if flow:
                    nodes = flow.flow_data.get('nodes', [])
                    current_node = next((n for n in nodes if n.get('id') == historical_node_id), None)
                    if current_node:
                        edges = flow.flow_data.get('edges', [])
                        next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
        except Message.DoesNotExist:
            pass

    if not next_edge:
        try:
            original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
            template_name = original_message.text_content.replace("Sent template: ", "").strip()
            possible_flows = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at')
            if possible_flows.exists():
                flow = possible_flows.first()
                nodes = flow.flow_data.get('nodes', [])
                current_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data', {}).get('selectedTemplateName') == template_name), None)
                if current_node:
                    edges = flow.flow_data.get('edges', [])
                    next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
        except Message.DoesNotExist:
            pass
    
    if not flow or not current_node or not next_edge:
        logger.error(f"Could not determine a valid next step for contact {contact.wa_id} with input '{user_input}'.")
        return False

    nodes = flow.flow_data.get('nodes', [])
    target_node_id = next_edge.get('target')
    target_node = next((n for n in nodes if n.get('id') == target_node_id), None)
    
    if not target_node:
        logger.error(f"Edge points to a non-existent target node ID: '{target_node_id}'")
        return False

    # Once the target_node is found, pass it to the executor.
    return execute_flow_node(contact, flow, target_node)


# Keep all your other existing views (get_whatsapp_templates_api, save_flow_api, etc.)
# @csrf_exempt
# def whatsapp_webhook_view(request):
#     """Handles all incoming WhatsApp events, prioritizing dynamic flows."""
#     # ** NEW LOG 1: Check if the view is being hit at all **
#     logger.info("====== WEBHOOK URL HAS BEEN HIT ======")
    
#     if request.method == 'POST':
#         # ** NEW LOG 2: Check if the request body is being read **
#         logger.info("====== Webhook is a POST request. Attempting to read body. ======")
        
#         data = json.loads(request.body)
#         logger.info(f"====== INCOMING WEBHOOK BODY ======\n{json.dumps(data, indent=2)}")
#         try:
#             for entry in data.get('entry', []):
#                 for change in entry.get('changes', []):
#                     value = change.get('value', {})
#                     if 'messages' in value:
#                         for msg in value.get('messages', []):
#                             # ... (Your message saving logic remains the same) ...
#                             contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
#                             contact.last_contact_at = timezone.now()
#                             contact.save()
#                             message_type = msg.get('type')
#                             # ... (The rest of your code to save the incoming message instance) ...
                            
#                             # --- START: FLOW ENGINE TRIGGER ---
#                             replied_to_wamid = msg.get('context', {}).get('id')
#                             user_input = None
#                             if message_type == 'text':
#                                 user_input = msg.get('text', {}).get('body')

#                             elif message_type == 'button':
#                                 user_input = msg.get('button', {}).get('text')
#                             elif message_type == 'interactive' and msg.get('interactive', {}).get('type') == 'button_reply':
#                                 user_input = msg.get('interactive', {}).get('button_reply', {}).get('title')
                            
#                             logger.info(f"DEBUG-FLOW: Extracted user_input='{user_input}' and replied_to_wamid='{replied_to_wamid}'")
#                             flow_handled = False
#                             if user_input and replied_to_wamid:
#                                 flow_handled = try_execute_flow_step(contact, user_input, replied_to_wamid)
#                             elif user_input:
#                                 logger.info(f"User sent input '{user_input}' without replying to a flow message. No action taken.")
#                                 pass
#                                 # Go to the next message
#                             if flow_handled:
#                                 logger.info("DEBUG-FLOW: Flow was successfully handled. Skipping fallback logic.")
#                                 continue
#                             # --- FALLBACK LOGIC ---
#                             # ... (Your existing hardcoded command logic goes here) ...
#                             # ... (It will run only if flow_handled is False) ...
                            
#                     elif 'statuses' in value:
#                         # ... (Your status update logic) ...
#                         pass
#         except Exception as e:
#             logger.error(f"Error in webhook: {e}", exc_info=True)
#         return JsonResponse({"status": "success"}, status=200)


# contact_app/views.py

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
# def try_execute_flow_step(contact, user_input, replied_to_wamid):
#     """
#     Finds and executes the next step in a flow using a session-based approach.
#     This version only triggers flows marked as active.
#     """
#     try:
#         session = UserFlowSession.objects.filter(contact=contact).first()
#         flow = session.flow if session else None
#         current_node = None
#         next_edge = None

#         # --- Stage 1: Try to find the next step based on the current session ---
#         if session:
#             logger.info(f"Found active session for contact {contact.wa_id} in flow '{flow.name}' at node '{session.current_node_id}'.")
#             nodes = flow.flow_data.get('nodes', [])
#             current_node = next((n for n in nodes if n.get('id') == session.current_node_id), None)
#             if current_node:
#                 edges = flow.flow_data.get('edges', [])
#                 next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)

#         # --- Stage 2: If no path found, try to branch from a historical message ---
#         if not next_edge:
#             logger.warning(f"No valid path from current session. Attempting to branch from historical context of replied message...")
#             try:
#                 original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound')
#                 historical_node_id = original_message.source_node_id

#                 if historical_node_id:
#                     # If we don't know the flow (because the session was deleted), we must find it.
#                     if not flow:
#                         logger.info("No active flow. Searching all active flows for historical node...")
#                         # This is the new, robust fallback logic
#                         active_flows = Flow.objects.filter(is_active=True)
#                         for f in active_flows:
#                             # Check if the historical node exists in this flow's data
#                             if any(n.get('id') == historical_node_id for n in f.flow_data.get('nodes', [])):
#                                 flow = f
#                                 logger.info(f"Found historical node in flow '{flow.name}'.")
#                                 break
                    
#                     if flow:
#                         nodes = flow.flow_data.get('nodes', [])
#                         current_node = next((n for n in nodes if n.get('id') == historical_node_id), None)
#                         if current_node:
#                             edges = flow.flow_data.get('edges', [])
#                             next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
#                             if next_edge:
#                                 logger.info(f"SUCCESS: Found a valid historical path. Branching from node '{historical_node_id}'.")
#             except Message.DoesNotExist:
#                 logger.debug("Replied-to message not found in DB for historical check.")
#                 pass
        
#         # --- Stage 3: If still no path, try to start a brand new flow ---
#         if not next_edge:
#             logger.warning(f"No historical path found. Attempting to start a new flow from a trigger template...")
#             try:
#                 original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
#                 template_name = original_message.text_content.replace("Sent template: ", "").strip()
#                 possible_flows = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at')
                
#                 if possible_flows.exists():
#                     flow = possible_flows.first()
#                     nodes = flow.flow_data.get('nodes', [])
#                     current_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data', {}).get('selectedTemplateName') == template_name), None)
#                     if current_node:
#                         edges = flow.flow_data.get('edges', [])
#                         next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
#                         if next_edge:
#                             logger.info(f"SUCCESS: Starting new session for contact {contact.wa_id} with flow '{flow.name}'")
#             except Message.DoesNotExist:
#                 logger.debug("Replied-to message is not a trigger template.")
#                 pass

#         # --- Stage 4: Final check and execution ---
#         if not flow or not current_node or not next_edge:
#             logger.error(f"After all checks, could not determine a valid next step for contact {contact.wa_id} with input '{user_input}'. Halting execution.")
#             return False

#         nodes = flow.flow_data.get('nodes', [])
#         edges = flow.flow_data.get('edges', [])
#         target_node_id = next_edge.get('target')
#         target_node = next((n for n in nodes if n.get('id') == target_node_id), None)
        
#         if not target_node:
#             logger.error(f"FATAL: Edge points to a non-existent target node ID: '{target_node_id}'")
#             return False
#         # 3. CONSTRUCT AND SEND THE MESSAGE (This part remains the same)
#         node_type = target_node.get('type')
#         node_data = target_node.get('data', {})
#         payload = {"messaging_product": "whatsapp", "to": contact.wa_id}
#         message_type_to_save = 'unknown'
#         text_content_to_save = f"Flow Step: {node_type}"
#         # ... (All your elif blocks for textNode, templateNode, imageNode, buttonsNode are correct and go here) ...
#         if node_type == 'textNode':
#             message_text = node_data.get('text', '...')
#             payload.update({"type": "text", "text": {"body": message_text}})
#             message_type_to_save = 'text'
#             text_content_to_save = message_text
        
#         elif node_type == 'templateNode':
#             target_template_name = node_data.get('selectedTemplateName')
#             if not target_template_name:
#                 logger.error("Flow Error: Target node is a template but no template name is selected.")
#                 return False
#             components = []
#             if 'headerUrl' in node_data and node_data['headerUrl']:
#                 components.append({
#                     "type": "header", "parameters": [{"type": "image", "image": { "link": node_data['headerUrl'] }}]
#                 })
#             body_params = []
#             for i in range(1, 10):
#                 var_key = f'bodyVar{i}'
#                 if var_key in node_data and node_data[var_key]:
#                     body_params.append({ "type": "text", "text": node_data[var_key] })
#                 else:
#                     break
#             if body_params:
#                 components.append({ "type": "body", "parameters": body_params })
#             payload.update({
#                 "type": "template",
#                 "template": {"name": target_template_name, "language": { "code": "en" }, "components": components }
#             })
#             message_type_to_save = 'template'
#             text_content_to_save = f"Sent template: {target_template_name}"
            
#         elif node_type == 'imageNode':
#             meta_media_id = node_data.get('metaMediaId') # We will now store the Meta Media ID
#             caption = node_data.get('caption')
#             if not meta_media_id:
#                 logger.error(f"Flow Error: Image node for contact {contact.wa_id} has no URL.")
#                 return False
#             payload.update({"type": "image", "image": {"id": meta_media_id, "caption": caption}})
#             message_type_to_save = 'image'
#             text_content_to_save = caption or "Sent an image"
            
#         elif node_type == 'buttonsNode':
#             body_text = node_data.get('text')
#             buttons = node_data.get('buttons', [])
#             if not body_text or not buttons:
#                 logger.error(f"Flow Error: Buttons node for contact {contact.wa_id} is missing text or buttons.")
#                 return False
#             action = {"buttons": []}
#             for btn in buttons:
#                 action["buttons"].append({"type": "reply", "reply": {"id": btn.get('text'), "title": btn.get('text')}})
#             payload.update({
#                 "type": "interactive",
#                 "interactive": {"type": "button", "body": { "text": body_text }, "action": action}
#             })
#             message_type_to_save = 'interactive'
#             text_content_to_save = body_text
#         else:
#             return False
            
#         # 4. SEND MESSAGE AND MANAGE SESSION
#         success, response_data = send_whatsapp_message(payload)
        
#         if success:
#             save_outgoing_message(
#                 contact=contact, 
#                 wamid=response_data['messages'][0]['id'], 
#                 message_type=message_type_to_save, 
#                 text_content=text_content_to_save,
#                 source_node_id=target_node_id  # <-- Pass the new ID
#             )
#             # --- MODIFIED LOGIC WITH DEBUG LOGS ---
#             target_has_outputs = any(e for e in edges if e.get('source') == target_node_id)
#             logger.info(f"DEBUG-SESSION: Checking for outputs from target_node_id: '{target_node_id}'. Has outputs: {target_has_outputs}")

#             if target_has_outputs:
#                 UserFlowSession.objects.update_or_create(
#                     contact=contact,
#                     defaults={'flow': flow, 'current_node_id': target_node_id}
#                 )
#                 logger.info(f"Session for {contact.wa_id} updated to node '{target_node_id}'")
#             else:
#                 if session:
#                     session.delete()
#                 logger.info(f"Flow ended for {contact.wa_id} because node has no outputs. Session deleted.")
#             # --- END MODIFIED LOGIC ---
            
#             return True
#         else:
#             logger.error(f"Flow step failed for contact {contact.wa_id}. API Response: {response_data}")
#             return False

#     except Exception as e:
#         logger.error(f"CRITICAL FLOW ERROR: {e}", exc_info=True)
#         return False
r
#            

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

