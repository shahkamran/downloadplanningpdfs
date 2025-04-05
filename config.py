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
REQUEST_DELAY = 0.5  # Delay between requests (seconds)
MAX_WORKERS = 20  # Maximum number of concurrent downloads (for parallel version)
DOCUMENT_TYPE_FILTER = "Planning Comments"  # Type of documents to download

# Performance settings
USE_CACHE = True  # Enable document data caching
CACHE_FILE = "document_cache.json"  # Cache file name
CACHE_EXPIRY = 3600  # Cache expiry in seconds (1 hour)
CONNECTION_TIMEOUT = 30  # Connection timeout in seconds
RETRY_ATTEMPTS = 3  # Number of retry attempts for failed downloads
BATCH_SIZE = 100  # Number of documents to process in one batch (0 for all)


# HTTP request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
