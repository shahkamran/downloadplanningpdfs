#!/usr/bin/env python3
"""
Document Downloader

This script downloads documents from web portals using a configurable approach.
It supports both sequential and parallel downloading modes with performance optimizations.

Author: Kamran
Date: April 2025
"""

import os
import time
import requests
import json
import re
import logging
from datetime import datetime
import random
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from tqdm import tqdm
import argparse
import sys
from pathlib import Path

# Import configuration
try:
    from config import (
        COUNCIL_NAME, BASE_URL, START_URL, DOWNLOAD_DIR, 
        HEADERS, REQUEST_DELAY, MAX_WORKERS, DOCUMENT_TYPE_FILTER,
        USE_CACHE, CACHE_FILE, CACHE_EXPIRY, CONNECTION_TIMEOUT,
        RETRY_ATTEMPTS, BATCH_SIZE
    )
except ImportError as e:
    # Handle missing new configuration variables
    from config import (
        COUNCIL_NAME, BASE_URL, START_URL, DOWNLOAD_DIR, 
        HEADERS, REQUEST_DELAY, MAX_WORKERS, DOCUMENT_TYPE_FILTER
    )
    # Set defaults for new config variables
    USE_CACHE = True
    CACHE_FILE = "document_cache.json"
    CACHE_EXPIRY = 3600
    CONNECTION_TIMEOUT = 30
    RETRY_ATTEMPTS = 3
    BATCH_SIZE = 0

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('download_log.txt')
    ]
)
logger = logging.getLogger(__name__)

# Create a session for connection pooling
session = requests.Session()

def create_download_directory():
    """
    Create the download directory if it doesn't exist.
    
    Returns:
        str: The absolute path to the download directory
    """
    start_time = time.time()
    
    # Get the absolute path by joining with the current directory
    abs_download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), DOWNLOAD_DIR)
    
    if not os.path.exists(abs_download_dir):
        os.makedirs(abs_download_dir)
        logger.info(f"Created download directory: {abs_download_dir}")
    
    elapsed = time.time() - start_time
    logger.debug(f"Creating download directory took {elapsed:.2f} seconds")
    
    return abs_download_dir

def get_page_content(url):
    """
    Get the HTML content of a page using connection pooling.
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        str or None: The HTML content of the page, or None if the request failed
    """
    start_time = time.time()
    
    try:
        logger.info(f"Fetching URL: {url}")
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = session.get(url, headers=HEADERS, timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                
                elapsed = time.time() - start_time
                logger.debug(f"Fetching URL took {elapsed:.2f} seconds")
                
                return response.text
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                if attempt < RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt+1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def load_document_cache():
    """
    Load document data from cache if available and not expired.
    
    Returns:
        list or None: Cached document data or None if cache is invalid
    """
    if not USE_CACHE:
        return None
        
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)
    
    if not os.path.exists(cache_path):
        return None
        
    try:
        # Check if cache is expired
        cache_time = os.path.getmtime(cache_path)
        if time.time() - cache_time > CACHE_EXPIRY:
            logger.info(f"Cache expired (older than {CACHE_EXPIRY} seconds)")
            return None
            
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
            
        logger.info(f"Loaded {len(cache_data)} documents from cache")
        return cache_data
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
        return None

def save_document_cache(documents):
    """
    Save document data to cache.
    
    Args:
        documents (list): Document data to cache
    """
    if not USE_CACHE:
        return
        
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(documents, f)
            
        logger.info(f"Saved {len(documents)} documents to cache")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def extract_document_data(html_content):
    """
    Extract document data from the JavaScript model in the HTML.
    
    Args:
        html_content (str): The HTML content of the page
        
    Returns:
        list: A list of document data dictionaries
    """
    start_time = time.time()
    
    try:
        # Find the model JSON data in the JavaScript
        match = re.search(r'var model =(\{.*?\});', html_content, re.DOTALL)
        if not match:
            logger.error("Could not find document data in the page")
            return []
        
        # Extract and parse the JSON
        json_str = match.group(1)
        # Clean up the JSON string if needed
        model_data = json.loads(json_str)
        
        if 'Rows' in model_data:
            rows = model_data['Rows']
            elapsed = time.time() - start_time
            logger.debug(f"Extracting document data took {elapsed:.2f} seconds")
            return rows
        else:
            logger.error("No 'Rows' found in model data")
            return []
    except Exception as e:
        logger.error(f"Error extracting document data: {e}")
        return []

def download_document(guid, doc_ref, download_url_base, download_dir, add_delay=True):
    """
    Download a document using its GUID with retry logic.
    
    Args:
        guid (str): The GUID of the document
        doc_ref (str): The reference of the document
        download_url_base (str): The base URL for downloading
        download_dir (str): The directory to save the file to
        add_delay (bool): Whether to add a delay before downloading
        
    Returns:
        tuple: (bool, str) - Success status and filename
    """
    try:
        # Create a sanitized filename
        filename = sanitize_filename(doc_ref)
        
        # Check if file already exists
        file_path = os.path.join(download_dir, filename)
        
        # Skip if file exists
        if os.path.exists(file_path):
            logger.info(f"File already exists, skipping: {filename}")
            return True, filename
        
        # Construct the download URL
        url = f"{download_url_base}{guid}"
        
        # Add a delay to avoid hammering the server
        if add_delay:
            jitter = random.uniform(0.5, 1.0)
            time.sleep(REQUEST_DELAY * jitter)
        
        # Try multiple times with exponential backoff
        for attempt in range(RETRY_ATTEMPTS):
            try:
                # Make the request using the session
                response = session.get(url, headers=HEADERS, stream=True, timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                
                # Check if it's a PDF
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' not in content_type:
                    logger.warning(f"Warning: {url} might not be a PDF (Content-Type: {content_type})")
                
                # Save the file
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True, filename
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                if attempt < RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt+1} failed for {doc_ref}, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
                    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading document with GUID {guid}: {e}")
        return False, doc_ref
    except Exception as e:
        logger.error(f"Unexpected error downloading document with GUID {guid}: {e}")
        return False, doc_ref

def sanitize_filename(name):
    """
    Create a valid filename from a string.
    
    Args:
        name (str): The original filename
        
    Returns:
        str: A sanitized filename
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name)
    # Limit length and ensure it ends with .pdf
    sanitized = sanitized[:100]  # Limit length
    if not sanitized.lower().endswith('.pdf'):
        sanitized += '.pdf'
    return sanitized

def download_sequential(documents, download_url_base, download_dir, start_idx=0, end_idx=None):
    """
    Download documents sequentially.
    
    Args:
        documents (list): List of document tuples (guid, doc_ref)
        download_url_base (str): Base URL for downloading
        download_dir (str): Directory to save files to
        start_idx (int): Starting index for batch processing
        end_idx (int): Ending index for batch processing
        
    Returns:
        tuple: (total_downloaded, skipped)
    """
    # Apply batch limits if specified
    if end_idx is None:
        end_idx = len(documents)
    
    batch_documents = documents[start_idx:end_idx]
    total_documents = len(batch_documents)
    total_downloaded = 0
    
    # Use tqdm for progress bar
    with tqdm(total=total_documents, desc="Downloading Documents") as pbar:
        for i, (guid, doc_ref) in enumerate(batch_documents, 1):
            logger.info(f"Processing {i}/{total_documents}: {doc_ref}")
            success, _ = download_document(guid, doc_ref, download_url_base, download_dir)
            if success:
                total_downloaded += 1
            
            # Update progress bar
            pbar.update(1)
            pbar.set_postfix(downloaded=total_downloaded)
    
    return total_downloaded

def download_parallel(documents, download_url_base, download_dir, start_idx=0, end_idx=None):
    """
    Download documents in parallel using ThreadPoolExecutor for better performance.
    
    Args:
        documents (list): List of document tuples (guid, doc_ref)
        download_url_base (str): Base URL for downloading
        download_dir (str): Directory to save files to
        start_idx (int): Starting index for batch processing
        end_idx (int): Ending index for batch processing
        
    Returns:
        tuple: (total_downloaded, failed_downloads)
    """
    # Apply batch limits if specified
    if end_idx is None:
        end_idx = len(documents)
    
    batch_documents = documents[start_idx:end_idx]
    total_downloaded = 0
    failed_downloads = []
    
    # Create a partial function with the download_url_base and download_dir parameters already set
    download_func = partial(download_document, download_url_base=download_url_base, download_dir=download_dir)
    
    # Use ThreadPoolExecutor instead of ProcessPoolExecutor for better performance with I/O bound tasks
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all download tasks
        future_to_doc = {
            executor.submit(download_func, guid, doc_ref): (guid, doc_ref) 
            for guid, doc_ref in batch_documents
        }
        
        # Process results as they complete with a progress bar
        with tqdm(total=len(batch_documents), desc="Downloading Documents") as pbar:
            for future in as_completed(future_to_doc):
                guid, doc_ref = future_to_doc[future]
                try:
                    success, filename = future.result()
                    if success:
                        total_downloaded += 1
                        logger.info(f"Downloaded: {filename}")
                    else:
                        failed_downloads.append(doc_ref)
                        logger.error(f"Failed to download: {doc_ref}")
                except Exception as e:
                    failed_downloads.append(doc_ref)
                    logger.error(f"Exception while downloading {doc_ref}: {e}")
                finally:
                    pbar.update(1)
                    pbar.set_postfix(downloaded=total_downloaded)
    
    return total_downloaded, failed_downloads

def main():
    """Main function to run the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download documents from web portals')
    parser.add_argument('--parallel', action='store_true', help='Use parallel downloading')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, help='Number of parallel workers')
    parser.add_argument('--start', type=int, default=0, help='Starting document index')
    parser.add_argument('--end', type=int, default=None, help='Ending document index')
    parser.add_argument('--batch', type=int, default=BATCH_SIZE, help='Batch size (0 for all)')
    parser.add_argument('--no-cache', action='store_true', help='Disable document cache')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Override config with command line arguments
    use_cache = USE_CACHE and not args.no_cache
    batch_size = args.batch if args.batch > 0 else 0
    
    start_time = time.time()
    logger.info(f"Starting {COUNCIL_NAME} Document Downloader")
    if args.parallel:
        logger.info(f"Using parallel mode with {args.workers} workers")
    
    # Create download directory and get absolute path
    download_dir = create_download_directory()
    
    # Try to load from cache first
    all_documents = None
    if use_cache:
        all_documents = load_document_cache()
    
    # If cache is not available or disabled, fetch from the web
    if all_documents is None:
        # Get the initial page
        logger.info(f"Fetching initial page: {START_URL}")
        html_content = get_page_content(START_URL)
        
        if not html_content:
            logger.error("Failed to retrieve the initial page. Exiting.")
            return
        
        # Extract document data
        all_documents = extract_document_data(html_content)
        logger.info(f"Found {len(all_documents)} documents")
        
        # Save to cache if enabled
        if use_cache:
            save_document_cache(all_documents)
    
    # Download URL base
    download_url_base = f"{BASE_URL}Document/ViewDocument?id="
    
    # Filter for documents matching the filter
    filtered_documents = []
    for doc in all_documents:
        if 'Guid' in doc and 'Doc_Ref2' in doc and DOCUMENT_TYPE_FILTER in doc.get('Doc_Type', ''):
            filtered_documents.append((doc['Guid'], doc['Doc_Ref2']))
    
    logger.info(f"Found {len(filtered_documents)} documents matching filter '{DOCUMENT_TYPE_FILTER}'")
    
    # Apply start/end indices
    start_idx = args.start
    end_idx = args.end
    
    # If batch size is specified, calculate end_idx
    if batch_size > 0 and end_idx is None:
        end_idx = min(start_idx + batch_size, len(filtered_documents))
    
    # Log batch information
    if start_idx > 0 or end_idx is not None:
        logger.info(f"Processing batch from index {start_idx} to {end_idx or len(filtered_documents)}")
    
    # Download documents
    if args.parallel:
        total_downloaded, failed_downloads = download_parallel(
            filtered_documents, download_url_base, download_dir, start_idx, end_idx
        )
        
        if failed_downloads:
            logger.warning(f"Failed to download {len(failed_downloads)} files:")
            for doc_ref in failed_downloads:
                logger.warning(f"  - {doc_ref}")
    else:
        total_downloaded = download_sequential(
            filtered_documents, download_url_base, download_dir, start_idx, end_idx
        )
    
    elapsed_time = time.time() - start_time
    logger.info(f"\nDownload complete! Downloaded {total_downloaded} files to {download_dir}")
    logger.info(f"Total time elapsed: {elapsed_time:.2f} seconds")
    
    # Calculate and display performance metrics
    total_processed = end_idx - start_idx if end_idx else len(filtered_documents) - start_idx
    if total_processed > 0 and elapsed_time > 0:
        docs_per_second = total_processed / elapsed_time
        logger.info(f"Performance: {docs_per_second:.2f} documents/second")

if __name__ == "__main__":
    main()
