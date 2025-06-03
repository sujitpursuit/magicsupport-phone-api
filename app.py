# Backend API Only (api.py) - Clean version for deployment

from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS - Update this for production with your specific domains
CORS(app, origins=[
    "http://localhost:3000",  # React dev server
    "http://localhost:8080",  # Vue dev server
    "https://app-magicsuppport-ui-dev-gbg5g3hvcudzgugb.centralindia-01.azurewebsites.net"

    # Add more domains as needed
])

# =============================================================================
# CONFIGURATION - Set these as environment variables
# =============================================================================

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_API_KEY = os.getenv('TWILIO_API_KEY')
TWILIO_API_SECRET = os.getenv('TWILIO_API_SECRET')
TWILIO_APP_SID = os.getenv('TWILIO_APP_SID')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Fixed number to call - configure this for your use case
FIXED_CALL_NUMBER = os.getenv('FIXED_CALL_NUMBER', '+18009359935')

# Validate required environment variables
required_vars = [
    'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_API_KEY', 
    'TWILIO_API_SECRET', 'TWILIO_APP_SID', 'TWILIO_PHONE_NUMBER'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {missing_vars}")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Twilio Calling API',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/calling/token', methods=['POST'])
def generate_access_token():
    """
    Generate Twilio access token for browser client
    
    Request Body (JSON):
    {
        "identity": "optional_user_identifier"
    }
    
    Response:
    {
        "success": true,
        "token": "jwt_token_string",
        "identity": "user_identity",
        "expires_in": 3600
    }
    """
    try:
        data = request.get_json() or {}
        
        # Generate unique identity for this calling session
        user_identity = data.get('identity', f"caller_{int(datetime.now().timestamp())}")
        
        logger.info(f"Generating token for identity: {user_identity}")
        
        # Create access token
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=user_identity,
            ttl=3600  # Token valid for 1 hour
        )
        
        # Add voice grant for outgoing calls only
        voice_grant = VoiceGrant(
            outgoing_application_sid=TWILIO_APP_SID,
            incoming_allow=False  # Disable incoming calls for simplicity
        )
        token.add_grant(voice_grant)
        
        return jsonify({
            'success': True,
            'token': token.to_jwt(),
            'identity': user_identity,
            'expires_in': 3600
        })
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate access token'
        }), 500

@app.route('/api/calling/voice', methods=['POST'])
def handle_voice_webhook():
    """
    Twilio voice webhook - handles all outgoing calls
    Routes all calls to the fixed number configured in FIXED_CALL_NUMBER
    
    This endpoint is called by Twilio when a call is initiated from the browser
    """
    try:
        # Get caller information
        caller_identity = request.form.get('From', 'Unknown')
        call_sid = request.form.get('CallSid', 'Unknown')
        
        logger.info(f"Voice webhook - Call SID: {call_sid}, From: {caller_identity}")
        logger.info(f"Routing call to fixed number: {FIXED_CALL_NUMBER}")
        
        # Create TwiML response to dial the fixed number
        response = VoiceResponse()
        
        # Dial the fixed number
        dial = response.dial(
            caller_id=TWILIO_PHONE_NUMBER,
            timeout=30,
            action='/api/calling/call-status',
            method='POST'
        )
        dial.number(FIXED_CALL_NUMBER)
        
        logger.info(f"Generated TwiML for call {call_sid}")
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Voice webhook error: {e}")
        
        # Return error TwiML
        response = VoiceResponse()
        response.say("Sorry, there was an error connecting your call. Please try again later.")
        
        return str(response), 500, {'Content-Type': 'text/xml'}

@app.route('/api/calling/call-status', methods=['POST'])
def handle_call_status():
    """
    Handle call status updates from Twilio
    Called when call status changes (completed, failed, etc.)
    """
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')
        call_duration = request.form.get('CallDuration', '0')
        from_number = request.form.get('From')
        to_number = request.form.get('To')
        
        logger.info(f"Call status update - SID: {call_sid}, Status: {call_status}, Duration: {call_duration}s")
        
        # You can add database logging, analytics, notifications here
        # Example: store_call_log(call_sid, call_status, call_duration, from_number, to_number)
        
        return '', 200
        
    except Exception as e:
        logger.error(f"Call status webhook error: {e}")
        return '', 500

@app.route('/api/calling/config', methods=['GET'])
def get_calling_config():
    """
    Get calling configuration for frontend
    Returns configuration that frontend can use to display information
    """
    return jsonify({
        'success': True,
        'config': {
            'fixed_number': FIXED_CALL_NUMBER,
            'display_number': FIXED_CALL_NUMBER,  # Format this for display if needed
            'service_name': 'Customer Service',    # Customize this
            'features': {
                'outgoing_calls': True,
                'incoming_calls': False,
                'call_recording': False,  # Set to True if you want to enable recording
                'mute': True,
                'hold': False
            },
            'limits': {
                'max_call_duration': 1800,  # 30 minutes
                'concurrent_calls': 1
            }
        }
    })

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested API endpoint does not exist'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

if __name__ == '__main__':
    print("🚀 TWILIO CALLING API - Backend Only")
    print("=" * 50)
    print("📡 Starting API server...")
    print(f"📞 Fixed calling number: {FIXED_CALL_NUMBER}")
    print("\n📋 Available endpoints:")
    print("   GET  /api/health                  - Health check")
    print("   POST /api/calling/token           - Generate access token")
    print("   POST /api/calling/voice           - Voice webhook (for Twilio)")
    print("   POST /api/calling/call-status     - Call status webhook (for Twilio)")
    print("   GET  /api/calling/config          - Get calling configuration")
    print("\n🔑 Required environment variables:")
    for var in required_vars:
        status = "✅ SET" if os.getenv(var) else "❌ MISSING"
        print(f"   {var}: {status}")
    print(f"\n🌐 Server starting on port 5000...")
    
    # Use different configs for development vs production
    if os.getenv('FLASK_ENV') == 'production':
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)

# =============================================================================
# FRONTEND INTEGRATION DOCUMENTATION
# =============================================================================

"""
📖 FRONTEND INTEGRATION GUIDE

Your frontend developer needs to implement:

1. GET ACCESS TOKEN:
   POST /api/calling/token
   Body: {"identity": "user123"}
   Response: {"success": true, "token": "jwt_token", "identity": "user123"}

2. INITIALIZE TWILIO DEVICE:
   // Load Twilio SDK
   <script src="https://sdk.twilio.com/js/client/releases/1.14.0/twilio.min.js"></script>
   
   // Initialize device
   const device = new Twilio.Device(token);
   
   device.on('ready', () => {
       // Enable call button
   });

3. MAKE CALL:
   // Simple call - will automatically route to fixed number
   const call = device.connect();
   
   call.on('connect', () => {
       // Call connected - show hang up button
   });
   
   call.on('disconnect', () => {
       // Call ended - reset UI
   });

4. HANG UP:
   call.disconnect();

EXAMPLE FRONTEND CODE:
```javascript
class CallingService {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.device = null;
        this.currentCall = null;
    }
    
    async initialize() {
        // Get token
        const response = await fetch(`${this.apiBaseUrl}/api/calling/token`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({identity: 'user123'})
        });
        
        const data = await response.json();
        
        // Initialize device
        this.device = new Twilio.Device(data.token);
        
        return new Promise((resolve) => {
            this.device.on('ready', resolve);
        });
    }
    
    makeCall() {
        this.currentCall = this.device.connect();
        return this.currentCall;
    }
    
    hangUp() {
        if (this.currentCall) {
            this.currentCall.disconnect();
        }
    }
}
```

DEPLOYMENT NOTES:
- Deploy this API to Heroku/AWS/Azure/DigitalOcean
- Set all environment variables
- Update TwiML App Voice URL to: https://your-api-domain.com/api/calling/voice
- Configure CORS for your frontend domain
- The fixed number is set via FIXED_CALL_NUMBER environment variable
"""