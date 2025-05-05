import requests
import os
import time

BASE_LIST_API = "https://globalplasticshub.org/api/resources"
BASE_DETAIL_API = "https://globalplasticshub.org/api/detail"
# RAG_WEB_UI_ENDPOINT = "http://localhost:81/api/documents/upload"
SAVE_DIR = ".downloads/unep"


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


def main(max_pdfs, kb_description):
    os.makedirs(SAVE_DIR, exist_ok=True)
    offset = 0
    limit = 20
    total_pdfs = 0

    while total_pdfs < max_pdfs:
        url = f"{BASE_LIST_API}?incBadges=true&limit={limit}&offset={offset}"
        url = f"{url}&orderBy=created&descending=true"
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
                    # PUSH FILE TO RAG HERE
                    total_pdfs += 1
                    print(f"Processed PDF #{total_pdfs}")

        offset += limit
        time.sleep(0.5)

    print(f"\n✅ Imported {total_pdfs} PDF document(s) to the Knowledge Base.")


if __name__ == "__main__":
    max_docs, description = ask_user_input()
    main(max_docs, description)
