"""
Simple Google Drive upload utility
"""
from pathlib import Path
from typing import Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("app.utils.drive")


def upload_file_to_drive(file_path: str, filename: Optional[str] = None) -> str:
    """
    Upload file to Google Drive and return shareable URL
    
    Args:
        file_path: Path to file to upload
        filename: Optional custom filename
    
    Returns:
        str: Shareable Google Drive URL
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        raise ImportError("Google Drive API libraries not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib")
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    upload_name = filename or file_path.name
    
    try:
        # Get credentials
        service = _get_drive_service()
        
        # Upload file
        file_metadata = {'name': upload_name}
        media = MediaFileUpload(str(file_path))
        
        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = result.get('id')
        
        # Make public
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Return shareable URL
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        logger.info(f"Uploaded to Google Drive: {url}")
        
        return url
        
    except Exception as e:
        logger.error(f"Google Drive upload failed: {e}")
        raise


def _get_drive_service():
    """Get authenticated Google Drive service using OAuth client credentials"""
    if not settings.GOOGLE_DRIVE_CREDENTIALS_FILE:
        raise ValueError("GOOGLE_DRIVE_CREDENTIALS_FILE not set in config")
    
    creds_path = Path(settings.GOOGLE_DRIVE_CREDENTIALS_FILE)
    if not creds_path.exists():
        raise FileNotFoundError(f"OAuth credentials file not found: {creds_path}")
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # Use OAuth flow for desktop/installed app
    token_path = creds_path.parent / "token.json"
    
    creds = None
    # Load existing token if it exists
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
            logger.info("Refreshed Google Drive OAuth token")
        else:
            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Completed Google Drive OAuth authentication")
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        logger.info("Saved Google Drive OAuth token")
    
    logger.info("Using OAuth client credentials for Google Drive")
    return build('drive', 'v3', credentials=creds)