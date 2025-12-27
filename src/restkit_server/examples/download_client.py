"""Example client demonstrating file transfer with a RestKit server.

This module provides examples of:
 - Downloading files via query parameters
 - Downloading files via JSON body
 - Uploading files to the server
 - Error handling for file transfer operations
 - Streaming large file downloads

Usage:
    First, start a server with file transfer capability:
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


def upload_file(base_url: str, file_path: str, custom_filename: str = None) -> bool:
    """
    Upload a file to the server.

    :param base_url: The base URL of the server (e.g., 'http://localhost:5001')
    :param file_path: The local path to the file to upload
    :param custom_filename: Optional custom filename to use on the server
    :return: True if upload was successful, False otherwise
    """
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {}
            if custom_filename:
                data['filename'] = custom_filename

            response = requests.post(
                f"{base_url}/upload",
                files=files,
                data=data if data else None,
                timeout=60
            )

        if response.status_code == 201:
            result = response.json()
            filename = result.get('data', {}).get('filename', 'unknown')
            size = result.get('data', {}).get('size', 0)
            print(f"✅ File uploaded successfully: {filename} ({size} bytes)")
            return True

        error_data = response.json()
        print(f"❌ Upload failed: {error_data.get('data', {}).get('error', 'Unknown error')}")
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


def upload_bytes(base_url: str, content: bytes, filename: str) -> bool:
    """
    Upload bytes content to the server.

    :param base_url: The base URL of the server (e.g., 'http://localhost:5001')
    :param content: The bytes content to upload
    :param filename: The filename to use on the server
    :return: True if upload was successful, False otherwise
    """
    try:
        import io
        files = {'file': (filename, io.BytesIO(content))}

        response = requests.post(
            f"{base_url}/upload",
            files=files,
            timeout=60
        )

        if response.status_code == 201:
            result = response.json()
            size = result.get('data', {}).get('size', 0)
            print(f"✅ Content uploaded successfully: {filename} ({size} bytes)")
            return True

        error_data = response.json()
        print(f"❌ Upload failed: {error_data.get('data', {}).get('error', 'Unknown error')}")
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
    """Demonstrate file transfer functionality."""
    base_url = "http://localhost:5001"

    # Check command line arguments for file path
    if len(sys.argv) > 1:
        file_to_transfer = sys.argv[1]
    else:
        # Default: use this script itself as a demo
        file_to_transfer = os.path.abspath(__file__)

    output_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("RestKit File Transfer Client Example")
    print("=" * 60)
    print(f"\nServer URL: {base_url}")
    print(f"File to transfer: {file_to_transfer}")
    print(f"Output directory: {output_dir}\n")

    # ===== UPLOAD EXAMPLES =====
    print("📤 UPLOAD EXAMPLES")
    print("-" * 40)

    # Example 1: Upload a file
    print("1️⃣  Uploading file...")
    upload_file(base_url, file_to_transfer)

    print()

    # Example 2: Upload with custom filename
    print("2️⃣  Uploading file with custom filename...")
    upload_file(base_url, file_to_transfer, custom_filename="my_custom_file.py")

    print()

    # Example 3: Upload bytes content
    print("3️⃣  Uploading bytes content...")
    upload_bytes(base_url, b"Hello, this is test content!", "test_content.txt")

    print()

    # ===== DOWNLOAD EXAMPLES =====
    print("📥 DOWNLOAD EXAMPLES")
    print("-" * 40)

    # Example 4: Download via query parameter
    print("4️⃣  Downloading via query parameter...")
    output_file = os.path.join(output_dir, "downloaded_via_query.txt")
    download_via_query_param(base_url, file_to_transfer, output_file)

    print()

    # Example 5: Download via JSON body
    print("5️⃣  Downloading via JSON body...")
    output_file = os.path.join(output_dir, "downloaded_via_json.txt")
    download_via_json_body(base_url, file_to_transfer, output_file)

    print()

    # Example 6: Streaming download (for large files)
    print("6️⃣  Downloading via streaming (memory-efficient for large files)...")
    output_file = os.path.join(output_dir, "downloaded_via_stream.txt")
    download_streaming(base_url, file_to_transfer, output_file)

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
