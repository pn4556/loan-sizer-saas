"""
Email Processing API Endpoints
Handles incoming forwarded emails via webhooks from SendGrid/Mailgun/SES
"""

import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Client, User, LoanApplication as LoanApplicationModel, EmailProcessingLog, ExcelTemplate
from auth import get_current_user
from email_processor import EmailForwardProcessor, ForwardedEmail

# Router
router = APIRouter(prefix="/email", tags=["Email Processing"])

# Initialize processor (lazy loading)
email_processor = None

def get_email_processor():
    global email_processor
    if email_processor is None:
        email_processor = EmailForwardProcessor()
    return email_processor


class IncomingEmailWebhook(BaseModel):
    """Generic incoming email webhook format"""
    to_email: str  # The receiving address (e.g., client123@process.loansizer.com)
    from_email: str  # Forwarder's email
    from_name: Optional[str] = None
    subject: str
    body_text: str
    body_html: Optional[str] = None
    attachments: Optional[list] = []
    headers: Optional[dict] = {}


class EmailProcessingResponse(BaseModel):
    """Response after processing"""
    success: bool
    message: str
    application_id: Optional[int] = None
    decision: Optional[str] = None
    processing_time_ms: Optional[int] = None
    email_sent: bool = False


@router.post("/webhook/sendgrid", response_model=EmailProcessingResponse)
async def sendgrid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive forwarded emails from SendGrid Inbound Parse
    Docs: https://docs.sendgrid.com/for-developers/parsing-email/setting-up-the-inbound-parse-webhook
    """
    try:
        # Parse multipart form data from SendGrid
        form_data = await request.form()
        
        # Extract email data
        to_email = form_data.get('to', '')
        from_email = form_data.get('from', '')
        subject = form_data.get('subject', '')
        body_text = form_data.get('text', '')
        
        # Process attachments
        attachments = []
        num_attachments = int(form_data.get('attachments', 0))
        
        for i in range(1, num_attachments + 1):
            attachment_key = f'attachment-{i}'
            if attachment_key in form_data:
                file_data = form_data[attachment_key]
                attachments.append({
                    'filename': file_data.filename,
                    'content_type': file_data.content_type,
                    'content': await file_data.read()
                })
        
        # Process the email
        result = await process_incoming_email(
            to_email=to_email,
            from_email=from_email,
            from_name=from_email,  # Parse from headers if available
            subject=subject,
            body=body_text,
            attachments=attachments,
            db=db
        )
        
        return EmailProcessingResponse(**result)
        
    except Exception as e:
        return EmailProcessingResponse(
            success=False,
            message=f"Error processing email: {str(e)}"
        )


@router.post("/webhook/mailgun", response_model=EmailProcessingResponse)
async def mailgun_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive forwarded emails from Mailgun Routes
    Docs: https://documentation.mailgun.com/docs/inbound-webhooks
    """
    try:
        form_data = await request.form()
        
        to_email = form_data.get('recipient', '')
        from_email = form_data.get('sender', '')
        from_name = form_data.get('from', '').split('<')[0].strip()
        subject = form_data.get('subject', '')
        body_text = form_data.get('body-plain', '')
        
        # Process Mailgun attachments
        attachments = []
        attachment_count = int(form_data.get('attachment-count', 0))
        
        for i in range(1, attachment_count + 1):
            attachment_data = form_data.get(f'attachment-{i}')
            if attachment_data:
                attachments.append({
                    'filename': attachment_data.filename,
                    'content_type': attachment_data.content_type,
                    'content': await attachment_data.read()
                })
        
        result = await process_incoming_email(
            to_email=to_email,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body=body_text,
            attachments=attachments,
            db=db
        )
        
        return EmailProcessingResponse(**result)
        
    except Exception as e:
        return EmailProcessingResponse(
            success=False,
            message=f"Error processing email: {str(e)}"
        )


@router.post("/webhook/generic", response_model=EmailProcessingResponse)
async def generic_webhook(
    email_data: IncomingEmailWebhook,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generic webhook for any email service
    Accepts structured JSON payload
    """
    try:
        attachments = []
        for att in email_data.attachments or []:
            content = att.get('content')
            if isinstance(content, str):
                content = base64.b64decode(content)
            attachments.append({
                'filename': att.get('filename', 'attachment'),
                'content_type': att.get('content_type', 'application/octet-stream'),
                'content': content
            })
        
        result = await process_incoming_email(
            to_email=email_data.to_email,
            from_email=email_data.from_email,
            from_name=email_data.from_name or email_data.from_email,
            subject=email_data.subject,
            body=email_data.body_text,
            attachments=attachments,
            db=db
        )
        
        return EmailProcessingResponse(**result)
        
    except Exception as e:
        return EmailProcessingResponse(
            success=False,
            message=f"Error processing email: {str(e)}"
        )


async def process_incoming_email(
    to_email: str,
    from_email: str,
    from_name: str,
    subject: str,
    body: str,
    attachments: list,
    db: Session
) -> dict:
    """
    Core email processing logic:
    1. Identify client from receiving email address
    2. Parse forwarded email
    3. Extract data from body + attachments
    4. Run sizer
    5. Send results back
    6. Log everything
    """
    import time
    start_time = time.time()
    
    # Step 1: Identify client from email address
    # Format: client-slug@process.loansizer.com OR client-id@process.loansizer.com
    client = await identify_client_from_email(to_email, db)
    
    if not client:
        return {
            'success': False,
            'message': f'Unknown recipient: {to_email}. Please check your forwarding address.',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
    
    # Step 2: Find the user (forwarder)
    forwarder = db.query(User).filter(
        User.email == from_email,
        User.client_id == client.id
    ).first()
    
    if not forwarder:
        # Create a processing log for unknown forwarder
        log = EmailProcessingLog(
            client_id=client.id,
            forwarder_email=from_email,
            to_email=to_email,
            subject=subject,
            status='rejected',
            error_message='Forwarder not authorized for this client'
        )
        db.add(log)
        db.commit()
        
        return {
            'success': False,
            'message': 'Email not from authorized user for this client',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
    
    # Get client's default template
    default_template = db.query(ExcelTemplate).filter(
        ExcelTemplate.client_id == client.id,
        ExcelTemplate.is_default == True
    ).first()
    
    if not default_template:
        # Try any template for this client
        default_template = db.query(ExcelTemplate).filter(
            ExcelTemplate.client_id == client.id
        ).first()
    
    if not default_template:
        return {
            'success': False,
            'message': 'No Excel template configured. Please upload a template first.',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
    
    # Get email processor with template
    processor = EmailForwardProcessor(template_path=default_template.file_path)
    
    # Step 3: Parse the forwarded email
    forwarded = processor.parse_forwarded_email(
        raw_email_content=body,
        forwarder_email=from_email,
        forwarder_name=from_name,
        attachments=attachments
    )
    forwarded.client_id = client.id
    
    # Step 4: Process the application
    result = processor.process_forwarded_email(forwarded)
    
    # Step 5: Save to database
    application_record = None
    if result.success:
        application_record = LoanApplicationModel(
            client_id=client.id,
            processed_by_id=forwarder.id,
            source_type='email_forward',
            applicant_email=forwarded.original_sender_email or from_email,
            applicant_name=forwarded.original_sender_name or '',
            property_address=result.application_data.get('address', ''),
            property_city=result.application_data.get('city', ''),
            property_state=result.application_data.get('state', ''),
            property_zip=result.application_data.get('zip_code', ''),
            loan_amount=result.application_data.get('loan_amount', 0),
            estimated_value=result.application_data.get('estimated_value', 0),
            units=result.application_data.get('units', 0),
            credit_score=result.application_data.get('credit_score_middle', 0),
            overall_decision=result.sizer_result.get('overall_decision', 'PENDING'),
            sizer_output=json.dumps(result.sizer_result),
            status='completed'
        )
        db.add(application_record)
        db.flush()
    
    # Step 6: Send response email back to forwarder
    email_sent = False
    if result.success and result.generated_email:
        try:
            # Create email with attachment
            email_msg = processor.create_email_with_attachment(
                to_email=from_email,
                to_name=from_name,
                subject=f"RE: {subject} - {result.sizer_result.get('overall_decision', 'ANALYSIS')}",
                html_body=result.generated_email,
                attachment_path=result.excel_file_path,
                attachment_filename=f"LoanSizer_Analysis_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            # Send via configured email provider
            await send_email_via_provider(email_msg, client)
            email_sent = True
            
        except Exception as e:
            print(f"Error sending email: {e}")
    
    # Step 7: Log processing
    log = EmailProcessingLog(
        client_id=client.id,
        user_id=forwarder.id,
        application_id=application_record.id if application_record else None,
        forwarder_email=from_email,
        to_email=to_email,
        subject=subject,
        original_sender=forwarded.original_sender_email,
        status='completed' if result.success else 'failed',
        processing_time_ms=int(result.processing_time_seconds * 1000),
        error_message=result.error_message,
        email_sent=email_sent,
        decision=result.sizer_result.get('overall_decision') if result.sizer_result else None
    )
    db.add(log)
    db.commit()
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    return {
        'success': result.success,
        'message': 'Application processed successfully' if result.success else result.error_message,
        'application_id': application_record.id if application_record else None,
        'decision': result.sizer_result.get('overall_decision') if result.sizer_result else None,
        'processing_time_ms': processing_time_ms,
        'email_sent': email_sent
    }


async def identify_client_from_email(to_email: str, db: Session) -> Optional[Client]:
    """
    Extract client from receiving email address
    Formats supported:
    - client-slug@process.loansizer.com
    - client-id@process.loansizer.com
    """
    # Extract local part (before @)
    local_part = to_email.split('@')[0].lower()
    
    # Try to find by slug
    client = db.query(Client).filter(Client.slug == local_part).first()
    if client:
        return client
    
    # Try by ID
    try:
        client_id = int(local_part)
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            return client
    except ValueError:
        pass
    
    # Try custom domain routing
    domain = to_email.split('@')[1] if '@' in to_email else ''
    if domain and domain != 'process.loansizer.com':
        client = db.query(Client).filter(Client.custom_domain == domain).first()
        if client:
            return client
    
    return None


async def send_email_via_provider(email_msg: dict, client: Client):
    """
    Send email via configured provider (SendGrid, Mailgun, SES)
    """
    provider = client.email_provider or 'sendgrid'
    
    if provider == 'sendgrid':
        await send_via_sendgrid(email_msg, client)
    elif provider == 'mailgun':
        await send_via_mailgun(email_msg, client)
    elif provider == 'ses':
        await send_via_ses(email_msg, client)
    else:
        raise ValueError(f"Unknown email provider: {provider}")


async def send_via_sendgrid(email_msg: dict, client: Client):
    """Send email via SendGrid API with attachments"""
    import httpx
    import base64
    
    api_key = client.sendgrid_api_key or os.getenv('SENDGRID_API_KEY')
    if not api_key:
        raise ValueError("SendGrid API key not configured")
    
    # Decode the MIME message to extract parts
    mime_bytes = base64.urlsafe_b64decode(email_msg['raw'])
    
    # Parse MIME message to extract HTML body and attachments
    from email import message_from_bytes
    msg = message_from_bytes(mime_bytes)
    
    html_content = ""
    attachments = []
    
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = part.get('Content-Disposition', '')
        
        if content_type == 'text/html' and 'attachment' not in content_disposition:
            html_content = part.get_payload(decode=True).decode('utf-8')
        elif 'attachment' in content_disposition:
            filename = part.get_filename()
            content = part.get_payload(decode=True)
            attachments.append({
                'content': base64.b64encode(content).decode(),
                'filename': filename,
                'type': content_type,
                'disposition': 'attachment'
            })
    
    # Build SendGrid payload
    payload = {
        'personalizations': [{
            'to': [{'email': email_msg['to']}]
        }],
        'from': {'email': 'loans@complaicore.com', 'name': 'ComplAiCore Loan Sizer'},
        'subject': email_msg['subject'],
        'content': [{
            'type': 'text/html',
            'value': html_content
        }]
    }
    
    if attachments:
        payload['attachments'] = attachments
    
    async with httpx.AsyncClient() as client_http:
        response = await client_http.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json=payload
        )
        response.raise_for_status()


async def send_via_mailgun(email_msg: dict, client: Client):
    """Send email via Mailgun API"""
    import httpx
    
    api_key = client.mailgun_api_key or os.getenv('MAILGUN_API_KEY')
    domain = client.mailgun_domain or os.getenv('MAILGUN_DOMAIN')
    
    if not api_key or not domain:
        raise ValueError("Mailgun not configured")
    
    async with httpx.AsyncClient() as client_http:
        response = await client_http.post(
            f'https://api.mailgun.net/v3/{domain}/messages',
            auth=('api', api_key),
            data={
                'from': 'Loan Sizer AI <processing@loansizer.com>',
                'to': email_msg['to'],
                'subject': email_msg['subject'],
                'html': email_msg['raw']
            }
        )
        response.raise_for_status()


async def send_via_ses(email_msg: dict, client: Client):
    """Send email via AWS SES"""
    import boto3
    
    # AWS credentials should be in environment or IAM role
    ses = boto3.client('ses')
    
    ses.send_raw_email(
        Source='processing@loansizer.com',
        Destinations=[email_msg['to']],
        RawMessage={'Data': base64.b64decode(email_msg['raw'])}
    )


# Client management endpoints
@router.get("/forwarding-address/{client_id}")
async def get_forwarding_address(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the unique email forwarding address for a client"""
    
    # Verify user belongs to this client
    if current_user.client_id != client_id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate forwarding address - use complaicore.com domain
    domain = client.custom_domain or 'complaicore.com'
    forwarding_address = f"loans+{client.slug}@{domain}"
    
    return {
        'client_id': client.id,
        'client_name': client.company_name,
        'forwarding_address': forwarding_address,
        'instructions': f"Forward loan application emails to: {forwarding_address}",
        'setup_guide': {
            'step1': f'Forward loan application emails to: {forwarding_address}',
            'step2': 'Our AI will automatically extract loan data and run analysis',
            'step3': 'You will receive an email back with PASS/FAIL decision and completed Excel file',
            'format': 'Simply forward any email containing loan application details'
        }
    }


@router.post("/setup-forwarding/{client_id}")
async def setup_email_forwarding(
    client_id: int,
    provider: str = 'sendgrid',  # sendgrid, mailgun, ses
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set up email forwarding for a client
    Creates the inbound email route/webhook
    """
    if current_user.client_id != client_id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Store provider preference
    client.email_provider = provider
    db.commit()
    
    # Generate webhook URL
    webhook_url = f"https://api.loansizer.com/email/webhook/{provider}"
    
    return {
        'status': 'configured',
        'client_id': client_id,
        'forwarding_address': f"{client.slug}@process.loansizer.com",
        'webhook_url': webhook_url,
        'provider': provider,
        'next_steps': [
            f'1. Configure {provider} to receive emails at {client.slug}@process.loansizer.com',
            f'2. Set webhook URL: {webhook_url}',
            '3. Test by forwarding an email'
        ]
    }


@router.get("/processing-history")
async def get_processing_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get email processing history for current user's client"""
    
    logs = db.query(EmailProcessingLog).filter(
        EmailProcessingLog.client_id == current_user.client_id
    ).order_by(
        EmailProcessingLog.created_at.desc()
    ).limit(limit).all()
    
    return {
        'history': [{
            'id': log.id,
            'forwarder_email': log.forwarder_email,
            'subject': log.subject,
            'original_sender': log.original_sender,
            'decision': log.decision,
            'status': log.status,
            'email_sent': log.email_sent,
            'processing_time_ms': log.processing_time_ms,
            'created_at': log.created_at.isoformat()
        } for log in logs]
    }