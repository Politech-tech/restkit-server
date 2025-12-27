"""Example client demonstrating how to download files from a RestKit server.

This module provides examples of:
 - Downloading files via query parameters
 - Downloading files via JSON body
 - Error handling for download operations
 - Streaming large file downloads

Usage:
    First, start a server with download capability:
        python -m restkit_server.examples.demo_server

    Then run this client:
        python -m restkit_server.examples.download_client
"""

import os
import sys
import requests


def download_via_query_param(base_url: str, file_path: str, output_path: str) -> bool:
    """
    Download a file using query parameter.

    :param base_url: The base URL of the server (e.g., 'http://localhost:5001')
    :param file_path: The path to the file on the server
    :param output_path: The local path where the file will be saved
    :return: True if download was successful, False otherwise
    """
    try:
        response = requests.get(
            f"{base_url}/download",
            params={"path": file_path},
            timeout=30
        )

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ File downloaded successfully to: {output_path}")
            return True

        error_data = response.json()
        print(f"❌ Download failed: {error_data.get('data', {}).get('error', 'Unknown error')}")
        return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {base_url}")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False


def download_via_json_body(base_url: str, file_path: str, output_path: str) -> bool:
    """
    Download a file using JSON body.

    :param base_url: The base URL of the server (e.g., 'http://localhost:5001')
    :param file_path: The path to the file on the server
    :param output_path: The local path where the file will be saved
    :return: True if download was successful, False otherwise
    """
    try:
        response = requests.get(
            f"{base_url}/download",
            json={"path": file_path},
            timeout=30
        )

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ File downloaded successfully to: {output_path}")
            return True

        error_data = response.json()
        print(f"❌ Download failed: {error_data.get('data', {}).get('error', 'Unknown error')}")
        return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {base_url}")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False


def download_streaming(base_url: str, file_path: str, output_path: str, chunk_size: int = 8192) -> bool:
    """
    Download a large file using streaming (memory-efficient).

    :param base_url: The base URL of the server (e.g., 'http://localhost:5001')
    :param file_path: The path to the file on the server
    :param output_path: The local path where the file will be saved
    :param chunk_size: Size of chunks to download at a time (default 8KB)
    :return: True if download was successful, False otherwise
    """
    try:
        with requests.get(
            f"{base_url}/download",
            params={"path": file_path},
            stream=True,
            timeout=30
        ) as response:

            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                print(f"✅ File streamed successfully to: {output_path}")
                return True

            error_data = response.json()
            print(f"❌ Download failed: {error_data.get('data', {}).get('error', 'Unknown error')}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {base_url}")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False


def main():
    """Demonstrate download functionality."""
    base_url = "http://localhost:5001"

    # Check command line arguments for file path
    if len(sys.argv) > 1:
        file_to_download = sys.argv[1]
    else:
        # Default: try to download this script itself as a demo
        file_to_download = os.path.abspath(__file__)

    output_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("RestKit Download Client Example")
    print("=" * 60)
    print(f"\nServer URL: {base_url}")
    print(f"File to download: {file_to_download}")
    print(f"Output directory: {output_dir}\n")

    # Example 1: Download via query parameter
    print("1️⃣  Downloading via query parameter...")
    output_file = os.path.join(output_dir, "downloaded_via_query.txt")
    download_via_query_param(base_url, file_to_download, output_file)

    print()

    # Example 2: Download via JSON body
    print("2️⃣  Downloading via JSON body...")
    output_file = os.path.join(output_dir, "downloaded_via_json.txt")
    download_via_json_body(base_url, file_to_download, output_file)

    print()

    # Example 3: Streaming download (for large files)
    print("3️⃣  Downloading via streaming (memory-efficient for large files)...")
    output_file = os.path.join(output_dir, "downloaded_via_stream.txt")
    download_streaming(base_url, file_to_download, output_file)

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
