import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from datetime import datetime, timedelta

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Helper Functions ---

def get_db_schema():
    """
    Connects to the database and retrieves the CREATE TABLE statements
    for a predefined list of allowed tables.
    """
    allowed_tables = ['registration_chatcontact','registration_farmer','registration_cropdetails',
                      'registration_intervention', 'flow_flows', 'registration_message',
                      'registration_labourer', 'registration_job','user_profiles'] 
    
    schema_str = ""
    with connection.cursor() as cursor:
        for table_name in allowed_tables:
            cursor.execute(f"""
                SELECT 'CREATE TABLE ' || '{table_name}' || ' (' || string_agg(column_name || ' ' || data_type, ', ') || ');'
                FROM information_schema.columns
                WHERE table_name = '{table_name}';
            """)
            row = cursor.fetchone()
            if row and row[0]:
                schema_str += row[0] + "\n\n"
    return schema_str


def get_comprehensive_farmer_data():
    """
    Retrieves comprehensive farmer data for analysis including crops, 
    interventions, messages, and engagement patterns.
    """
    with connection.cursor() as cursor:
        # Get farmer demographics and crop details
        cursor.execute("""
            SELECT 
                f.id as farmer_id,
                f.name,
                f.phone_number,
                f.location,
                f.farm_size,
                f.created_at,
                f.last_active,
                COUNT(DISTINCT cd.id) as total_crops,
                STRING_AGG(DISTINCT cd.crop_name, ', ') as crops_grown,
                COUNT(DISTINCT i.id) as total_interventions,
                COUNT(DISTINCT m.id) as total_messages,
                MAX(m.created_at) as last_message_date
            FROM registration_farmer f
            LEFT JOIN registration_cropdetails cd ON f.id = cd.farmer_id
            LEFT JOIN registration_intervention i ON f.id = i.farmer_id
            LEFT JOIN registration_message m ON f.phone_number = m.phone_number
            GROUP BY f.id, f.name, f.phone_number, f.location, f.farm_size, f.created_at, f.last_active
        """)
        
        columns = [col[0] for col in cursor.description]
        farmer_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Get crop-specific details
        cursor.execute("""
            SELECT 
                farmer_id,
                crop_name,
                crop_variety,
                planting_date,
                expected_harvest_date,
                area_planted,
                growth_stage
            FROM registration_cropdetails
        """)
        columns = [col[0] for col in cursor.description]
        crop_details = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Get intervention history
        cursor.execute("""
            SELECT 
                farmer_id,
                intervention_type,
                intervention_date,
                status,
                outcome
            FROM registration_intervention
            ORDER BY intervention_date DESC
        """)
        columns = [col[0] for col in cursor.description]
        interventions = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return {
            'farmers': farmer_data,
            'crop_details': crop_details,
            'interventions': interventions
        }


def analyze_farmer_segments_with_ai(farmer_data):
    """
    Uses AI to automatically analyze farmer data and create actionable segments
    with specific flow recommendations.
    """
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
You are an expert agricultural business analyst for a FARMER-LABOR PLATFORM. Analyze the farmer data below and create actionable customer segments with specific WhatsApp flow recommendations.

FARMER DATA:
{json.dumps(farmer_data, indent=2, default=str)}

YOUR TASK:
1. Identify different farmer segments based on:
   - Engagement level (active, inactive, dormant)
   - Crop types and diversity
   - Farm size and scale
   - Intervention history
   - Communication patterns
   - Conversion potential (likelihood to become paying customer)

2. For EACH segment, provide:
   - Segment name and description
   - Size (number of farmers)
   - Key characteristics
   - Business opportunity (revenue potential)
   - Recommended WhatsApp flow strategy
   - Specific message templates needed
   - Best time to contact
   - Success metrics

3. Prioritize segments by:
   - Conversion potential (high/medium/low)
   - Revenue impact
   - Ease of implementation

OUTPUT FORMAT (JSON):
{{
  "analysis_summary": {{
    "total_farmers": number,
    "analysis_date": "current date",
    "key_insights": ["insight1", "insight2", "insight3"]
  }},
  "segments": [
    {{
      "segment_id": "unique_id",
      "segment_name": "Descriptive Name",
      "priority": "HIGH/MEDIUM/LOW",
      "farmer_count": number,
      "conversion_potential": "HIGH/MEDIUM/LOW",
      "estimated_revenue": "₹X,XXX per farmer/month",
      "characteristics": [
        "characteristic1",
        "characteristic2"
      ],
      "farmer_ids": [list of farmer IDs in this segment],
      "recommended_actions": [
        {{
          "action_type": "flow/template/campaign",
          "action_name": "Specific action",
          "timing": "immediate/weekly/monthly",
          "expected_outcome": "what you'll achieve"
        }}
      ],
      "whatsapp_flow_strategy": {{
        "flow_type": "onboarding/retention/upsell/reactivation",
        "flow_name": "Suggested flow name",
        "trigger": "What triggers this flow",
        "steps": [
          {{
            "step_number": 1,
            "template_type": "greeting/offer/survey/reminder",
            "message_intent": "What this message achieves",
            "sample_text_hindi": "Sample message in Hindi",
            "sample_text_english": "Sample message in English",
            "buttons": ["Button 1", "Button 2"],
            "expected_response": "What farmer should do"
          }}
        ],
        "success_metrics": ["metric1", "metric2"]
      }},
      "contact_strategy": {{
        "best_time": "morning/afternoon/evening",
        "frequency": "daily/weekly/monthly",
        "channel_preference": "whatsapp/sms/call"
      }}
    }}
  ],
  "immediate_opportunities": [
    {{
      "opportunity": "Description",
      "target_segment": "segment_id",
      "potential_revenue": "₹X,XXX",
      "implementation_difficulty": "easy/medium/hard",
      "action_items": ["step1", "step2"]
    }}
  ],
  "automation_recommendations": [
    {{
      "automation_type": "Type of automation",
      "description": "What it does",
      "target_segments": ["segment1", "segment2"],
      "implementation_priority": "HIGH/MEDIUM/LOW"
    }}
  ]
}}

Make it actionable, specific, and focused on CONVERSION and REVENUE.
Generate ONLY valid JSON.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return None


def generate_flow_prompts_from_segments(segments_data):
    """
    Converts AI segment analysis into ready-to-use flow creation prompts.
    """
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
Based on the farmer segment analysis, generate specific, ready-to-execute prompts for creating WhatsApp flows.

SEGMENT ANALYSIS:
{json.dumps(segments_data, indent=2)}

Generate detailed prompts that can be directly used to create flows. Each prompt should be complete and actionable.

OUTPUT FORMAT (JSON):
{{
  "flow_prompts": [
    {{
      "prompt_id": "unique_id",
      "segment_targeted": "segment name",
      "priority": "HIGH/MEDIUM/LOW",
      "prompt_title": "Short title",
      "full_prompt": "Complete prompt ready to paste for flow creation",
      "expected_templates": number,
      "language": "hi/en/both",
      "estimated_conversion_rate": "X%",
      "implementation_notes": ["note1", "note2"]
    }}
  ]
}}

Generate ONLY valid JSON.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating flow prompts: {e}")
        return None


# --- API Views ---

@csrf_exempt
def auto_analyze_farmers_view(request):
    """
    Automatically analyzes all farmer data and provides actionable insights
    with recommended flows and conversion strategies.
    """
    if request.method == 'POST':
        try:
            # Get comprehensive farmer data
            farmer_data = get_comprehensive_farmer_data()
            
            if not farmer_data['farmers']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No farmer data found in database'
                }, status=404)
            
            # Perform AI analysis
            analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            
            if not analysis_result:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to analyze farmer data'
                }, status=500)
            
            # Generate ready-to-use flow prompts
            flow_prompts = generate_flow_prompts_from_segments(analysis_result)
            
            return JsonResponse({
                'status': 'success',
                'analysis': analysis_result,
                'flow_prompts': flow_prompts,
                'raw_data_summary': {
                    'total_farmers': len(farmer_data['farmers']),
                    'total_crops': len(farmer_data['crop_details']),
                    'total_interventions': len(farmer_data['interventions'])
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"Analysis failed: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def get_segment_details_view(request):
    """
    Get detailed information about a specific farmer segment.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            segment_id = data.get('segment_id')
            
            if not segment_id:
                return JsonResponse({'error': 'Segment ID not provided'}, status=400)
            
            # Get full analysis
            farmer_data = get_comprehensive_farmer_data()
            analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            
            # Find specific segment
            target_segment = None
            for segment in analysis_result.get('segments', []):
                if segment['segment_id'] == segment_id:
                    target_segment = segment
                    break
            
            if not target_segment:
                return JsonResponse({'error': 'Segment not found'}, status=404)
            
            # Get farmer details for this segment
            farmer_ids = target_segment.get('farmer_ids', [])
            farmers_in_segment = [
                f for f in farmer_data['farmers'] 
                if f['farmer_id'] in farmer_ids
            ]
            
            return JsonResponse({
                'status': 'success',
                'segment': target_segment,
                'farmers': farmers_in_segment,
                'total_farmers': len(farmers_in_segment)
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def generate_query_view(request):
    """
    API View to generate an SQL query from a natural language request.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            if not query:
                return JsonResponse({'error': 'Query not provided'}, status=400)

            sql_query, used_tables = generate_sql_from_llm(query)

            # Security Check: Ensure the generated query is safe
            if not sql_query.strip().upper().startswith('SELECT'):
                return JsonResponse({'error': 'Generated query is not a SELECT statement. Aborting.'}, status=400)

            return JsonResponse({
                'sql_query': sql_query,
                'used_tables': used_tables,
                'full_schema': get_db_schema()
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def execute_query_view(request):
    """
    API View to execute a SQL query (either as a test or full run).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sql_query = data.get('sql_query')
            test_run = data.get('test_run', False)

            if not sql_query:
                return JsonResponse({'error': 'SQL query not provided'}, status=400)

            # Security Check: Double-check that it's a safe query
            if not sql_query.strip().upper().startswith('SELECT'):
                return JsonResponse({'error': 'Only SELECT statements can be executed.'}, status=403)

            final_query = sql_query
            if test_run:
                # Add a LIMIT clause for the test run
                final_query = f"{sql_query.rstrip(';')} LIMIT 100;"

            with connection.cursor() as cursor:
                cursor.execute(final_query)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Suggest a chart type based on the results
            chart_type = 'table'
            if len(results) > 0:
                first_row = results[0]
                if len(first_row.keys()) == 2:
                    key1, key2 = list(first_row.keys())
                    # If one column is text-like and the other is numeric, suggest bar or pie
                    if isinstance(first_row[key1], str) and isinstance(first_row[key2], (int, float)):
                        chart_type = 'bar' if len(results) > 5 else 'pie'

            return JsonResponse({'results': results, 'chart_type': chart_type})
        except Exception as e:
            return JsonResponse({'error': f"Database query failed: {e}"}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def generate_sql_from_llm(user_query: str):
    """
    Generates a secure, read-only SQL query from a natural language prompt using the Gemini API.
    """
    db_schema = get_db_schema()
    if not db_schema:
        return "-- Failed to retrieve database schema.", []

    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    json_output_config = {
        "response_mime_type": "application/json",
    }

    prompt = f"""
    You are a PostgreSQL expert data analyst. Your task is to convert a user's question into a valid, performant, and secure PostgreSQL query and identify which tables were used.

    Here is the database schema you must use:
    {db_schema}

    Analyze the user's question and the schema to construct a read-only SQL query.

    Rules:
    1.  CRITICAL: Only generate `SELECT` statements. Never generate `INSERT`, `UPDATE`, `DELETE`, `DROP`, `GRANT`, or any other data-modifying statements.
    2.  Only use tables and columns present in the provided schema.
    3.  If a table name includes a prefix (like 'registration_'), you must include it in the query.
    4.  Return the result as a JSON object with two keys: "sql_query" which contains the generated SQL string, and "used_tables" which is a list of the table names you used in the query.
    5. MOST IMPORTANT CRITICAL: If the user's question cannot be answered with the provided schema, return a JSON object with "sql_query" set to "-- Unable to generate a valid SQL query with the provided schema." and "used_tables" as an empty list.
    
    User Question: "{user_query}"

    JSON Response:
    """
    
    try:
        response = model.generate_content(prompt, generation_config=json_output_config)
        print(response.text)
        
        result_json = json.loads(response.text)
        sql_query = result_json.get("sql_query", "-- Failed to generate SQL.")
        used_tables = result_json.get("used_tables", [])
        
        return sql_query, used_tables

    except Exception as e:
        print(f"An error occurred with the Gemini API call: {e}")
        return f"-- An error occurred: {e}", []