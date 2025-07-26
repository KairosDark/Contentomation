import json
import logging
import os
from typing import List, Dict
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests  # Added for optional outbound Zapier webhook calls

from ddgs import DDGS
from xai_sdk import Client

# Load environment variables
load_dotenv()

# Get API key from environment variable
GROK_API_KEY = os.getenv('GROK_API_KEY')
if not GROK_API_KEY:
    raise ValueError("GROK_API_KEY environment variable is not set")

# Optional: Zapier webhook URL for outbound calls (no API key needed)
ZAPIER_WEBHOOK_URL = os.getenv('ZAPIER_WEBHOOK_URL')

# Initialize xAI client for Grok integration
client = Client(api_key=GROK_API_KEY)

# Set up logging for production
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Temporary debug route to test server availability (remove after fixing 404)
@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'App is running! Integrate with Zapier via /run_cycle POST.'}), 200

def web_search(query: str, num_results: int = 10) -> List[Dict]:
    """
    Perform web search using DDGS.
    Returns list of dicts with 'title' and 'snippet'.
    """
    logging.info(f"Executing web search for query: {query}")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=num_results)]
        return [{'title': r['title'], 'snippet': r.get('body', r.get('snippet', ''))} for r in results]
    except Exception as e:
        logging.error(f"Web search failed: {str(e)}")
        return []

def grok_process_raw_data(raw_data: List[Dict]) -> Dict:
    """
    Use Grok API to categorize and process raw search data into themes.
    Returns dict of categories.
    """
    if not raw_data:
        return {'productivity': [], 'health': [], 'creativity': []}
    
    prompt = (
        "Categorize the following search results into 'productivity', 'health', 'creativity'. "
        "Filter for uniqueness. Output as JSON: {'productivity': [list of {'title': str, 'snippet': str}], ...} "
        f"Data: {json.dumps(raw_data)}"
    )
    
    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are an efficient categorizer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        categorized = json.loads(response.choices[0].message.content)
        return categorized
    except Exception as e:
        logging.error(f"Grok processing failed: {str(e)}")
        return {'productivity': [], 'health': [], 'creativity': []}

def generate_outputs(categorized: Dict, raw_data: List[Dict], user_profiles: List[Dict] = None) -> Dict:
    """
    Generate outputs for all products, reusing data to optimize.
    Optionally POST to Zapier webhook for further automation.
    """
    outputs = {}
    
    # 1. Newsletter: Curate top 5 hacks
    all_hacks = [h for hacks in categorized.values() for h in hacks]
    outputs['newsletter'] = {'content': [h['snippet'] for h in all_hacks[:5]]}
    
    # 2. Tool Vault: Extract tool mentions
    tools = [h for hacks in categorized.values() for h in hacks if 'tool' in h['snippet'].lower()]
    outputs['tool_vault'] = {'updates': tools}
    
    # 3. Community Forum: Seed topics from raw data
    outputs['forum'] = {'topics': [h['title'] for h in raw_data[:3]]}
    
    # 4. Coaching Bot: Refresh knowledge base with personalization
    bot_knowledge = {k: [h['snippet'] for h in v] for k, v in categorized.items()}
    if user_profiles:
        for profile in user_profiles:
            interest = profile.get('interest')
            if interest in bot_knowledge:
                bot_knowledge[profile['id']] = bot_knowledge[interest]
    outputs['coaching_bot'] = {'knowledge_base': bot_knowledge}
    
    # 5. Workshop Series: Generate session outlines
    outputs['workshops'] = {'sessions': [{'theme': k, 'materials': [h['snippet'] for h in v[:2]]} for k, v in categorized.items()]}
    
    # Optional: Send outputs to Zapier webhook for external automation (e.g., emailing, posting)
    if ZAPIER_WEBHOOK_URL:
        try:
            requests.post(ZAPIER_WEBHOOK_URL, json=outputs)
            logging.info("Outputs sent to Zapier webhook successfully")
        except Exception as e:
            logging.error(f"Failed to send to Zapier: {str(e)}")
    
    return outputs

@app.route('/run_cycle', methods=['POST'])
def run_automation_cycle():
    """
    Endpoint for Zapier/Grok to trigger. Accepts JSON with 'user_profiles' (optional).
    Returns JSON outputs or error.
    """
    try:
        data = request.get_json()
        user_profiles = data.get('user_profiles', [])
        
        raw_data = web_search('latest AI life hacks for productivity health creativity site:reddit.com OR x.com', 10)
        categorized = grok_process_raw_data(raw_data)
        outputs = generate_outputs(categorized, raw_data, user_profiles)
        
        logging.info("Automation cycle completed successfully")
        return jsonify(outputs), 200
    except Exception as e:
        logging.error(f"Error in automation cycle: {str(e)}")
        return jsonify({'error': str(e)}), 500

# For local dev only; in production (e.g., Replit with Gunicorn), this won't run
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=False)