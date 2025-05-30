import os
import io
from dotenv import load_dotenv
import requests
# Load environment variables from .env file (optional, remove if not using .env)
load_dotenv()

# Retrieve Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")


# Validate environment variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")


def upload_file(blob, filename, content_type="application/pdf"):
    try:
        # Construct the upload URL
        project_id = SUPABASE_URL.split('//')[1].split('.')[0]
        upload_url = f"https://{project_id}.supabase.co/storage/v1/object/{BUCKET_NAME}/{filename}"

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",  # Overwrite if file exists
            "Cache-Control": "max-age=3600",  # Cache for 1 hour
        }

        # Upload the blob
        response = requests.put(upload_url, data=blob, headers=headers)

        # Check response
        response.raise_for_status()  # Raise an exception for 4xx/5xx errors

        # Construct the public URL
        public_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{BUCKET_NAME}/{filename}"
        
        # print(f"Blob {filename} uploaded successfully to {BUCKET_NAME}")
        # print(f"Public URL: {public_url}")
        return public_url  # Return the public URL
    except requests.exceptions.RequestException as e:
        print(f"Error uploading blob: {str(e)}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

def get_file(filename):
    """
    Get the public URL for a file in the storage bucket.
    
    Args:
        filename (str): The name of the file in the bucket
        
    Returns:
        str: The public URL of the file
    """
    try:
        # Construct the public URL for the file
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
        
        # Verify the file exists by making a HEAD request
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.head(file_url, headers=headers)
        
        if response.status_code == 404:
            print(f"File {filename} not found in bucket {BUCKET_NAME}")
            return None
            
        return file_url
    except Exception as e:
        print(f"Error getting file URL: {str(e)}")
        return None

# Example usage
# if __name__ == "__main__":
#     # Upload a file
#     print("Uploading file")
#     file_path = "/Users/jcooper/Downloads/Harjeetsinh_Jadeja_Resume.pdf"
    
#     # Read the file contents
#     try:
#         with open(file_path, 'rb') as f:
#             content = f.read()
        
#         # Get just the filename from the path
#         filename = os.path.basename(file_path)
        
#         uploaded_filename = upload_file(content, filename)
#         if uploaded_filename:
#             print(f"Uploaded file: {uploaded_filename}")

#             # Retrieve the file
#             pdf_binary = get_file(uploaded_filename)
#             if pdf_binary:
#                 print(f"Retrieved file size: {len(pdf_binary)} bytes")
#                 # Optionally save the binary to a file
#                 with open("downloaded_example.pdf", "wb") as f:
#                     f.write(pdf_binary)
#                 print("File saved as downloaded_example.pdf")
#     except Exception as e:
#         print(f"Error processing file: {str(e)}")