# # Contentomation

This Flask app automates content generation using Grok (via xAI SDK) and integrates with Zapier via webhooks for external automation (e.g., emailing, posting). No Zapier API key needed—use inbound/outbound webhooks.

## Setup on Replit
1. Upload all files: main.py, .env (with your keys), requirements.txt, .replit, Procfile.
2. Install deps: `pip install -r requirements.txt` in shell.
3. Run the app: Click "Run" (uses Gunicorn for production).
4. Test endpoint: POST to /run_cycle with JSON (e.g., via curl or Zapier).
5. Zapier Integration: Create Zaps to trigger /run_cycle or receive POSTs from the app.

## Environment Variables (.env)
- GROK_API_KEY: Required for Grok.
- ZAPIER_WEBHOOK_URL: Optional for sending outputs to Zapier.

## Debugging
- Visit / for a status check.
- Logs in Replit console.

For Grok cohesion: The script uses Grok for categorization; extend with custom Grok projects/tasks via SDK.