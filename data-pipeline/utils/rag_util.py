import os
import requests

RAG_URL = "http://backend:8000/api/"


def request_post(
    endpoint: str, data: dict, headers: dict, use_json: bool = False
):
    url = f"{RAG_URL}{endpoint}"
    try:
        if use_json:
            response = requests.post(url, json=data, headers=headers)
        else:
            response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        return False
    except Exception as e:
        print(f"Request to {url} failed: {e}")
        return False


def rag_login():
    payload = {
        "username": os.getenv("RAG_USERNAME"),
        "password": os.getenv("RAG_PASSWORD")
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    result = request_post("auth/token", payload, headers)
    if result:
        return f"Bearer {result.get('access_token')}"
    return False


def rag_create_knowledge_base(token: str, title: str, description: str):
    payload = {
        "name": title,
        "description": description
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }

    res = request_post("knowledge-base", payload, headers, use_json=True)
    if res:
        return res.get('id', False)
    return False
