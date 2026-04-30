"""
API endpoints for batch loan application processing
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
from datetime import datetime
import json
import asyncio
from io import BytesIO

from batch_processor import batch_processor, ApplicationParser, ProcessingStatus

router = APIRouter(prefix="/batch", tags=["batch-processing"])


@router.post("/upload")
async def upload_applications(
    files: List[UploadFile] = File(...),
    folder_name: Optional[str] = Form(None)
):
    """Upload multiple loan application files for batch processing"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    file_contents = []
    
    for file in files:
        content = await file.read()
        file_contents.append({
            'filename': file.filename,
            'content': content.decode('utf-8', errors='replace')
        })
    
    # Add applications to queue
    application_ids = batch_processor.add_applications(file_contents)
    
    return {
        "success": True,
        "folder_name": folder_name or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "applications_added": len(application_ids),
        "application_ids": application_ids,
        "total_in_queue": len(batch_processor.processing_queue)
    }


@router.post("/process")
async def start_batch_processing(background_tasks: BackgroundTasks):
    """Start processing all pending applications in the queue"""
    
    if batch_processor.is_processing:
        return {
            "success": False,
            "message": "Processing already in progress",
            "is_processing": True
        }
    
    pending_count = len([a for a in batch_processor.processing_queue 
                        if a.status == ProcessingStatus.PENDING])
    
    if pending_count == 0:
        return {
            "success": False,
            "message": "No pending applications to process",
            "is_processing": False
        }
    
    # Start processing in background
    background_tasks.add_task(batch_processor.process_all)
    
    return {
        "success": True,
        "message": f"Started processing {pending_count} applications",
        "pending_count": pending_count,
        "is_processing": True
    }


@router.get("/status")
async def get_batch_status():
    """Get current processing status and queue information"""
    
    all_apps = batch_processor.get_all_applications()
    
    return {
        "is_processing": batch_processor.is_processing,
        "total_applications": len(all_apps),
        "pending": len([a for a in all_apps if a['status'] == 'pending']),
        "processing": len([a for a in all_apps if a['status'] == 'processing']),
        "completed": len([a for a in all_apps if a['status'] == 'completed']),
        "error": len([a for a in all_apps if a['status'] == 'error']),
        "results_summary": {
            "pass": len([a for a in all_apps if a['result'] == 'PASS']),
            "conditional": len([a for a in all_apps if a['result'] == 'CONDITIONAL']),
            "fail": len([a for a in all_apps if a['result'] == 'FAIL']),
            "pending_result": len([a for a in all_apps if a['result'] == 'Pending'])
        },
        "total_amount": sum(a['loan_amount'] for a in all_apps),
        "pass_amount": sum(a['loan_amount'] for a in all_apps if a['result'] == 'PASS')
    }


@router.get("/applications")
async def get_applications(
    status: Optional[str] = "all",
    limit: int = 100,
    offset: int = 0
):
    """Get list of all applications with optional filtering"""
    
    applications = batch_processor.get_by_status(status)
    
    # Sort by created_at descending
    applications.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Paginate
    total = len(applications)
    applications = applications[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "applications": applications
    }


@router.get("/applications/{app_id}")
async def get_application_details(app_id: str):
    """Get detailed information for a specific application"""
    
    all_apps = batch_processor.get_all_applications()
    app = next((a for a in all_apps if a['id'] == app_id), None)
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return app


@router.post("/export/pdf")
async def export_to_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = "all"
):
    """Export applications to PDF format with optional date filtering"""
    
    # Get applications based on filters
    if start_date or end_date:
        applications = batch_processor.get_by_date_range(start_date, end_date)
    else:
        applications = batch_processor.get_by_status(status_filter)
    
    if not applications:
        raise HTTPException(status_code=404, detail="No applications found for export")
    
    # Generate PDF-like JSON structure
    export_data = batch_processor.export_to_dict(applications)
    
    # Return as JSON for now - frontend will handle PDF generation
    return JSONResponse(content=export_data)


@router.post("/export/csv")
async def export_to_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = "all"
):
    """Export applications to CSV format with optional date filtering"""
    
    # Get applications based on filters
    if start_date or end_date:
        applications = batch_processor.get_by_date_range(start_date, end_date)
    else:
        applications = batch_processor.get_by_status(status_filter)
    
    if not applications:
        raise HTTPException(status_code=404, detail="No applications found for export")
    
    # Generate CSV
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Application ID', 'Date', 'Applicant Name', 'Entity', 'Loan Type',
        'Loan Amount', 'Property', 'City', 'State', 'FICO', 'DSCR', 'LTV',
        'Result', 'Status', 'Recommendation'
    ])
    
    # Write data
    for app in applications:
        recommendation = app.get('result_details', {}).get('recommendation', '')
        writer.writerow([
            app['id'],
            app.get('processed_at', app.get('created_at', '')),
            app['applicant_name'],
            app['entity_name'],
            app['loan_type'],
            f"${app['loan_amount']:,.2f}",
            app['property_address'],
            app['property_city'],
            app['property_state'],
            app['fico_score'],
            app['dscr_ratio'] if app['dscr_ratio'] else '',
            f"{app['ltv_ratio']:.1%}" if app['ltv_ratio'] else '',
            app['result'],
            app['status'],
            recommendation
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=batch_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.delete("/clear")
async def clear_batch_queue():
    """Clear all applications from the queue"""
    
    batch_processor.processing_queue = []
    batch_processor.completed_applications = []
    batch_processor.is_processing = False
    
    return {
        "success": True,
        "message": "Batch queue cleared"
    }


@router.delete("/applications/{app_id}")
async def delete_application(app_id: str):
    """Delete a specific application from the queue"""
    
    # Remove from queue
    batch_processor.processing_queue = [
        a for a in batch_processor.processing_queue if a.id != app_id
    ]
    
    # Remove from completed
    batch_processor.completed_applications = [
        a for a in batch_processor.completed_applications if a.id != app_id
    ]
    
    return {
        "success": True,
        "message": f"Application {app_id} deleted"
    }


# WebSocket support for real-time updates
@router.websocket("/ws")
async def websocket_batch_status(websocket):
    """WebSocket endpoint for real-time batch processing updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send current status every 2 seconds
            status = {
                "is_processing": batch_processor.is_processing,
                "total": len(batch_processor.processing_queue) + len(batch_processor.completed_applications),
                "completed": len(batch_processor.completed_applications),
                "applications": batch_processor.get_all_applications()
            }
            
            await websocket.send_json(status)
            await asyncio.sleep(2)
            
    except Exception:
        await websocket.close()
