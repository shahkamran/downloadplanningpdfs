# Document Downloader

This project contains a script to download documents from local council public access portals or similar web interfaces.

## Features

- Automatically extracts document information from web portals
- Downloads PDF documents based on configurable filters
- Handles file naming and organization
- Provides logging and progress tracking
- Supports both sequential and parallel downloading modes

## Installation

### For Users New to GitHub

1. **Install Python** (if not already installed):
   - Download and install Python from [python.org](https://www.python.org/downloads/) (version 3.6 or higher)
   - During installation, make sure to check "Add Python to PATH"

2. **Get the code**:
   - Option 1: Download as ZIP
     - Go to the GitHub repository page
     - Click the green "Code" button
     - Select "Download ZIP"
     - Extract the ZIP file to a folder on your computer

   - Option 2: Clone with Git (if you have Git installed)
     ```
     git clone https://github.com/username/document-downloader.git
     cd document-downloader
     ```

3. **Install required dependencies**:
   - Open a command prompt or terminal
   - Navigate to the folder containing the code
   - Run:
     ```
     pip install requests beautifulsoup4 tqdm
     ```

## Usage

1. **Configure the settings** in `config.py` for your target portal:
   ```python
   # Portal configuration
   COUNCIL_NAME = "YourCouncil"  # Used for logging and display
   BASE_URL = "https://publicaccess.yourcouncil.gov.uk/PublicAccess_LIVE/"
   START_URL = "https://publicaccess.yourcouncil.gov.uk/PublicAccess_LIVE/SearchResult/RunThirdPartySearch?FileSystemid=PL&FOLDER1_REF=123456"
   ```

2. **Run the script**:
   - Open a command prompt or terminal
   - Navigate to the folder containing the code
   - Run one of the following commands:

   ```
   # Sequential mode (default)
   python downloader.py
   
   # Parallel mode (recommended for speed)
   python downloader.py --parallel
   
   # Parallel mode with custom number of workers
   python downloader.py --parallel --workers 20
   
   # Process documents in batches
   python downloader.py --parallel --batch 100
   
   # Process specific range of documents
   python downloader.py --parallel --start 200 --end 300
   
   # Disable document caching
   python downloader.py --parallel --no-cache
   
   # Enable debug logging
   python downloader.py --parallel --debug
   ```

3. **Find your downloaded files** in the `downloaded-pdfs` directory (configurable in `config.py`)

### Troubleshooting

- If you get a "command not found" error, try using `python3` instead of `python`
- If you get a "module not found" error, make sure you've installed all dependencies with `pip install requests beautifulsoup4 tqdm`
- If the script can't find the configuration file, make sure you're running the script from the directory containing both `downloader.py` and `config.py`

## Configuration

All configuration options are available in `config.py`:

- `COUNCIL_NAME` - The name of the portal (used for logging)
- `BASE_URL` - The base URL of the web portal
- `START_URL` - The starting search URL
- `DOWNLOAD_DIR` - Directory where files will be saved
- `REQUEST_DELAY` - Delay between requests (to be respectful to the server)
- `MAX_WORKERS` - Maximum number of concurrent downloads in parallel mode
- `DOCUMENT_TYPE_FILTER` - The type of documents to download (e.g., "Planning Comments")

### Performance Settings

- `USE_CACHE` - Enable/disable document data caching (default: True)
- `CACHE_FILE` - Name of the cache file (default: "document_cache.json")
- `CACHE_EXPIRY` - Cache expiry time in seconds (default: 3600)
- `CONNECTION_TIMEOUT` - Connection timeout in seconds (default: 30)
- `RETRY_ATTEMPTS` - Number of retry attempts for failed downloads (default: 3)
- `BATCH_SIZE` - Number of documents to process in one batch (default: 0 for all)

## How It Works

The script:
1. Fetches the initial search page
2. Extracts document information from JavaScript data in the page
3. Filters documents based on the configured document type
4. Downloads each document, saving it with a sanitized filename
5. Provides progress information and logs the process

## Notes

- The script is designed to be respectful to servers by including appropriate delays
- Duplicate detection avoids re-downloading files
- Comprehensive logging is provided to track download progress and issues
- The tool is designed to work with portals that use a similar structure

## Important Legal and Privacy Considerations

**Before using this tool, please carefully review the following important considerations:**

### GDPR Compliance
- Ensure your use of this tool complies with the General Data Protection Regulation (GDPR) and other applicable data protection laws
- Only download and process data for legitimate purposes that are permitted by law
- Be aware that planning documents may contain personal data of individuals (names, addresses, contact details)
- Consider whether you need to perform a Data Protection Impact Assessment (DPIA) before bulk downloading documents

### Personal Identifiable Information (PII)
- Documents downloaded may contain PII such as names, addresses, phone numbers, and email addresses
- Implement appropriate technical and organizational measures to protect any PII contained in downloaded documents
- Consider anonymizing or pseudonymizing personal data if you plan to process it further
- Delete any personal data that is not necessary for your legitimate purpose

### Terms of Service
- Review the terms of service of the website you're downloading from to ensure your usage is permitted
- Be aware that automated downloading may be against some websites' terms of service
- Consider reaching out to the data controller (e.g., the local council) to inform them of your intended use

### Data Security
- Store downloaded documents securely with appropriate access controls
- Implement encryption for sensitive data
- Have a data retention policy and delete documents when they are no longer needed
- Document your compliance measures in case you need to demonstrate compliance

### Ethical Considerations
- Just because data is publicly accessible doesn't mean unlimited use is ethical or legal
- Consider the impact of your data processing on individuals whose information may be contained in the documents
- Be transparent about your data processing activities

**The authors of this tool accept no liability for misuse or for any failure to comply with data protection laws. Users are solely responsible for ensuring their use of this tool is lawful.**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Push your branch to your fork
6. Submit a pull request

The project includes a `.gitignore` file that excludes:
- Downloaded documents
- Log files
- Cache files
- IDE-specific files
- OS-specific files (like .DS_Store)
- Virtual environment directories

## License

This project is licensed under the MIT License - see the LICENSE file for details.
