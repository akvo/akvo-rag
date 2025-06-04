import os
import requests
from typing import Optional

RAG_URL = "http://backend:8000/api/"


def request_post(
    endpoint: str,
    data: dict,
    headers: dict,
    use_json: bool = False,
    files: list = None,
    return_status: bool = False,
    method: Optional[str] = "POST",
):
    url = f"{RAG_URL}{endpoint}"
    try:
        request_method = getattr(requests, method.lower())
        if files:
            response = request_method(url, files=files, headers=headers)
        elif use_json:
            response = request_method(url, json=data, headers=headers)
        else:
            response = request_method(url, data=data, headers=headers)

        if response.status_code == 200:
            return (
                (response.status_code, response.json())
                if return_status
                else response.json()
            )

        print(f"[ERROR] POST {url}: {response.status_code} - {response.text}")
        return (response.status_code, None) if return_status else False

    except Exception as e:
        print(f"[Exception] Request to {url} failed: {e}")
        return (None, None) if return_status else False


def rag_register_user(
    create_or_update: bool = False,
    is_super_user: bool = False,
    email: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    payload = {
        "email": email or os.getenv("RAG_EMAIL"),
        "username": username or os.getenv("RAG_USERNAME"),
        "password": password or os.getenv("RAG_PASSWORD"),
        "is_active": True,
        "is_superuser": is_super_user,
    }
    headers = {"Content-Type": "application/json"}
    status, result = request_post(
        "auth/register", payload, headers, use_json=True, return_status=True
    )
    if status == 200 and result:
        print("✅ User registered successfully.")
        return True

    if status == 400 and create_or_update:
        print("⚠️ User already exists. Trying to update user...")
        token = rag_login()
        headers = {"Content-Type": "application/json", "Authorization": token}
        status, result = request_post(
            "auth/user",
            payload,
            headers,
            use_json=True,
            return_status=True,
            method="PUT",
        )
        if status == 200 and result:
            print("✅ User updated successfully.")
            return True
        else:
            print("[ERROR] User update failed.")
            return False

    print(f"[ERROR] User registration failed: {status}")
    return False


def rag_login():
    payload = {
        "username": os.getenv("RAG_USERNAME"),
        "password": os.getenv("RAG_PASSWORD"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    status, result = request_post(
        "auth/token", payload, headers, return_status=True
    )

    if status == 200 and result:
        return f"Bearer {result.get('access_token')}"

    if status == 401:
        print("⚠️ Unauthorized. Trying to register user...")
        if rag_register_user(is_super_user=True):
            # Retry login
            status, result = request_post(
                "auth/token", payload, headers, return_status=True
            )
            if status == 200 and result:
                return f"Bearer {result.get('access_token')}"
            print("[ERROR] Login failed after registration.")

    print(f"[ERROR] Login failed: {status}")
    return False


def rag_create_knowledge_base(token: str, title: str, description: str):
    payload = {"name": title, "description": description}
    headers = {"Content-Type": "application/json", "Authorization": token}
    result = request_post("knowledge-base", payload, headers, use_json=True)
    return result.get("id") if result else False


def rag_upload_documents(token: str, kb_id: int, file_paths: list):
    endpoint = f"knowledge-base/{kb_id}/documents/upload"
    headers = {"Authorization": token}

    files = [
        (
            "files",
            (os.path.basename(path), open(path, "rb"), "application/pdf"),
        )
        for path in file_paths
    ]

    try:
        result = request_post(endpoint, data={}, headers=headers, files=files)
        return result
    finally:
        for f in files:
            f[1][1].close()  # Close file handles


def rag_process_documents(token: str, kb_id: int, upload_results: list):
    endpoint = f"knowledge-base/{kb_id}/documents/process"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    return request_post(endpoint, upload_results, headers, use_json=True)
