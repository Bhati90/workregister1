

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Helper Functions ---

def get_db_schema():
    """
    Connects to the database and retrieves the CREATE TABLE statements
    for a predefined list of allowed tables.
    """
    # CRITICAL: Define which tables the AI is allowed to see and query.
    # This is your primary security layer.
    # Replace these with the actual table names from your database.
    allowed_tables = ['registration_chatcontact', 'flow_flows', 'registration_message','registration_labourer', 'registration_job','user_profiles'] 
    
    schema_str = ""
    with connection.cursor() as cursor:
        for table_name in allowed_tables:
            # This query fetches the table structure for PostgreSQL
            cursor.execute(f"""
                SELECT 'CREATE TABLE ' || '{table_name}' || ' (' || string_agg(column_name || ' ' || data_type, ', ') || ');'
                FROM information_schema.columns
                WHERE table_name = '{table_name}';
            """)
            row = cursor.fetchone()
            if row and row[0]:
                schema_str += row[0] + "\n\n"
    return schema_str

def generate_sql_from_llm(user_query: str):
    """
    Generates a secure, read-only SQL query from a natural language prompt using the Gemini API.
    """
    db_schema = get_db_schema()
    if not db_schema:
        return "-- Failed to retrieve database schema.", []

    # --- UPDATED MODEL NAME AND CONFIGURATION ---
    # Use a modern, fast model and configure it to expect JSON output.
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    json_output_config = {
        "response_mime_type": "application/json",
    }
    # --- END OF UPDATE ---

    prompt = f"""
    You are a PostgreSQL expert data analyst. Your task is to convert a user's question into a valid, performant, and secure PostgreSQL query and identify which tables were used.

    Here is the database schema you must use:
    {db_schema}

    here is the breack down of the database schema & the discription & the meaning of the db_schema 

    

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
        
        # The response text should now be a JSON string
        result_json = json.loads(response.text)
        
        sql_query = result_json.get("sql_query", "-- Failed to generate SQL.")
        used_tables = result_json.get("used_tables", [])
        
        return sql_query, used_tables

    except Exception as e:
        print(f"An error occurred with the Gemini API call: {e}")
        return f"-- An error occurred: {e}", []


# --- API Views ---

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
