import logging
import json
import requests
from celery import shared_task
from .models import ChatContact, Flows, Attribute, ContactAttributeValue, UserFlowSessions
from .utils import substitute_variables, extract_json_path # <-- IMPORT FROM UTILS

logger = logging.getLogger(__name__)

# This task now needs access to the main execute function to continue the flow.
# To prevent circular imports, we import it *inside* the function where it's needed.
def _get_execute_flow_node_func():
    from .views import execute_flow_node
    return execute_flow_node

@shared_task
def process_api_request_node(contact_id, flow_id, target_node):
    """
    A Celery task to make an API request asynchronously and then trigger the next node.
    """
    try:
        contact = ChatContact.objects.get(id=contact_id)
        flow = Flows.objects.get(id=flow_id)
    except (ChatContact.DoesNotExist, Flows.DoesNotExist) as e:
        logger.error(f"Could not find contact or flow for API task: {e}")
        return

    target_node_id = target_node.get('id')
    node_data = target_node.get('data', {})
    
    # 1. Substitute variables using the helper from utils.py
    api_url = substitute_variables(node_data.get('apiUrl'), contact)
    headers = substitute_variables(node_data.get('headers', '{}'), contact)
    body = substitute_variables(node_data.get('requestBody', '{}'), contact)
    
    logger.info(f"Executing API Node Task for Contact {contact_id} to URL: {api_url}")
    logger.debug(f"Request Body after substitution: {body}")

    # 2. Make the request
    request_config = {'method': node_data.get('method', 'GET').upper(), 'url': api_url, 'timeout': 25}
    try:
        request_config['headers'] = json.loads(headers) if headers else {}
        if request_config['method'] != 'GET' and body:
            # Use data= for form data, json= for json payload
            if request_config['headers'].get('Content-Type') == 'application/json':
                 request_config['json'] = json.loads(body)
            else:
                 request_config['data'] = body
    except json.JSONDecodeError:
        logger.error("Invalid JSON in headers or body for API request task.")
    
    api_success = False
    status_code = 0
    try:
        response = requests.request(**request_config)
        status_code = response.status_code
        response_data = response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
        api_success = 200 <= status_code < 300
    except requests.exceptions.RequestException as e:
        logger.error(f"API request task failed for {api_url}: {e}")
        response_data = {"error": str(e)}

    # 3. Process the response (same as before)
    status_code_attr_id = node_data.get('statusCodeAttributeId')
    if status_code_attr_id:
        try:
            attr = Attribute.objects.get(id=status_code_attr_id)
            ContactAttributeValue.objects.update_or_create(contact=contact, attribute=attr, defaults={'value': str(status_code)})
        except Attribute.DoesNotExist:
            logger.warning(f"Status code attribute ID {status_code_attr_id} not found.")

    response_mappings = node_data.get('responseMappings', [])
    if api_success and response_mappings and isinstance(response_data, (dict, list)):
        for mapping in response_mappings:
            json_path, attribute_id = mapping.get('jsonPath'), mapping.get('attributeId')
            if not json_path or not attribute_id: continue
            try:
                value = extract_json_path(response_data, json_path)
                if value is not None:
                    attr = Attribute.objects.get(id=attribute_id)
                    ContactAttributeValue.objects.update_or_create(contact=contact, attribute=attr, defaults={'value': str(value)})
            except Attribute.DoesNotExist:
                logger.error(f"Attribute ID {attribute_id} not found in mapping")

    # 4. Find and execute the next node in the flow
    edges = flow.flow_data.get('edges', [])
    next_handle = 'onSuccess' if api_success else 'onError'
    next_edge = next((e for e in edges if e.get('source') == target_node_id and e.get('sourceHandle') == next_handle), None)
    
    if next_edge:
        next_node = next((n for n in flow.flow_data.get('nodes', []) if n.get('id') == next_edge.get('target')), None)
        if next_node:
            # Get the execution function and call it for the next node
            execute_flow_node = _get_execute_flow_node_func()
            execute_flow_node(contact, flow, next_node)
    else:
        # If there's no next node, end the session
        UserFlowSessions.objects.filter(contact=contact).delete()

