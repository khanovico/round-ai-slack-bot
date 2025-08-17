"""
Slack OAuth handler with Slack SDK installation store
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.web import WebClient
from slack_sdk.oauth.installation_store import Installation
from slack_sdk.errors import SlackApiError
from uuid import uuid4
import html
import json

from app.db.database import AsyncSessionLocal
from app.models import SlackWorkspace
from app.core.config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)

class SlackOAuthHandler:
    """Handles Slack OAuth flow using Slack SDK installation store"""
    
    def __init__(self):
        self.client_id = settings.SLACK_CLIENT_ID
        self.client_secret = settings.SLACK_CLIENT_SECRET
        self.redirect_uri = settings.SLACK_REDIRECT_URI
        
        # Initialize OAuth URL generator
        self.authorize_url_generator = AuthorizeUrlGenerator(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scopes=["chat:write", "app_mentions:read", "channels:history", "channels:read", "groups:read"],
        )
        
        # Simple state store (in production, use Redis or database)
        self.state_store = set()
    
    def get_oauth_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        try:
            # Generate a unique state parameter
            state_param = state or str(uuid4())
            self.state_store.add(state_param)
            
            # Generate OAuth URL
            oauth_url = self.authorize_url_generator.generate(state=state_param)
            
            logger.info(f"Generated OAuth URL with state: {state_param}")
            return oauth_url
            
        except Exception as e:
            logger.error(f"Error generating OAuth URL: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating oauth url: {str(e)}")
    
    async def exchange_code_for_token(self, code: str, state: str = None) -> Dict[str, Any]:
        """Exchange authorization code for access token and create installation"""
        try:
            # Complete the installation by calling oauth.v2.access API method
            client = WebClient()  # no prepared token needed for this
            oauth_response = client.oauth_v2_access(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                code=code
            )
            
            if not oauth_response.get("ok", False):
                error_msg = oauth_response.get('error', 'Unknown error')
                logger.error(f"Slack OAuth error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Extract installation data
            installed_enterprise = oauth_response.get("enterprise") or {}
            is_enterprise_install = oauth_response.get("is_enterprise_install")
            installed_team = oauth_response.get("team") or {}
            installer = oauth_response.get("authed_user") or {}
            incoming_webhook = oauth_response.get("incoming_webhook") or {}
            bot_token = oauth_response.get("access_token")
            
            # Get bot_id if bot_token is available
            bot_id = None
            enterprise_url = None
            channel_id = None
            channel_name = None
            
            if bot_token is not None:
                auth_test = client.auth_test(token=bot_token)
                bot_id = auth_test["bot_id"]

                if is_enterprise_install is True:
                    enterprise_url = auth_test.get("url")
                # Find or create the default channel
                try:
                    # Create WebClient with bot token to access channels
                    bot_client = WebClient(token=bot_token)
                    
                    # List all channels to find the default channel
                    channels_response = bot_client.conversations_list(types="public_channel,private_channel")
                    channels = channels_response['channels']
                    
                    # Look for the default channel
                    channel_found = False
                    for channel in channels:
                        if channel['name'] == settings.DEFAULT_SLACK_CHANNEL:
                            channel_id = channel['id']
                            channel_name = channel['name']
                            logger.info(f"Found existing default channel '{channel_name}' with ID: {channel_id}")
                            channel_found = True
                            break
                    
                    # If channel doesn't exist, try to create it
                    if not channel_found:
                        try:
                            create_response = bot_client.conversations_create(
                                name=settings.DEFAULT_SLACK_CHANNEL,
                                is_private=False  # Create as public channel
                            )
                            channel_id = create_response['channel']['id']
                            channel_name = create_response['channel']['name']

                            # After creating the channel
                            # Invite the bot user                   
                            
                            logger.info(f"Created new default channel '{channel_name}' with ID: {channel_id}")
                            
                            # Send welcome message to the new channel
                            try:
                                welcome_message = {
                                    "channel": channel_id,
                                    "text": f"🎉 Welcome to #{channel_name}! I'm your AI assistant bot.\n\nI can help you with:\n• Data analysis and insights\n• SQL queries and database questions\n• Generating reports and visualizations\n• Answering questions about your data"
                                }
                                
                                # Send the welcome message using the bot client
                                bot_client.chat_postMessage(**welcome_message)
                                logger.info(f"Sent welcome message to channel #{channel_name}")
                                
                            except SlackApiError as welcome_error:
                                logger.warning(f"Could not send welcome message to channel #{channel_name}: {welcome_error}")
                                # Continue without welcome message - not critical
                        except SlackApiError as create_error:
                            if create_error.response['error'] in SLACK_CHANNEL_CREATE_ERRORS:
                                logger.warning(f"Channel '{settings.DEFAULT_SLACK_CHANNEL}' already exists but couldn't find it")
                                # Try to find it again after creation attempt
                                channels_response = bot_client.conversations_list(types="public_channel")
                                for channel in channels_response.get('channels', []):
                                    if channel['name'] == settings.DEFAULT_SLACK_CHANNEL:
                                        channel_id = channel['id']
                                        channel_name = channel['name']
                                        logger.info(f"Found channel after creation attempt: '{channel_name}' with ID: {channel_id}")
                                        break
                            else:
                                logger.warning(f"Could not create default channel '{settings.DEFAULT_SLACK_CHANNEL}': {create_error}")
                                # Continue without default channel
                    
                    installer_user_id = installer.get("id")
                    if installer_user_id:
                        try:
                            bot_client.conversations_invite(channel=channel_id, users=installer_user_id)
                        except SlackApiError as e:
                            if e.response['error'] != 'already_in_channel':
                                logger.warning(f"Could not invite installer to channel: {e}")
                    
                except SlackApiError as e:
                    logger.warning(f"Error accessing channels: {e}")

            installation = Installation(
                app_id=oauth_response.get("app_id"),
                team_id=installed_team.get("id"),
                team_name=installed_team.get("name"),
                bot_token=bot_token,
                bot_id=bot_id,
                bot_user_id=oauth_response.get("bot_user_id"),
                bot_scopes=oauth_response.get("scope"),
                user_id=installer.get("id"),
                user_token=installer.get("access_token"),
                user_scopes=installer.get("scope"),
                is_enterprise_install=is_enterprise_install,
                token_type=oauth_response.get("token_type"),
            )
            # Save installation to database (using our existing model for now)
            try:
                async with AsyncSessionLocal() as db:
                    try:
                        # Check if workspace already exists
                        existing_workspace = await db.execute(
                            select(SlackWorkspace).where(SlackWorkspace.team_id == installation.team_id)
                        )
                        existing_workspace = existing_workspace.scalar_one_or_none()
                        
                        workspace_data = {
                            'team_id': installation.team_id,
                            'team_name': installation.team_name,
                            'bot_user_id': installation.bot_user_id,
                            'bot_token': installation.bot_token,
                            'is_active': True
                        }

                        print("==============================", workspace_data['team_name'])
                        
                        if existing_workspace:
                            # Update existing workspace
                            for key, value in workspace_data.items():
                                setattr(existing_workspace, key, value)
                            await db.commit()
                            workspace = existing_workspace
                            logger.info(f"Updated existing workspace: {workspace_data['team_name']}")
                        else:
                            # Create new workspace
                            workspace = SlackWorkspace(**workspace_data)
                            db.add(workspace)
                            await db.commit()
                            await db.refresh(workspace)
                            logger.info(f"Created new workspace: {workspace_data['team_name']}")
                        
                        return {
                            'success': True,
                            'team_name': workspace_data['team_name'],
                            'bot_user_id': workspace_data['bot_user_id'],
                            'workspace_id': workspace.id
                        }
                        
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Database error: {e}")
                        return {
                            'success': False,
                            'error': f"Database error: {str(e)}"
                        }
                    
            except Exception as e:
                logger.error(f"Error saving installation: {e}")
                return {
                    'success': False,
                    'error': f"Installation save error: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error during token exchange: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_workspace_by_team_id(self, team_id: str) -> Optional[SlackWorkspace]:
        """Get workspace by team ID from database"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SlackWorkspace).where(
                        SlackWorkspace.team_id == team_id,
                        SlackWorkspace.is_active == True
                    )
                )
                workspace = result.scalar_one_or_none()
                return workspace
        except Exception as e:
            logger.error(f"Error getting workspace: {e}")
            return None
    
    async def get_bot_token(self, team_id: str) -> Optional[str]:
        """Get bot token for a specific team"""
        workspace = await self.get_workspace_by_team_id(team_id)
        return workspace.bot_token if workspace else None
    
    async def is_authenticated(self, team_id: str) -> bool:
        """Check if a team is authenticated"""
        return bool(await self.get_bot_token(team_id))
    
    async def get_workspace_info(self, team_id: str) -> Dict[str, Any]:
        """Get workspace information"""
        workspace = await self.get_workspace_by_team_id(team_id)
        if workspace:
            return {
                'workspace': {
                    'id': workspace.id,
                    'team_id': workspace.team_id,
                    'team_name': workspace.team_name,
                    'bot_user_id': workspace.bot_user_id,
                    'bot_token': workspace.bot_token,
                    'is_active': workspace.is_active
                }
            }
        return {}
    
    async def revoke_workspace(self, team_id: str) -> bool:
        """Revoke and deactivate workspace"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SlackWorkspace).where(SlackWorkspace.team_id == team_id)
                )
                workspace = result.scalar_one_or_none()
                
                if workspace:
                    workspace.is_active = False
                    await db.commit()
                    logger.info(f"Revoked workspace: {workspace.team_name}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error revoking workspace: {e}")
            return False


# Global OAuth handler instance
oauth_handler = SlackOAuthHandler()
