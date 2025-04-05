#!/usr/bin/env python3
"""
Document Downloader

This script downloads documents from web portals using a configurable approach.
It supports both sequential and parallel downloading modes.

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
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from tqdm import tqdm
import argparse

# Import configuration
from config import (
    COUNCIL_NAME, BASE_URL, START_URL, DOWNLOAD_DIR, 
    HEADERS, REQUEST_DELAY, MAX_WORKERS, DOCUMENT_TYPE_FILTER
)

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

def create_download_directory():
    """
    Create the download directory if it doesn't exist.
    
    Returns:
        str: The absolute path to the download directory
    """
    # Get the absolute path by joining with the current directory
    abs_download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), DOWNLOAD_DIR)
    
    if not os.path.exists(abs_download_dir):
        os.makedirs(abs_download_dir)
        logger.info(f"Created download directory: {abs_download_dir}")
    
    return abs_download_dir

def get_page_content(url):
    """
    Get the HTML content of a page.
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        str or None: The HTML content of the page, or None if the request failed
    """
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def extract_document_data(html_content):
    """
    Extract document data from the JavaScript model in the HTML.
    
    Args:
        html_content (str): The HTML content of the page
        
    Returns:
        list: A list of document data dictionaries
    """
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
            return model_data['Rows']
        else:
            logger.error("No 'Rows' found in model data")
            return []
    except Exception as e:
        logger.error(f"Error extracting document data: {e}")
        return []

def download_document(guid, doc_ref, download_url_base, download_dir, add_delay=True):
    """
    Download a document using its GUID.
    
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
            jitter = random.uniform(0.8, 1.2)
            time.sleep(REQUEST_DELAY * jitter)
        
        # Make the request
        response = requests.get(url, headers=HEADERS, stream=True)
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

def download_sequential(documents, download_url_base, download_dir):
    """
    Download documents sequentially.
    
    Args:
        documents (list): List of document tuples (guid, doc_ref)
        download_url_base (str): Base URL for downloading
        download_dir (str): Directory to save files to
        
    Returns:
        tuple: (total_downloaded, skipped)
    """
    total_documents = len(documents)
    total_downloaded = 0
    
    for i, (guid, doc_ref) in enumerate(documents, 1):
        logger.info(f"Processing {i}/{total_documents}: {doc_ref}")
        success, _ = download_document(guid, doc_ref, download_url_base, download_dir)
        if success:
            total_downloaded += 1
        
        # Be nice to the server
        time.sleep(REQUEST_DELAY)
    
    return total_downloaded

def download_parallel(documents, download_url_base, download_dir):
    """
    Download documents in parallel.
    
    Args:
        documents (list): List of document tuples (guid, doc_ref)
        download_url_base (str): Base URL for downloading
        download_dir (str): Directory to save files to
        
    Returns:
        tuple: (total_downloaded, failed_downloads)
    """
    total_downloaded = 0
    failed_downloads = []
    
    # Create a partial function with the download_url_base and download_dir parameters already set
    download_func = partial(download_document, download_url_base=download_url_base, download_dir=download_dir)
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all download tasks
        future_to_doc = {
            executor.submit(download_func, guid, doc_ref): (guid, doc_ref) 
            for guid, doc_ref in documents
        }
        
        # Process results as they complete with a progress bar
        with tqdm(total=len(documents), desc="Downloading Documents") as pbar:
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
    
    return total_downloaded, failed_downloads

def main():
    """Main function to run the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download documents from web portals')
    parser.add_argument('--parallel', action='store_true', help='Use parallel downloading')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, help='Number of parallel workers')
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info(f"Starting {COUNCIL_NAME} Document Downloader")
    if args.parallel:
        logger.info(f"Using parallel mode with {args.workers} workers")
    
    # Create download directory and get absolute path
    download_dir = create_download_directory()
    
    # Get the initial page
    logger.info(f"Fetching initial page: {START_URL}")
    html_content = get_page_content(START_URL)
    
    if not html_content:
        logger.error("Failed to retrieve the initial page. Exiting.")
        return
    
    # Extract document data
    all_documents = extract_document_data(html_content)
    logger.info(f"Found {len(all_documents)} documents")
    
    # Download URL base
    download_url_base = f"{BASE_URL}Document/ViewDocument?id="
    
    # Filter for documents matching the filter
    filtered_documents = []
    for doc in all_documents:
        if 'Guid' in doc and 'Doc_Ref2' in doc and DOCUMENT_TYPE_FILTER in doc.get('Doc_Type', ''):
            filtered_documents.append((doc['Guid'], doc['Doc_Ref2']))
    
    logger.info(f"Found {len(filtered_documents)} documents matching filter '{DOCUMENT_TYPE_FILTER}'")
    
    # Download documents
    if args.parallel:
        total_downloaded, failed_downloads = download_parallel(filtered_documents, download_url_base, download_dir)
        
        if failed_downloads:
            logger.warning(f"Failed to download {len(failed_downloads)} files:")
            for doc_ref in failed_downloads:
                logger.warning(f"  - {doc_ref}")
    else:
        total_downloaded = download_sequential(filtered_documents, download_url_base, download_dir)
    
    elapsed_time = time.time() - start_time
    logger.info(f"\nDownload complete! Downloaded {total_downloaded} files to {download_dir}")
    logger.info(f"Total time elapsed: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
