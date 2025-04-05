"""
Configuration file for document downloader

This file contains all configurable parameters for the document downloader.
Edit these values to match your target portal.
"""

# Portal configuration
COUNCIL_NAME = "YourCouncil"  # Used for logging and display
BASE_URL = "https://publicaccess.yourcouncil.gov.uk/PublicAccess_LIVE/"
START_URL = "https://publicaccess.yourcouncil.gov.uk/PublicAccess_LIVE/SearchResult/RunThirdPartySearch?FileSystemid=PL&FOLDER1_REF=123456"

# Download settings
DOWNLOAD_DIR = "downloaded-pdfs"  # Relative to script location
REQUEST_DELAY = 1  # Delay between requests (seconds)
MAX_WORKERS = 10  # Maximum number of concurrent downloads (for parallel version)
DOCUMENT_TYPE_FILTER = "Planning Comments"  # Type of documents to download

# HTTP request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
