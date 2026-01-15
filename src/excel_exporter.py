import pandas as pd
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from loguru import logger


class ExcelExporter:
    """Handles exporting leads to Excel file on user's desktop with date in filename."""
    
    def __init__(self, desktop_path: str = None):
        """
        Initialize the Excel exporter.
        
        Args:
            desktop_path: Path to desktop. If None, attempts to detect automatically.
        """
        if desktop_path is None:
            # Try to detect desktop path
            self.desktop_path = self._detect_desktop_path()
        else:
            self.desktop_path = desktop_path
            
        if not os.path.exists(self.desktop_path):
            raise ValueError(f"Desktop path does not exist: {self.desktop_path}")
    
    def _detect_desktop_path(self) -> str:
        """Detect the desktop path for various systems."""
        # Try common desktop paths
        possible_paths = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            "/mnt/c/Users/" + os.getenv("USER", "Filip") + "/Desktop",
            os.path.join(os.path.expanduser("~"), "Bureau"),  # French
            os.path.join(os.path.expanduser("~"), "Escritorio"),  # Spanish
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Fallback to home directory
        return os.path.expanduser("~")
    
    def _generate_filename(self) -> str:
        """Generate filename with current date."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return f"leads_{current_date}.xlsx"
    
    def export_to_excel(self, posts: List[Dict]) -> str:
        """
        Export posts to Excel file on desktop.
        
        Args:
            posts: List of post dictionaries to export
            
        Returns:
            Path to the created Excel file
        """
        if not posts:
            print("No posts to export")
            return None
        
        # Create DataFrame
        df = pd.DataFrame(posts)
        
        # Generate full file path
        filename = self._generate_filename()
        file_path = os.path.join(self.desktop_path, filename)
        
        # Export to Excel
        df.to_excel(file_path, index=False, engine='openpyxl')
        
        print(f"\n✅ Leads exported to: {file_path}")
        print(f"📊 Total leads exported: {len(posts)}")
        
        return file_path
    
    def filter_and_export_leads(self, posts: List[Dict]) -> str:
        """
        Filter only leads (is_lead=True) and export to Excel.
        
        Args:
            posts: List of post dictionaries (including non-leads)
            
        Returns:
            Path to the created Excel file
        """
        leads = [post for post in posts if post.get("is_lead", False)]
        
        if not leads:
            print("No leads found to export")
            return None
        
        return self.export_to_excel(leads)
