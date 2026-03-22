"""
쿠팡파트너스 API 클라이언트
- 상품 검색, 골드박스, 카테고리 베스트, 딥링크 생성
"""

import sys
import os
import json
import hmac
import hashlib
import urllib.parse
from time import gmtime, strftime
from pathlib import Path

import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
BASE_URL = "https://api-gateway.coupang.com"


def generate_auth(method: str, url_path: str, query: str = "") -> str:
    """HMAC-SHA256 인증 헤더 생성"""
    datetime_gmt = strftime("%y%m%dT%H%M%SZ", gmtime())
    message = datetime_gmt + method + url_path + query
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, "
        f"signed-date={datetime_gmt}, signature={signature}"
    )


def api_get(path: str, params: dict = None) -> dict:
    """GET 요청"""
    query = ""
    if params:
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = BASE_URL + path
    if query:
        url += "?" + query
    auth = generate_auth("GET", path, query)
    resp = requests.get(url, headers={"Authorization": auth}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, body: dict) -> dict:
    """POST 요청"""
    auth = generate_auth("POST", path)
    resp = requests.post(
        BASE_URL + path,
        headers={"Authorization": auth, "Content-Type": "application/json"},
        json=body,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── 엔드포인트 ─────────────────────────────────────────

def search(keyword: str, limit: int = 10) -> dict:
    """상품 검색 (주의: 10회/시간 제한)"""
    path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
    return api_get(path, {"keyword": keyword, "limit": limit})


def goldbox() -> dict:
    """골드박스 (핫딜) 조회"""
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/goldbox"
    return api_get(path, {"imageSize": "300x300"})


def best_category(category_id: int, limit: int = 20) -> dict:
    """카테고리별 베스트 상품"""
    path = f"/v2/providers/affiliate_open_api/apis/openapi/products/bestcategories/{category_id}"
    return api_get(path, {"limit": limit, "imageSize": "300x300"})


def deeplink(urls: list[str]) -> dict:
    """쿠팡 URL → 제휴 딥링크 변환"""
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    return api_post(path, {"coupangUrls": urls})


# ── 결과 포맷팅 ────────────────────────────────────────

def format_product(product: dict, index: int = 0) -> str:
    """제품 정보를 보기 좋게 포맷"""
    tags = []
    if product.get("isRocket"):
        tags.append("[로켓배송]")
    if product.get("isFreeShipping"):
        tags.append("[무료배송]")
    tag_str = " ".join(tags)
    price = f"{int(product.get('productPrice', 0)):,}원"
    return (
        f"[{index + 1}] {product.get('productName', 'N/A')}\n"
        f"    가격: {price} {tag_str}\n"
        f"    이미지: {product.get('productImage', 'N/A')}\n"
        f"    링크: {product.get('productUrl', 'N/A')}\n"
    )


def format_results(data: dict | list, source: str = "search") -> str:
    """검색/골드박스 결과를 포맷"""
    if source == "search":
        products = data.get("data", {}).get("productData", [])
    else:
        products = data.get("data", [])

    if not products:
        return "결과 없음"

    lines = [f"총 {len(products)}개 제품\n{'='*60}"]
    for i, p in enumerate(products):
        lines.append(format_product(p, i))
    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python coupang_api.py search <키워드>")
        print("  python coupang_api.py goldbox")
        print("  python coupang_api.py best <카테고리ID>")
        print("  python coupang_api.py deeplink <URL>")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "search":
            keyword = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "생활용품"
            result = search(keyword)
            print(format_results(result, "search"))

        elif command == "goldbox":
            result = goldbox()
            print(format_results(result, "goldbox"))

        elif command == "best":
            cat_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1001
            result = best_category(cat_id)
            print(format_results(result, "best"))

        elif command == "deeplink":
            url = sys.argv[2]
            result = deeplink([url])
            links = result.get("data", [])
            for link in links:
                print(f"원본: {link.get('originalUrl')}")
                print(f"단축: {link.get('shortenUrl')}")

        elif command == "raw":
            # 디버깅용: raw JSON 출력
            sub = sys.argv[2] if len(sys.argv) > 2 else "goldbox"
            if sub == "goldbox":
                result = goldbox()
            else:
                result = search(sub)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:
            print(f"알 수 없는 명령: {command}")
            sys.exit(1)

    except requests.exceptions.HTTPError as e:
        print(f"API 에러: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
