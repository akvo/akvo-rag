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

BASE_LIST_API = "https://tdt.akvotest.org/cms/api/knowledge-hubs"
SAVE_DIR = "./downloads/tdt"
CSV_PATH = "./downloads/tdt/tdt_files.csv"
KB_TITLE = "TDT Library"


def ask_user_mode():
    print("=== TDT Knowledge Import Script ===")
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

    kb_description = input(
        "Enter a description for this Knowledge Base: "
    ).strip()
    return max_pdfs, kb_description


def safe_request_get(url, params=None, max_retries=5, delay=5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params)
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


def collect_pdf_urls(max_pdfs, seen_urls=None):
    print("\n🔍 Collecting PDF URLs...")
    pdf_records = []
    seen_urls = seen_urls or set()
    page = get_last_page_from_csv()
    page_size = 20
    total_pdfs = 0

    while total_pdfs < max_pdfs:
        params = {
            "pagination[page]": page,
            "pagination[pageSize]": page_size,
            "sort[0]": "publication_date:desc",
            "populate[0]": "topic",
            "populate[1]": "regions",
            "populate[2]": "file",
            "populate[3]": "image",
        }

        print(f"Fetching page {page}...")
        r = safe_request_get(BASE_LIST_API, params=params)
        if not r:
            print(f"❌ Skipping page {page} due to failure.")
            page += 1
            continue

        resources = r.json().get("data", [])
        if not resources:
            print("No more resources found.")
            break

        for res in resources:
            file = res.get("file", {})
            title = file.get("name", "document")
            if file and file.get("url", "").lower().endswith(".pdf"):
                pdf_url = file["url"]
                if pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                pdf_records.append((title, pdf_url, page))
                total_pdfs += 1
                if total_pdfs >= max_pdfs:
                    break

        page += 1
        time.sleep(2)

    print(f"\n✅ Collected {total_pdfs} new PDF URLs.")
    return pdf_records


def save_pdfs_to_csv(pdf_records, csv_path=CSV_PATH):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df = pd.DataFrame(pdf_records, columns=["title", "url", "page"])
    df.to_csv(csv_path, index=False)
    print(f"📁 Saved {len(df)} PDF URLs to {csv_path}")


def read_pdfs_from_csv(csv_path=CSV_PATH, limit=None):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)
    return list(df.itertuples(index=False, name=None))


def get_last_page_from_csv(csv_path=CSV_PATH):
    if not os.path.exists(csv_path):
        return 1
    try:
        df = pd.read_csv(csv_path)
        last_page = int(df["page"].max())
        return last_page + 1
    except Exception:
        return 1


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
        yield file_list[i : i + chunk_size]


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

    for title, url, page in pdf_records:
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

    seen_urls = (
        set(existing_df["url"].tolist()) if not existing_df.empty else set()
    )
    pdf_records = collect_pdf_urls(remaining_to_fetch, seen_urls=seen_urls)
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
