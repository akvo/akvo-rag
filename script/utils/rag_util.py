import os
import requests

RAG_URL = "http://backend:8000/api/"


def request_post(
    endpoint: str, data: dict, headers: dict,
    use_json: bool = False, files: list = None
):
    url = f"{RAG_URL}{endpoint}"
    try:
        if files:
            response = requests.post(url, files=files, headers=headers)
        elif use_json:
            response = requests.post(url, json=data, headers=headers)
        else:
            response = requests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            return response.json()
        print(f"[ERROR] POST {url}: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"Request to {url} failed: {e}")
        return False


def rag_register_user(is_super_user: bool = False):
    payload = {
        "email": os.getenv("RAG_EMAIL"),
        "username": os.getenv("RAG_USERNAME"),
        "password": os.getenv("RAG_PASSWORD"),
        "is_active": True,
        "is_superuser": is_super_user
    }
    headers = {"Content-Type": "application/json"}
    result = request_post("register", payload, headers, use_json=True)
    if result:
        print("✅ User registered successfully.")
        return True
    return False


def rag_login():
    payload = {
        "username": os.getenv("RAG_USERNAME"),
        "password": os.getenv("RAG_PASSWORD")
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    result = request_post("auth/token", payload, headers)
    if result:
        return f"Bearer {result.get('access_token')}"
    return False


def rag_create_knowledge_base(token: str, title: str, description: str):
    payload = {"name": title, "description": description}
    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }
    res = request_post("knowledge-base", payload, headers, use_json=True)
    return res.get('id') if res else False


def rag_upload_documents(token: str, kb_id: int, file_paths: list):
    endpoint = f"knowledge-base/{kb_id}/documents/upload"
    headers = {"Authorization": token}

    files = [(
        "files", (os.path.basename(path), open(path, "rb"), "application/pdf")
    ) for path in file_paths]

    try:
        result = request_post(endpoint, data={}, headers=headers, files=files)
        return result
    finally:
        for f in files:
            f[1][1].close()  # Close all file handles


def rag_process_documents(token: str, kb_id: int, upload_results: list):
    endpoint = f"knowledge-base/{kb_id}/documents/process"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    return request_post(endpoint, upload_results, headers, use_json=True)
