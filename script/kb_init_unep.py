import requests
import os
import time

from utils.rag_util import (
    rag_login, rag_create_knowledge_base,
    rag_upload_documents, rag_process_documents
)

BASE_LIST_API = "https://globalplasticshub.org/api/resources"
BASE_DETAIL_API = "https://globalplasticshub.org/api/detail"
SAVE_DIR = "./downloads/unep"


def ask_user_input():
    print("=== UNEP Knowledge Import Script ===")
    while True:
        try:
            max_pdfs = int(
                input("How many PDF documents do you want to import? ")
            )
            if max_pdfs > 0:
                break
            else:
                print("Please enter a number greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    kb_description = input("Enter a description for this Knowledge Base: ")
    kb_description = kb_description.strip()
    return max_pdfs, kb_description


def fetch_pdf_attachments(resource):
    r_type = resource["type"]
    r_id = resource["id"]
    url = f"{BASE_DETAIL_API}/{r_type}/{r_id}"
    print(f"Fetching detail: {url}")
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    attachments = data.get("attachments") or []
    return [
        a for a in attachments
        if isinstance(a, str) and a.lower().endswith(".pdf")
    ]


def download_pdf(url, save_dir, title_hint="document"):
    filename = title_hint.replace(" ", "_").replace("/", "_")
    filename += "_" + os.path.basename(url)
    filepath = os.path.join(save_dir, filename)
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {filepath}")
        return filepath
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None


def chunk_files(file_list, chunk_size):
    for i in range(0, len(file_list), chunk_size):
        yield file_list[i:i + chunk_size]


def get_pdf_files_from_directory(directory: str):
    return [os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith(".pdf")]


def main(max_pdfs: int, kb_id: int, token: str):
    os.makedirs(SAVE_DIR, exist_ok=True)
    offset = 0
    limit = 20
    total_pdfs = 0

    while total_pdfs < max_pdfs:
        url = f"{BASE_LIST_API}?incBadges=true&limit={limit}&offset={offset}"
        url += "&orderBy=created&descending=true"
        print(f"\nFetching: {url}")
        r = requests.get(url)
        r.raise_for_status()
        resources = r.json().get("results", [])
        if not resources:
            print("No more resources found.")
            break

        for res in resources:
            title = res.get("title", "document")
            pdf_links = fetch_pdf_attachments(res)
            for link in pdf_links:
                if total_pdfs >= max_pdfs:
                    break
                pdf_path = download_pdf(link, SAVE_DIR, title_hint=title)
                if pdf_path:
                    total_pdfs += 1

        offset += limit
        time.sleep(0.5)

    print(f"\n✅ Downloaded {total_pdfs} PDFs.")

    # Upload per 10 documents
    print("\n📤 Starting upload in chunks...")
    pdf_files = get_pdf_files_from_directory(SAVE_DIR)
    chunk_size = 10

    for idx, file_chunk in enumerate(chunk_files(pdf_files, chunk_size), 1):
        print(f"\n📦 Uploading chunk {idx} with {len(file_chunk)} documents...")
        upload_results = rag_upload_documents(token, kb_id, file_chunk)

        if upload_results:
            print("⚙️ Processing uploaded documents...")
            rag_process_documents(token, kb_id, upload_results)
        else:
            print("❌ Skipping processing due to failed upload.")


if __name__ == "__main__":
    max_docs, description = ask_user_input()

    access_token = rag_login()
    if access_token:
        kb_id = rag_create_knowledge_base(
            token=access_token, title="UNEP Library", description=description
        )
        if kb_id:
            main(max_pdfs=max_docs, kb_id=kb_id, token=access_token)
        else:
            print("❌ Failed to create knowledge base.")
    else:
        print("❌ Auth failed to RAG Web UI")
