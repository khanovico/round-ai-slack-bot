"""
Slack bot module with database integration
"""

import logging
from typing import Optional, Dict, Any
from app.db.database import AsyncSessionLocal
from app.models import SlackWorkspace
from slack_sdk.web import WebClient
from sqlalchemy import select

logger = logging.getLogger(__name__)

class SlackBotManager:
    """Manages Slack bot instance for single workspace"""
    
    def __init__(self):
        self.bot = None  # Single bot instance
        self.oauth_handler = None
    
    def set_oauth_handler(self, oauth_handler):
        """Set the OAuth handler"""
        self.oauth_handler = oauth_handler
    
    async def get_bot(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get bot instance for the installed workspace"""
        if self.bot:
            if(self.bot['channel_id'] == channel_id):
                return self.bot
        
        # Create new bot instance
        bot = await self._create_bot(channel_id)
        if bot:
            self.bot = bot
            return bot
        
        return None
    
    async def _create_bot(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Create bot instance for the installed workspace"""
        try:
            # Get the first active workspace from database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SlackWorkspace).where(SlackWorkspace.channel_id == channel_id)
                )
                workspace = result.scalar_one_or_none()
                if not workspace:
                    logger.warning("No active workspace found in database")
                    return None
                
                # Get bot token from workspace
                bot_token = workspace.bot_token
                if not bot_token:
                    logger.warning(f"No bot token found for workspace {workspace.team_name}")
                    return None
                
                # Create simple bot info without Slack Bolt
                bot_info = {
                    'token': bot_token,
                    'team_name': workspace.team_name,
                    'team_id': workspace.team_id,
                    'bot_user_id': workspace.bot_user_id,
                    'channel_id': workspace.channel_id
                }
                
                logger.info(f"Created bot instance for workspace: {workspace.team_name}")
                return bot_info
                    
        except Exception as e:
            logger.error(f"Error getting workspace from database: {e}")
            return None

    def create_ascii_table(self, data):
        """Create an ASCII table from data"""
        if not data or len(data) == 0:
            return "No data provided"
        
        # Extract headers from the first object's keys
        headers = list(data[0].keys())
        
        # Calculate the maximum width for each column
        column_widths = []
        for header in headers:
            max_width = len(header)
            for row in data:
                max_width = max(max_width, len(str(row[header])))
            column_widths.append(max_width)
        
        # Create the divider
        divider = "+" + "+".join("-" * (width + 2) for width in column_widths) + "+"
        
        # Create the header row
        header_row = "|" + "|".join(f" {header.ljust(column_widths[i])} " for i, header in enumerate(headers)) + "|"
        
        # Generate each row of data
        rows = []
        for row in data:
            row_str = "|" + "|".join(f" {str(row[header]).ljust(column_widths[i])} " for i, header in enumerate(headers)) + "|"
            rows.append(row_str)
        
        # Assemble the full table
        return "\n".join([divider, header_row, divider] + rows + [divider])

    async def handle_message(self, result) -> Dict[str, Any]:
        """Handle all app mention events using the intelligent agent runtime"""
        try:
            # Get bot info
            bot_info = await self.get_bot(result.session_id)
            if not bot_info:
                logger.error("No bot available to handle app mention")
                return {"success": False, "error": "Bot not available"}

            channel = result.session_id
            text = result.answer
            client = WebClient(token=bot_info['token'])
            slack_response = client.chat_postMessage(
                channel=channel,
                text=text
            )

            if slack_response.get("ok"):
                logger.info(f"Successfully sent response to channel {channel}")
                return {"success": True, "message": "Response sent successfully"}
            else:
                logger.error(f"Failed to send message: {slack_response.get('error')}")
                return {"success": False, "error": f"Slack API error: {slack_response.get('error')}"}


        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"success": False, "error": str(e)}

    async def handle_table(self, result) -> Dict[str, Any]:
        """Handle all app mention events using the intelligent agent runtime"""
        try:
            # Get bot info
            bot_info = await self.get_bot(result.session_id)
            if not bot_info:
                logger.error("No bot available to handle app mention")
                return {"success": False, "error": "Bot not available"}

            channel = result.session_id
            text = result.answer
            data = result.data
            client = WebClient(token=bot_info['token'])
            
            # Create ASCII table
            table_string = self.create_ascii_table(result.data)
            code_block = f"```\n{table_string}\n```"
            
            # Send message using WebClient
            client = WebClient(token=bot_info['token'])
            slack_response = client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=[
                    {
                        "text": {
                            "emoji": True,
                            "text": text,
                            "type": "plain_text",
                        },
                        "type": "section"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": code_block
                            }
                        ]
                    }
                ]
            )

            if slack_response.get("ok"):
                logger.info(f"Successfully sent response to channel {channel}")
                return {"success": True, "message": "Response sent successfully"}
            else:
                logger.error(f"Failed to send message: {slack_response.get('error')}")
                return {"success": False, "error": f"Slack API error: {slack_response.get('error')}"}

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"success": False, "error": str(e)}

    async def handle_download(self, result) -> Dict[str, Any]:
        """Handle all app mention events using the intelligent agent runtime"""
        try:
            # Get bot info
            bot_info = await self.get_bot(result.session_id)
            if not bot_info:
                logger.error("No bot available to handle app mention")
                return {"success": False, "error": "Bot not available"}

            channel = result.session_id
            text = result.answer
            data = result.data
            client = WebClient(token=bot_info['token'])
            
            slack_response = client.chat_postMessage(
                channel=channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn","text": text},
                        "accessory": {
                            "type": "button",
                            "text": {"type":"plain_text","text":"Download CSV"},
                            "url": data
                        }
                    }
                ],
                text="Weekly Sales with download link"
            )

            if slack_response.get("ok"):
                logger.info(f"Successfully sent response to channel {channel}")
                return {"success": True, "message": "Response sent successfully"}
            else:
                logger.error(f"Failed to send message: {slack_response.get('error')}")
                return {"success": False, "error": f"Slack API error: {slack_response.get('error')}"}

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"success": False, "error": str(e)}

    async def handle_sql(self, result) -> Dict[str, Any]:
        """Handle all app mention events using the intelligent agent runtime"""
        try:
            # Get bot info
            bot_info = await self.get_bot(result.session_id)
            if not bot_info:
                logger.error("No bot available to handle app mention")
                return {"success": False, "error": "Bot not available"}

            channel = result.session_id
            text = result.answer
            data = result.data
            client = WebClient(token=bot_info['token'])
            
            # Format the text with proper styling using Slack blocks
            slack_response = client.chat_postMessage(
                channel=channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f'`{data}`'
                        }
                    }
                ],
                text=text  # Fallback text for notifications
            )

            if slack_response.get("ok"):
                logger.info(f"Successfully sent response to channel {channel}")
                return {"success": True, "message": "Response sent successfully"}
            else:
                logger.error(f"Failed to send message: {slack_response.get('error')}")
                return {"success": False, "error": f"Slack API error: {slack_response.get('error')}"}

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"success": False, "error": str(e)}

    async def handle_error(self, result) -> Dict[str, Any]:
        """Handle error messages with proper formatting"""
        try:
            # Get bot info

            bot_info = await self.get_bot(result.session_id)

            if not bot_info:
                logger.error("No bot available to handle error message")
                return {"success": False, "error": "Bot not available"}

            channel = result.session_id
            error_text = result.answer
            client = WebClient(token=bot_info['token'])
            
            # Format error message with warning styling
            slack_response = client.chat_postMessage(
                channel=channel,
                text=f"Error: {error_text}"  # Fallback text for notifications
            )

            if slack_response.get("ok"):
                logger.info(f"Successfully sent error message to channel {channel}")
                return {"success": True, "message": "Error message sent successfully"}
            else:
                logger.error(f"Failed to send error message: {slack_response.get('error')}")
                return {"success": False, "error": f"Slack API error: {slack_response.get('error')}"}

        except Exception as e:
            logger.error(f"Error handling error message: {e}")
            return {"success": False, "error": str(e)}


    async def get_workspace_info(self):
        """Get information about the installed workspace"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SlackWorkspace).where(SlackWorkspace.is_active == True)
                )
                workspace = result.scalar_one_or_none()
                
                if workspace:
                    return {
                        'id': workspace.id,
                        'team_id': workspace.team_id,
                        'team_name': workspace.team_name,
                        'bot_user_id': workspace.bot_user_id,
                        'bot_token': workspace.bot_token,
                        'is_active': workspace.is_active
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return None


# Global bot manager instance
bot_manager = SlackBotManager()