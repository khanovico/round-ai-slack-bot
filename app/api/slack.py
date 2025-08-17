"""
Slack API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
import json
import logging
from app.slack.oauth import oauth_handler
from app.slack.bot import bot_manager
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from app.core.logging_config import get_logger
from app.ai.services.nl2sql_service import NL2SQLService, NL2SQServiceResponse

# Initialize chat history manager
nl2sql_service = NL2SQLService()

# Create router
router = APIRouter(prefix="/slack", tags=["slack"])
logger = get_logger("app.slack.api")

@router.get("/oauth/install")
async def slack_install():
    """Get OAuth installation URL"""
    try:
        oauth_url = oauth_handler.get_oauth_url()
        return {
            "message": "Installation required",
            "oauth_url": oauth_url,
            "instructions": "Click the OAuth URL to install the Slack app to your workspace"
        }
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate OAuth URL")


@router.get("/oauth/callback")
async def slack_oauth_callback(code: str, state: str = None):
    """Handle OAuth callback from Slack"""
    try:
        result = await oauth_handler.exchange_code_for_token(code, state)
        
        if result['success']:
            return {
                "message": "Installation successful! 🎉",
                "team_name": result['team_name'],
                "bot_user_id": result['bot_user_id'],
                "workspace_id": result['workspace_id'],
                "next_steps": [
                    "The bot has been added to your workspace",
                    "You can now mention the bot with @your-bot-name",
                    "Try saying 'hello' or 'help' to get started"
                ]
            }
        else:
            raise HTTPException(status_code=400, detail=f"Installation failed: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth callback failed")

@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack events - routes to the bot instance"""
    try:
        # Get the request body
        body = await request.body()
        event_data = json.loads(body)  
        event_type = event_data.get("type")
        
        if event_type == "url_verification":
            # Handle Slack URL verification challenge
            challenge = event_data.get("challenge")
            if not challenge:
                logger.error("No challenge found in url_verification request")
                return JSONResponse(
                    status_code=400,
                    content={"error": "No challenge found"}
                )
            
            logger.info("Processing Slack URL verification challenge")
            # Return challenge as plain text (not JSON)
            return PlainTextResponse(content=challenge, status_code=200)

        # Handle app_mention events (when someone mentions the bot)
        if event_type == "event_callback":
            # Get the event
            event = event_data.get("event", {})
            event_type_inner = event.get("type")
            event_subtype = event.get("subtype")
            text = event.get("text", "")
            channel = event.get("channel")

            bot_user_id = event_data.get("authorizations", [{}])[0].get("user_id") if event_data.get("authorizations") else None
            
            if (event.get("bot_id") or 
                event.get("user") == "USLACKBOT" or 
                (bot_user_id and event.get("user") == bot_user_id)):
                logger.info(f"Ignoring bot message (bot_id: {event.get('bot_id')}, user: {event.get('user')}, our_bot: {bot_user_id})")
                return JSONResponse(
                    status_code=200,
                    content={"success": True, "message": "Bot message ignored"}
                )

            logger.info(f"Processing {event_type_inner} event")
            
            # Handle app_mention events using bot manager
            if event.get("type") == "message" and not event_subtype and text != "":
                result = await nl2sql_service.run(text, channel)

                if result.get("success"):
                    if result.get("type") == 'text':
                        await bot_manager.handle_message(result)
                    if result.get("type") == 'table':
                        await bot_manager.handle_table(result)
                    if result.get("type") == 'download':
                        await bot_manager.handle_download(result)
                    return JSONResponse(
                        content={"message": "App mention handled successfully", "status": "ok"},
                        status_code=200
                    )
                else:
                    logger.error(f"Failed to handle app mention: {result.get('error')}")
                    return JSONResponse(
                        content={"error": result.get("error")},
                        status_code=500
                    )
            
            logger.info(f"Event type {event_type_inner} processed")
        
        # For other events, return a simple acknowledgment
        return JSONResponse(
            content={"message": "Event received", "status": "ok"},
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle Slack event")
