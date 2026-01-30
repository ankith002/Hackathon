from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import uuid
import os
from pathlib import Path
from bson import ObjectId
from contextlib import asynccontextmanager
from services import generate_content_for_all_platforms, generate_content, regenerate_content, post_to_n8n
from database import connect_to_mongo, close_mongo_connection, get_database, get_clients_collection, get_content_collection, get_campaigns_collection, get_credentials_collection
from platform_posting import post_to_platform
from puppeteer_posting import post_to_platform_puppeteer
import asyncio

def convert_objectid_to_str(obj):
    """Recursively convert ObjectId to string in dictionaries"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await connect_to_mongo()
    except Exception as e:
        print(f"⚠️ Warning: MongoDB connection issue during startup: {str(e)}")
        print("Continuing without MongoDB (will use in-memory storage)")
    
    yield
    
    # Shutdown
    try:
        await close_mongo_connection()
    except Exception as e:
        print(f"⚠️ Warning: Error during MongoDB shutdown: {str(e)}")
        # Continue shutdown even if MongoDB close fails

app = FastAPI(title="CampaignForge API", version="1.0.0", lifespan=lifespan)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Serve uploaded images statically
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class ClientOnboardingRequest(BaseModel):
    brand_tone: str
    industry: str
    target_audience: str
    past_examples: Optional[str] = None
    company_name: str
    website_url: Optional[str] = None
    social_media_handles: Optional[str] = None
    marketing_goals: Optional[str] = None
    content_preferences: Optional[str] = None
    budget_range: Optional[str] = None
    primary_channels: Optional[str] = None

class ApproveContentRequest(BaseModel):
    platform: Optional[str] = None
    credentials: Optional[dict] = None

# MongoDB collections will be accessed via helper functions from database.py

@app.get("/")
async def root():
    return {"message": "Welcome to CampaignForge API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/client/onboard")
async def onboard_client(
    brand_tone: str = Form(...),
    industry: str = Form(...),
    target_audience: str = Form(...),
    past_examples: Optional[str] = Form(None),
    company_name: str = Form(...),
    website_url: Optional[str] = Form(None),
    social_media_handles: Optional[str] = Form(None),
    marketing_goals: Optional[str] = Form(None),
    content_preferences: Optional[str] = Form(None),
    budget_range: Optional[str] = Form(None),
    primary_channels: Optional[str] = Form(None),
    texts: Optional[str] = Form(None),
    generate_images: Optional[str] = Form(None),
    images: List[UploadFile] = File(None),
    videos: List[UploadFile] = File(None)
):
    """
    Client onboarding endpoint that accepts form data including file uploads
    """
    try:
        # Process uploaded images
        image_files = []
        uploaded_image_urls = []
        if images:
            for image in images:
                if image.filename:
                    contents = await image.read()
                    # Generate unique filename
                    file_ext = Path(image.filename).suffix
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    file_path = UPLOAD_DIR / unique_filename
                    
                    # Save file
                    with open(file_path, "wb") as f:
                        f.write(contents)
                    
                    # Create URL
                    image_url = f"/uploads/images/{unique_filename}"
                    uploaded_image_urls.append(image_url)
                    
                    image_files.append({
                        "filename": image.filename,
                        "stored_filename": unique_filename,
                        "content_type": image.content_type,
                        "size": len(contents),
                        "url": image_url
                    })
        
        # Process uploaded videos
        video_files = []
        if videos:
            for video in videos:
                if video.filename:
                    contents = await video.read()
                    video_files.append({
                        "filename": video.filename,
                        "content_type": video.content_type,
                        "size": len(contents)
                    })
        
        # Create client record with UUID
        client_uuid = str(uuid.uuid4())
        client_data = {
            "client_id": client_uuid,
            "company_name": company_name,
            "brand_tone": brand_tone,
            "industry": industry,
            "target_audience": target_audience,
            "past_examples": past_examples,
            "website_url": website_url,
            "social_media_handles": social_media_handles,
            "marketing_goals": marketing_goals,
            "content_preferences": content_preferences,
            "budget_range": budget_range,
            "primary_channels": primary_channels,
            "texts": texts,
            "generate_images": generate_images == 'true' or generate_images == 'on' if generate_images else False,
            "images": image_files,
            "videos": video_files,
            "onboarded_at": datetime.now().isoformat(),
            "status": "onboarded"
        }
        
        # Save to MongoDB
        clients_collection = get_clients_collection()
        if clients_collection is not None:
            await clients_collection.insert_one(client_data)
        else:
            # Fallback to in-memory if DB not connected
            if not hasattr(app.state, 'clients_db'):
                app.state.clients_db = []
            app.state.clients_db.append(client_data)
        
        # Generate initial content for all platforms
        try:
            generated_content = generate_content_for_all_platforms(client_data)
            content_collection = get_content_collection()
            
            for content_item in generated_content:
                content_item['id'] = str(uuid.uuid4())
                content_item['created_at'] = datetime.now().isoformat()
                
                if content_collection is not None:
                    await content_collection.insert_one(content_item)
                else:
                    # Fallback to in-memory
                    if not hasattr(app.state, 'content_db'):
                        app.state.content_db = []
                    app.state.content_db.append(content_item)
        except Exception as e:
            print(f"Warning: Could not generate initial content: {str(e)}")
        
        # Convert ObjectId to string for JSON serialization (recursively handles nested structures)
        client_data_serializable = convert_objectid_to_str(client_data)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Client onboarded successfully",
                "client_id": client_data["client_id"],
                "data": client_data_serializable
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error onboarding client: {str(e)}"
            }
        )

@app.get("/api/clients")
async def get_clients():
    """Get all onboarded clients"""
    clients_collection = get_clients_collection()
    
    if clients_collection is not None:
        clients = await clients_collection.find({}).to_list(length=1000)
        # Convert ObjectId to string for JSON serialization
        for client in clients:
            if '_id' in client:
                client['_id'] = str(client['_id'])
        return {
            "success": True,
            "count": len(clients),
            "clients": clients
        }
    else:
        # Fallback to in-memory
        clients_db = getattr(app.state, 'clients_db', [])
        return {
            "success": True,
            "count": len(clients_db),
            "clients": clients_db
        }

@app.get("/api/client/{client_id}")
async def get_client(client_id: str):
    """Get specific client by ID"""
    clients_collection = get_clients_collection()
    
    if clients_collection is not None:
        client = await clients_collection.find_one({"client_id": client_id})
        if client is not None:
            if '_id' in client:
                client['_id'] = str(client['_id'])
            return {"success": True, "client": client}
    else:
        # Fallback to in-memory
        clients_db = getattr(app.state, 'clients_db', [])
        client = next((c for c in clients_db if c["client_id"] == client_id), None)
        if client is not None:
            return {"success": True, "client": client}
    
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "Client not found"}
    )

# Content Management Endpoints
@app.get("/api/content/pending")
async def get_pending_content(client_id: Optional[str] = Query(None)):
    """Get all pending content for approval"""
    content_collection = get_content_collection()
    
    if content_collection is not None:
        query = {"status": "pending"}
        if client_id and client_id != 'all':
            query["client_id"] = client_id
        
        pending = await content_collection.find(query).to_list(length=1000)
        # Convert ObjectId to string
        for item in pending:
            if '_id' in item:
                item['_id'] = str(item['_id'])
    else:
        # Fallback to in-memory
        content_db = getattr(app.state, 'content_db', [])
        pending = [c for c in content_db if c.get('status') == 'pending']
        if client_id and client_id != 'all':
            pending = [c for c in pending if c.get('client_id') == client_id]
    
    return {
        "success": True,
        "count": len(pending),
        "content": pending
    }

@app.post("/api/content/{content_id}/approve")
async def approve_content_endpoint(content_id: str, request: ApproveContentRequest = ApproveContentRequest()):
    """Approve content and post to platform with credentials"""
    try:
        content_collection = get_content_collection()
        clients_collection = get_clients_collection()
        credentials_collection = get_credentials_collection()
        
        # Get credentials and platform from request
        credentials = request.credentials if request.credentials else {}
        platform = (request.platform or '').lower()
        
        if content_collection is not None:
            content = await content_collection.find_one({"id": content_id})
            if content is None:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": f"Content not found with id: {content_id}"}
                )
        
        platform = platform or content.get('platform', '').lower()
        
        # Get client data
        if clients_collection is not None:
            client = await clients_collection.find_one({"client_id": content.get('client_id')})
        else:
            clients_db = getattr(app.state, 'clients_db', [])
            client = next((c for c in clients_db if c["client_id"] == content.get('client_id')), None)
        
        # Post to platform if credentials provided
        posting_result = None
        if credentials and platform in ['linkedin', 'reddit', 'email']:
            # Get image URL if available
            image_url = content.get('generated_image_url')
            if not image_url and content.get('uploaded_images'):
                image_url = content.get('uploaded_images', [])[0]
            if image_url and not image_url.startswith('http'):
                image_url = f"http://localhost:8000{image_url}"
            
            # Post to platform using Puppeteer (or SMTP for email)
            # Always await since post_to_platform_puppeteer is async
            posting_result = await post_to_platform_puppeteer(
                platform=platform,
                content=content.get('content', ''),
                credentials=credentials,
                image_url=image_url
            )
            
            # Store credentials for future use (optional - can be removed for security)
            if credentials_collection is not None and posting_result.get('success'):
                await credentials_collection.update_one(
                    {
                        "client_id": content.get('client_id'),
                        "platform": platform
                    },
                    {
                        "$set": {
                            "credentials": credentials,
                            "updated_at": datetime.now().isoformat()
                        }
                    },
                    upsert=True
                )
        elif platform and platform not in ['linkedin', 'reddit', 'email']:
            # For other platforms, use n8n as fallback
            if client is not None:
                posting_result = post_to_n8n(
                    platform=content.get('platform'),
                    content=content.get('content'),
                    client_data=client
                )
        
        # Update status
        update_data = {
            "status": "approved",
            "approved_at": datetime.now().isoformat()
        }
        
        if posting_result:
            update_data["posting_result"] = posting_result
        
            await content_collection.update_one(
                {"id": content_id},
                {"$set": update_data}
            )
            content.update(update_data)
            
            if '_id' in content:
                content['_id'] = str(content['_id'])
        else:
            # Fallback to in-memory
            content_db = getattr(app.state, 'content_db', [])
            clients_db = getattr(app.state, 'clients_db', [])
            content = next((c for c in content_db if c.get('id') == content_id), None)
            if content is None:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Content not found"}
                )
            
            content['status'] = 'approved'
            content['approved_at'] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "Content approved and posted",
            "data": content,
            "posting_result": posting_result if 'posting_result' in locals() else None
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in approve_content_endpoint: {str(e)}")
        print(error_trace)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error approving content: {str(e)}",
                "error": str(e)
            }
        )

@app.put("/api/content/{content_id}/edit")
async def edit_content_endpoint(content_id: str, request: dict):
    """Edit content"""
    content_collection = get_content_collection()
    
    if content_collection is not None:
        content = await content_collection.find_one({"id": content_id})
        if content is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Content not found"}
            )
        
        await content_collection.update_one(
            {"id": content_id},
            {"$set": {
                "content": request.get('content', content['content']),
                "edited_at": datetime.now().isoformat()
            }}
        )
        content['content'] = request.get('content', content['content'])
        content['edited_at'] = datetime.now().isoformat()
        if '_id' in content:
            content['_id'] = str(content['_id'])
    else:
        # Fallback to in-memory
        content_db = getattr(app.state, 'content_db', [])
        content = next((c for c in content_db if c.get('id') == content_id), None)
        if content is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Content not found"}
            )
        
        content['content'] = request.get('content', content['content'])
        content['edited_at'] = datetime.now().isoformat()
    
    return {
        "success": True,
        "message": "Content updated",
        "data": content
    }

@app.delete("/api/content/{content_id}")
async def delete_content_endpoint(content_id: str):
    """Delete content"""
    content_collection = get_content_collection()
    
    if content_collection is not None:
        result = await content_collection.delete_one({"id": content_id})
        if result.deleted_count == 0:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Content not found"}
            )
    else:
        # Fallback to in-memory
        if hasattr(app.state, 'content_db'):
            app.state.content_db = [c for c in app.state.content_db if c.get('id') != content_id]
    
    return {
        "success": True,
        "message": "Content deleted"
    }

@app.post("/api/content/{content_id}/regenerate")
async def regenerate_content_endpoint(content_id: str, request: dict):
    """Regenerate content"""
    content_collection = get_content_collection()
    clients_collection = get_clients_collection()
    
    if content_collection is not None:
        content = await content_collection.find_one({"id": content_id})
        if content is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Content not found"}
            )
        
        if clients_collection is not None:
            client = await clients_collection.find_one({"client_id": content.get('client_id')})
        else:
            clients_db = getattr(app.state, 'clients_db', [])
            client = next((c for c in clients_db if c["client_id"] == content.get('client_id')), None)
    else:
        # Fallback to in-memory
        content_db = getattr(app.state, 'content_db', [])
        clients_db = getattr(app.state, 'clients_db', [])
        content = next((c for c in content_db if c.get('id') == content_id), None)
        if content is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Content not found"}
            )
        
        client = next((c for c in clients_db if c["client_id"] == content.get('client_id')), None)
    
    if client is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Client not found"}
        )
    
    try:
        # Get existing content for regeneration
        existing_content = content.get('content', '')
        platform = request.get('platform', content.get('platform'))
        content_type = request.get('content_type', content.get('content_type'))
        improvement_focus = request.get('improvement_focus', None)
        
        # Regenerate content with improved prompt
        new_content = regenerate_content(
            client_data=client,
            platform=platform,
            content_type=content_type,
            existing_content=existing_content,
            improvement_focus=improvement_focus
        )
        
        # Update content with regenerated version
        regeneration_count = content.get('regeneration_count', 0) + 1
        
        if content_collection is not None:
            await content_collection.update_one(
                {"id": content_id},
                {"$set": {
                    "content": new_content,
                    "regenerated_at": datetime.now().isoformat(),
                    "regeneration_count": regeneration_count
                }}
            )
        
        content['content'] = new_content
        content['regenerated_at'] = datetime.now().isoformat()
        content['regeneration_count'] = regeneration_count
        
        if '_id' in content:
            content['_id'] = str(content['_id'])
        
        return {
            "success": True,
            "message": "Content regenerated successfully",
            "data": content
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error regenerating content: {str(e)}"}
        )

# Analytics Endpoints
@app.get("/api/analytics")
async def get_analytics(time_range: str = Query("7d")):
    """Get analytics data"""
    # Sample analytics data
    return {
        "success": True,
        "time_range": time_range,
        "performance_over_time": [
            {"date": "Mon", "views": 1200, "engagement": 450, "clicks": 320},
            {"date": "Tue", "views": 1900, "engagement": 680, "clicks": 510},
            {"date": "Wed", "views": 3000, "engagement": 920, "clicks": 720},
            {"date": "Thu", "views": 2780, "engagement": 850, "clicks": 680},
            {"date": "Fri", "views": 3890, "engagement": 1200, "clicks": 950},
            {"date": "Sat", "views": 2390, "engagement": 750, "clicks": 590},
            {"date": "Sun", "views": 3490, "engagement": 1100, "clicks": 890}
        ],
        "platform_performance": [
            {"name": "LinkedIn", "value": 35, "posts": 120},
            {"name": "Twitter", "value": 25, "posts": 85},
            {"name": "Instagram", "value": 20, "posts": 95},
            {"name": "Facebook", "value": 15, "posts": 70},
            {"name": "Reddit", "value": 12, "posts": 65},
            {"name": "Email", "value": 5, "posts": 30}
        ],
        "campaign_performance": [
            {"name": "Campaign A", "impressions": 45000, "clicks": 3200, "conversions": 450},
            {"name": "Campaign B", "impressions": 38000, "clicks": 2800, "conversions": 380},
            {"name": "Campaign C", "impressions": 52000, "clicks": 4100, "conversions": 520}
        ]
    }

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    clients_collection = get_clients_collection()
    content_collection = get_content_collection()
    campaigns_collection = get_campaigns_collection()
    
    if clients_collection is not None and content_collection is not None and campaigns_collection is not None:
        total_clients = await clients_collection.count_documents({})
        pending_content = await content_collection.count_documents({"status": "pending"})
        approved_content = await content_collection.count_documents({"status": "approved"})
        active_campaigns = await campaigns_collection.count_documents({"status": "active"})
    else:
        # Fallback to in-memory
        clients_db = getattr(app.state, 'clients_db', [])
        content_db = getattr(app.state, 'content_db', [])
        campaigns_db = getattr(app.state, 'campaigns_db', [])
        total_clients = len(clients_db)
        pending_content = len([c for c in content_db if c.get('status') == 'pending'])
        approved_content = len([c for c in content_db if c.get('status') == 'approved'])
        active_campaigns = len([c for c in campaigns_db if c.get('status') == 'active'])
    
    return {
        "success": True,
        "totalClients": total_clients,
        "pendingContent": pending_content,
        "approvedContent": approved_content,
        "activeCampaigns": active_campaigns
    }

# Campaign Endpoints
@app.get("/api/campaigns")
async def get_campaigns():
    """Get all campaigns"""
    campaigns_collection = get_campaigns_collection()
    
    if campaigns_collection is not None:
        campaigns = await campaigns_collection.find({}).to_list(length=1000)
        for campaign in campaigns:
            if '_id' in campaign:
                campaign['_id'] = str(campaign['_id'])
        return {
            "success": True,
            "count": len(campaigns),
            "campaigns": campaigns
        }
    else:
        # Fallback to in-memory
        campaigns_db = getattr(app.state, 'campaigns_db', [])
        return {
            "success": True,
            "count": len(campaigns_db),
            "campaigns": campaigns_db
        }

@app.post("/api/campaigns")
async def create_campaign_endpoint(campaign: dict):
    """Create a new campaign"""
    campaign_uuid = str(uuid.uuid4())
    clients_collection = get_clients_collection()
    campaigns_collection = get_campaigns_collection()
    
    # Get client name
    client_name = "Unknown"
    if clients_collection is not None:
        client = await clients_collection.find_one({"client_id": campaign.get("client_id")})
        if client is not None:
            client_name = client.get("company_name", "Unknown")
    else:
        clients_db = getattr(app.state, 'clients_db', [])
        client = next((c for c in clients_db if c["client_id"] == campaign.get("client_id")), None)
        if client is not None:
            client_name = client.get("company_name", "Unknown")
    
    campaign_data = {
        "id": campaign_uuid,
        "name": campaign.get("name"),
        "client_id": campaign.get("client_id"),
        "client_name": client_name,
        "platform": campaign.get("platform"),
        "budget": campaign.get("budget"),
        "start_date": campaign.get("start_date"),
        "end_date": campaign.get("end_date"),
        "target_audience": campaign.get("target_audience"),
        "ad_type": campaign.get("ad_type", "display"),
        "status": "active",
        "impressions": 0,
        "clicks": 0,
        "ctr": 0,
        "created_at": datetime.now().isoformat()
    }
    
    if campaigns_collection is not None:
        await campaigns_collection.insert_one(campaign_data)
    else:
        # Fallback to in-memory
        if not hasattr(app.state, 'campaigns_db'):
            app.state.campaigns_db = []
        app.state.campaigns_db.append(campaign_data)
    
    # Convert ObjectId to string for JSON serialization
    campaign_data_serializable = convert_objectid_to_str(campaign_data)
    
    return {
        "success": True,
        "message": "Campaign created",
        "data": campaign_data_serializable
    }

@app.put("/api/campaigns/{campaign_id}")
async def update_campaign_endpoint(campaign_id: str, campaign: dict):
    """Update a campaign"""
    campaigns_collection = get_campaigns_collection()
    
    if campaigns_collection is not None:
        campaign_item = await campaigns_collection.find_one({"id": campaign_id})
        if campaign_item is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Campaign not found"}
            )
        
        update_data = {k: v for k, v in campaign.items() if k != 'id'}
        update_data['updated_at'] = datetime.now().isoformat()
        
        await campaigns_collection.update_one(
            {"id": campaign_id},
            {"$set": update_data}
        )
        
        campaign_item.update(update_data)
        if '_id' in campaign_item:
            campaign_item['_id'] = str(campaign_item['_id'])
    else:
        # Fallback to in-memory
        campaigns_db = getattr(app.state, 'campaigns_db', [])
        campaign_item = next((c for c in campaigns_db if c.get('id') == campaign_id), None)
        if campaign_item is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Campaign not found"}
            )
        
        for key, value in campaign.items():
            if key != 'id':
                campaign_item[key] = value
        
        campaign_item['updated_at'] = datetime.now().isoformat()
    
    return {
        "success": True,
        "message": "Campaign updated",
        "data": campaign_item
    }

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign_endpoint(campaign_id: str):
    """Delete a campaign"""
    campaigns_collection = get_campaigns_collection()
    
    if campaigns_collection is not None:
        result = await campaigns_collection.delete_one({"id": campaign_id})
        if result.deleted_count == 0:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Campaign not found"}
            )
    else:
        # Fallback to in-memory
        if hasattr(app.state, 'campaigns_db'):
            app.state.campaigns_db = [c for c in app.state.campaigns_db if c.get('id') != campaign_id]
    
    return {
        "success": True,
        "message": "Campaign deleted"
    }

if __name__ == "__main__":
    import signal
    import sys
    import logging
    
    # Suppress KeyboardInterrupt errors during reload (Windows uvicorn issue)
    import logging
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Suppress multiprocessing KeyboardInterrupt during reload
    import multiprocessing
    import multiprocessing.process
    
    # Patch to handle KeyboardInterrupt gracefully during reload
    _original_bootstrap = multiprocessing.process.BaseProcess._bootstrap
    
    def _patched_bootstrap(self):
        try:
            return _original_bootstrap(self)
        except (KeyboardInterrupt, SystemExit):
            # Silently handle interrupts during reload - this is normal on Windows
            pass
        except Exception:
            # Re-raise other exceptions
            raise
    
    multiprocessing.process.BaseProcess._bootstrap = _patched_bootstrap
    
    def signal_handler(sig, frame):
        """Handle shutdown signals gracefully"""
        print("\n🛑 Shutting down server gracefully...")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown (only on Unix-like systems)
    if sys.platform != 'win32':
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    # Run with reload enabled, but handle Windows-specific issues
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            reload=True,
            reload_delay=1.5,  # Add delay to prevent rapid reloads
            log_level="info",
            reload_excludes=["*.pyc", "__pycache__", "*.log"]  # Exclude cache files
        )
    except KeyboardInterrupt:
        # Handle keyboard interrupt gracefully
        print("\n🛑 Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
