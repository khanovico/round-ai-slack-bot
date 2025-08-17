"""
CSV utility functions for data export
"""
import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from app.core.logging_config import get_logger

from .drive_utils import upload_file_to_drive

logger = get_logger("app.utils.csv")


def dict_list_to_csv(data: List[Dict[str, Any]], filename: str = None, output_dir: str = "exports") -> str:
    """
    Convert list of dictionaries to CSV file and return file path
    
    Args:
        data: List of dictionaries to convert
        filename: Optional filename (will generate timestamp-based name if not provided)
        output_dir: Directory to save the file (relative to project root)
    
    Returns:
        str: Absolute path to the created CSV file
    
    Raises:
        ValueError: If data is empty or invalid
        IOError: If file cannot be written
    """
    if not data:
        raise ValueError("Data list cannot be empty")
    
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("Data must be a list of dictionaries")
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.csv"
    
    # Ensure filename has .csv extension
    if not filename.endswith('.csv'):
        filename += '.csv'
    
    # Create output directory if it doesn't exist
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / output_dir
    output_path.mkdir(exist_ok=True)
    
    # Full file path
    file_path = output_path / filename
    
    try:
        # Get all unique keys from all dictionaries (in case some dicts have different keys)
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        
        # Sort keys for consistent column order
        fieldnames = sorted(all_keys)
        
        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for row in data:
                # Ensure all fields are present (fill missing with empty string)
                clean_row = {key: row.get(key, '') for key in fieldnames}
                writer.writerow(clean_row)
        
        logger.info(f"Successfully created CSV file: {file_path}")
        logger.info(f"Exported {len(data)} rows with {len(fieldnames)} columns")
        
        return str(file_path.absolute())
        
    except Exception as e:
        logger.error(f"Error creating CSV file: {e}")
        raise IOError(f"Failed to create CSV file: {e}")


def get_export_dir_path() -> str:
    """Get the absolute path to the exports directory"""
    project_root = Path(__file__).parent.parent.parent
    return str((project_root / "exports").absolute())


def list_csv_exports() -> List[str]:
    """List all CSV files in the exports directory"""
    export_dir = Path(get_export_dir_path())
    
    if not export_dir.exists():
        return []
    
    csv_files = []
    for file_path in export_dir.glob("*.csv"):
        csv_files.append(str(file_path.absolute()))
    
    return sorted(csv_files, reverse=True)  # Most recent first


def cleanup_old_exports(max_files: int = 10) -> int:
    """
    Clean up old CSV export files, keeping only the most recent ones
    
    Args:
        max_files: Maximum number of files to keep
    
    Returns:
        int: Number of files deleted
    """
    csv_files = list_csv_exports()
    
    if len(csv_files) <= max_files:
        return 0
    
    files_to_delete = csv_files[max_files:]
    deleted_count = 0
    
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            deleted_count += 1
            logger.info(f"Deleted old export file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")
    
    return deleted_count


def upload_csv(file_path: str, custom_filename: Optional[str] = None) -> str:
    """
    Upload CSV file to Google Drive and return shareable URL
    
    Args:
        file_path: Path to the CSV file to upload
        custom_filename: Optional custom filename for the upload
    
    Returns:
        str: Shareable Google Drive URL
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If upload fails
    """    
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    # Use custom filename or original filename
    upload_filename = custom_filename or file_path.name
    
    # Ensure .csv extension
    if not upload_filename.endswith('.csv'):
        upload_filename += '.csv'
    
    try:
        logger.info(f"Uploading CSV file to Google Drive: {file_path}")
        url = upload_file_to_drive(str(file_path), upload_filename)
        return url
        
    except Exception as e:
        logger.error(f"Failed to upload CSV to Google Drive: {e}")
        raise


def create_and_upload_csv(data: List[Dict[str, Any]], filename: str = None) -> tuple[str, str]:
    """
    Create CSV file from data and upload to transfer.sh
    
    Args:
        data: List of dictionaries to convert
        filename: Optional filename
    
    Returns:
        tuple: (local_file_path, download_url)
    """
    # Create CSV file
    local_path = dict_list_to_csv(data, filename)
    
    # Upload to transfer.sh
    download_url = upload_csv(local_path)
    
    return local_path, download_url