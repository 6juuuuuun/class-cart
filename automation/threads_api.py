"""
Threads API 클라이언트
- 텍스트/이미지/캐러셀 게시, 댓글 작성
- 참고: 이미지는 공개 URL이어야 함 (로컬 파일 직접 업로드 불가)
"""

import sys
import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
BASE_URL = "https://graph.threads.net/v1.0"


def get_user_id() -> str:
    """현재 사용자 ID 조회"""
    resp = requests.get(
        f"{BASE_URL}/me",
        params={"fields": "id,username", "access_token": ACCESS_TOKEN},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"사용자: @{data.get('username')} (ID: {data.get('id')})")
    return data["id"]


def create_text_post(user_id: str, text: str) -> str:
    """텍스트 전용 게시물 생성 및 발행"""
    # 1. 컨테이너 생성
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    print(f"컨테이너 생성: {container_id}")

    # 2. 발행 (30초 대기)
    time.sleep(5)
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"게시 완료! Post ID: {post_id}")
    return post_id


def create_image_post(user_id: str, text: str, image_url: str) -> str:
    """이미지 1장 + 텍스트 게시물"""
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads",
        params={
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    print(f"이미지 컨테이너 생성: {container_id}")

    time.sleep(10)
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"게시 완료! Post ID: {post_id}")
    return post_id


def create_carousel_post(user_id: str, text: str, image_urls: list[str]) -> str:
    """캐러셀 (이미지 여러 장) + 텍스트 게시물"""
    # 1. 각 이미지 아이템 컨테이너 생성
    item_ids = []
    for i, url in enumerate(image_urls):
        resp = requests.post(
            f"{BASE_URL}/{user_id}/threads",
            params={
                "media_type": "IMAGE",
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": ACCESS_TOKEN,
            },
            timeout=10,
        )
        resp.raise_for_status()
        item_id = resp.json()["id"]
        item_ids.append(item_id)
        print(f"  캐러셀 아이템 {i+1}/{len(image_urls)}: {item_id}")

    # 2. 캐러셀 컨테이너 생성
    time.sleep(10)
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads",
        params={
            "media_type": "CAROUSEL",
            "children": ",".join(item_ids),
            "text": text,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    carousel_id = resp.json()["id"]
    print(f"캐러셀 컨테이너: {carousel_id}")

    # 3. 발행
    time.sleep(10)
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads_publish",
        params={
            "creation_id": carousel_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"캐러셀 게시 완료! Post ID: {post_id}")
    return post_id


def reply_to_post(user_id: str, post_id: str, text: str) -> str:
    """게시물에 댓글 달기"""
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": post_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]

    time.sleep(5)
    resp = requests.post(
        f"{BASE_URL}/{user_id}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    reply_id = resp.json()["id"]
    print(f"댓글 작성 완료! Reply ID: {reply_id}")
    return reply_id


def get_post_info(post_id: str) -> dict:
    """게시물 정보 조회"""
    resp = requests.get(
        f"{BASE_URL}/{post_id}",
        params={
            "fields": "id,text,timestamp,permalink",
            "access_token": ACCESS_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── CLI ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python threads_api.py whoami")
        print("  python threads_api.py text '게시할 텍스트'")
        print("  python threads_api.py carousel '텍스트' url1 url2 url3 url4")
        print("  python threads_api.py reply POST_ID '댓글 텍스트'")
        print("  python threads_api.py info POST_ID")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "whoami":
            get_user_id()

        elif command == "text":
            text = sys.argv[2]
            user_id = get_user_id()
            create_text_post(user_id, text)

        elif command == "carousel":
            text = sys.argv[2]
            urls = sys.argv[3:]
            user_id = get_user_id()
            create_carousel_post(user_id, text, urls)

        elif command == "reply":
            post_id = sys.argv[2]
            text = sys.argv[3]
            user_id = get_user_id()
            reply_to_post(user_id, post_id, text)

        elif command == "info":
            post_id = sys.argv[2]
            info = get_post_info(post_id)
            print(json.dumps(info, ensure_ascii=False, indent=2))

        else:
            print(f"알 수 없는 명령: {command}")
            sys.exit(1)

    except requests.exceptions.HTTPError as e:
        print(f"API 에러: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
