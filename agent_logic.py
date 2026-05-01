import os
import time
from google import genai
from gmail_setup import get_gmail_service
from twilio.rest import Client as TwilioClient

# 1. AI Configuration
API_KEY = "AIzaSyBe_WFpMqUfip3kDOxopgRXYDRD2n8VJ2w"
client = genai.Client(api_key=API_KEY)

# 2. Twilio Configuration
TWILIO_SID = "AC8185c049ff80ff609247327509736070"
TWILIO_TOKEN = "fa13f23cc14bb9df082c8c836b08d1d7"
FROM_WHATSAPP = "whatsapp:+14155238886" 
TO_WHATSAPP = "whatsapp:+919167834030" 

def process_with_ai(email):
    """AI Classification Logic using Gemini 2.5/3 standards."""
    try:
        # Streamlined prompt for database categorization
        prompt = f"Analyze: {email['subject']}. Content: {email['snippet']}. Return ONLY one label: URGENT, LEGAL, or NORMAL."
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        return response.text.strip().upper()
    except Exception as e:
        print(f"AI Error: {e}")
        return "NORMAL"

def send_whatsapp_alert(subject, category):
    """WhatsApp Alert via Twilio for critical emails."""
    try:
        tw_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        tw_client.messages.create(
            body=f"🚨 *AI ALERT*: Important {category} email found!\n\nSubject: {subject}\n\nCheck your new custom dashboard for details.",
            from_=FROM_WHATSAPP, 
            to=TO_WHATSAPP
        )
        print(f"✅ WhatsApp alert sent for: {subject}")
    except Exception as e:
        print(f"❌ Twilio Error: {e}")

def sync_emails_to_db(db, EmailModel, deep_scan=False):
    """
    Core logic to fetch from Gmail, process with AI, and save to SQLite.
    If deep_scan is True, it scans up to 100 messages including read ones.
    """
    try:
        service = get_gmail_service()
        
        # LOGIC UPDATE:
        # If deep_scan is False: only look for unread messages (limit 20)
        # If deep_scan is True: look at all mail types (limit 100)
        search_query = "" if deep_scan else "is:unread"
        limit = 100 if deep_scan else 20
        
        print(f"--- Starting {'Deep' if deep_scan else 'Quick'} Sync (Limit: {limit}) ---")
        
        results = service.users().messages().list(
            userId='me', 
            q=search_query, 
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])

        for msg in messages:
            # Check if this email is already processed and saved in our DB
            if EmailModel.query.filter_by(gmail_id=msg['id']).first():
                continue

            # Fetch full email details
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            snippet = txt.get('snippet', '')
            is_unread = 'UNREAD' in txt.get('labelIds', [])

            # Get AI categorization
            category = process_with_ai({"subject": subject, "snippet": snippet})

            # Save to Database
            new_email = EmailModel(
                gmail_id=msg['id'],
                subject=subject,
                sender=sender,
                snippet=snippet,
                category=category,
                is_unread=is_unread
            )
            db.session.add(new_email)
            db.session.commit()
            print(f"Stored: {subject} as {category}")

            # Trigger WhatsApp Alert ONLY for unread critical messages
            # We don't want to alert for old read emails found during deep scan
            if is_unread and (category == "URGENT" or category == "LEGAL"):
                send_whatsapp_alert(subject, category)
                
    except Exception as e:
        print(f"Sync Error: {e}")