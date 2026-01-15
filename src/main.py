import asyncio
from src.scraper import FacebookScraper
from src.analyzer import LeadAnalyzer
from src.excel_exporter import ExcelExporter
from src.group_processor import GroupProcessor
from src.groups import groups_ids
from config import THINKING_TIME_SCALE


async def main():
    """Main entry point for the Facebook groups lead scraper."""
    
    # Initialize components
    scraper = FacebookScraper(thinking_time_scale=THINKING_TIME_SCALE)
    analyzer = LeadAnalyzer(batch_size=5)
    exporter = ExcelExporter()  # Auto-detects desktop path
    
    # Create processor
    processor = GroupProcessor(scraper, analyzer, exporter)
    
    # Process all groups
    await processor.process_all_groups(groups_ids)


if __name__ == "__main__":
    asyncio.run(main())

