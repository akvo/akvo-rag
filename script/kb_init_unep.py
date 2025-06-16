import requests
import os
import time
import pandas as pd

from utils.rag_util import (
    rag_login,
    rag_create_knowledge_base,
    rag_upload_documents,
    rag_process_documents,
)


# TODO :: implement same logic like collect_pdf_urls in tdt.py
# to avoid lost of pdfs when collect_pdf_urls is meet the max_pdfs
# but in current active page still have more pdfs

BASE_LIST_API = "https://globalplasticshub.org/api/resources"
BASE_DETAIL_API = "https://globalplasticshub.org/api/detail"
SAVE_DIR = "./downloads/unep"
CSV_PATH = "./downloads/unep/unep_files.csv"
KB_TITLE = "UNEP Library"


def ask_user_mode():
    print("=== UNEP Knowledge Import Script ===")
    while True:
        try:
            mode = int(
                input(
                    "Choose mode:\n"
                    "1. Save PDF URLs to CSV only\n"
                    "2. Save CSV and download PDFs\n"
                    "3. Full process (CSV + download + upload to RAG)\n"
                    "Your choice: "
                )
            )
            if mode in [1, 2, 3]:
                break
            else:
                print("Please enter 1, 2, or 3.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    return mode


def ask_user_input():
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


def safe_request_get(url, max_retries=5, delay=5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt} failed for {url}: {e}")
            if attempt < max_retries:
                print(f"⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Max retries reached. Skipping.")
                return None


def fetch_pdf_attachments(resource):
    r_type = resource["type"]
    r_id = resource["id"]
    url = f"{BASE_DETAIL_API}/{r_type}/{r_id}"
    print(f"Fetching detail: {url}")
    r = safe_request_get(url)
    if not r:
        print(f"❌ Failed to fetch detail for resource {resource['id']}")
        return []
    data = r.json()
    attachments = data.get("attachments") or []
    return [
        a
        for a in attachments
        if isinstance(a, str) and a.lower().endswith(".pdf")
    ]


def collect_pdf_urls(max_pdfs):
    print("\n🔍 Collecting PDF URLs...")
    pdf_records = []
    offset = get_last_offset_from_csv()
    limit = 20
    total_pdfs = 0

    while total_pdfs < max_pdfs:
        url = f"{BASE_LIST_API}?incBadges=true&limit={limit}&offset={offset}"
        url += "&orderBy=created&descending=true"
        print(f"Fetching: {url}")
        r = safe_request_get(url)
        if not r:
            print(f"❌ Skipping offset {offset} due to repeated failure.")
            offset += limit
            print(f"➡️ Continue to offset {offset}.")
            continue

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
                pdf_records.append((title, link, offset))
                total_pdfs += 1

        offset += limit
        time.sleep(5)

    print(f"\n✅ Collected {total_pdfs} PDF URLs.")
    return pdf_records


def save_pdfs_to_csv(pdf_records, csv_path=CSV_PATH):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df = pd.DataFrame(pdf_records, columns=["title", "url", "offset"])
    df.to_csv(csv_path, index=False)
    print(f"📁 Saved {len(df)} PDF URLs to {csv_path}")


def read_pdfs_from_csv(csv_path=CSV_PATH, limit=None):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)
    return list(df.itertuples(index=False, name=None))


def get_last_offset_from_csv(csv_path=CSV_PATH, limit=20):
    if not os.path.exists(csv_path):
        return 0
    try:
        df = pd.read_csv(csv_path)
        last_offset = int(df["offset"].max())
        return last_offset + limit
    except Exception:
        return 0


def download_pdf(url, save_dir, title_hint="document"):
    filename = title_hint.replace(" ", "_").replace("/", "_")
    filename += "_" + os.path.basename(url)
    filepath = os.path.join(save_dir, filename)

    if os.path.exists(filepath):
        print(f"✅ Skipped (already exists): {filepath}")
        return filepath

    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        print(f"📥 Downloaded: {filepath}")
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")
        return None


def chunk_files(file_list, chunk_size):
    for i in range(0, len(file_list), chunk_size):
        yield file_list[i : i + chunk_size]  # noqa


def get_pdf_files_from_directory(directory: str):
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".pdf")
    ]


def download_pdfs_from_csv(
    csv_path=CSV_PATH, save_dir=SAVE_DIR, max_files=None
):
    os.makedirs(save_dir, exist_ok=True)
    pdf_records = read_pdfs_from_csv(csv_path, limit=max_files)
    downloaded_files = []

    for title, url, offset in pdf_records:
        filepath = download_pdf(url, save_dir, title_hint=title)
        if filepath:
            downloaded_files.append(filepath)

    print(f"\n✅ Downloaded {len(downloaded_files)} PDFs.")
    return downloaded_files


def upload_and_process_pdfs(pdf_files, token, kb_id):
    chunk_size = 10
    for idx, file_chunk in enumerate(chunk_files(pdf_files, chunk_size), 1):
        print(
            f"\n📦 Uploading chunk {idx} with {len(file_chunk)} documents..."
        )
        upload_results = rag_upload_documents(token, kb_id, file_chunk)

        if upload_results:
            print("⚙️ Processing uploaded documents...")
            time.sleep(5)
            rag_process_documents(token, kb_id, upload_results)
        else:
            print("❌ Skipping processing due to failed upload.")
        time.sleep(5)


def main():
    mode = ask_user_mode()
    max_docs, description = ask_user_input()

    existing_df = (
        pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame()
    )
    existing_count = len(existing_df)
    remaining_to_fetch = max_docs - existing_count

    if remaining_to_fetch <= 0:
        print(f"📄 CSV already contains {existing_count} PDFs.")
        if mode == 1:
            print("🛑 Done. No need to fetch more.")
            return

        pdf_files = download_pdfs_from_csv(max_files=max_docs)

        if mode == 2:
            print("🛑 Done. Files downloaded to local dir.")
            return

        access_token = rag_login()
        if not access_token:
            print("❌ Auth failed to RAG Web UI")
            return

        kb_id = rag_create_knowledge_base(
            token=access_token, title=KB_TITLE, description=description
        )
        if not kb_id:
            print("❌ Failed to create knowledge base.")
            return

        upload_and_process_pdfs(pdf_files[:max_docs], access_token, kb_id)
        print("\n✅ Process uploaded documents success.")
        return

    pdf_records = collect_pdf_urls(remaining_to_fetch)
    save_pdfs_to_csv(existing_df.values.tolist() + pdf_records)

    if mode == 1:
        print("🛑 Done. URLs saved to CSV only.")
        return

    pdf_files = download_pdfs_from_csv(max_files=max_docs)

    if mode == 2:
        print("🛑 Done. Files downloaded to local dir.")
        return

    access_token = rag_login()
    if not access_token:
        print("❌ Auth failed to RAG Web UI")
        return

    kb_id = rag_create_knowledge_base(
        token=access_token, title=KB_TITLE, description=description
    )
    if not kb_id:
        print("❌ Failed to create knowledge base.")
        return

    upload_and_process_pdfs(pdf_files[:max_docs], access_token, kb_id)
    print("\n✅ Process uploaded documents success.")


if __name__ == "__main__":
    main()
