"""다이소몰 제품 이미지 다운로드 (Playwright - API 인터셉트)"""
import sys
import os
import re
import json
import time
import requests
from playwright.sync_api import sync_playwright


def search_and_download(keyword: str, output_dir: str, max_results: int = 1):
    """다이소몰에서 키워드 검색 후 제품 이미지 다운로드"""
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        api_responses = []
        image_urls_from_network = []

        def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")

            # API JSON 응답 캡처
            if "application/json" in content_type:
                try:
                    body = response.text()
                    if "/file/DS/" in body or "imgUrl" in body or "pdImgUrl" in body:
                        api_responses.append({"url": url, "body": body[:5000]})
                except:
                    pass

            # 이미지 파일 직접 캡처
            if "/file/DS/" in url:
                image_urls_from_network.append(url)

        page.on("response", handle_response)

        search_url = f"https://www.daisomall.co.kr/ds/search?keyword={keyword}"
        print(f"검색: {keyword}")
        page.goto(search_url, wait_until="networkidle", timeout=45000)
        time.sleep(5)

        # 스크롤해서 lazy load 트리거
        for i in range(3):
            page.evaluate(f"window.scrollTo(0, {(i+1) * 500})")
            time.sleep(2)

        print(f"  캡처된 API 응답: {len(api_responses)}개")
        print(f"  캡처된 이미지 URL: {len(image_urls_from_network)}개")

        # API 응답에서 이미지 URL 추출
        all_image_urls = set(image_urls_from_network)
        for resp_data in api_responses:
            body = resp_data["body"]
            print(f"  API: {resp_data['url'][:80]}")
            # JSON에서 이미지 경로 추출
            found = re.findall(r'/file/DS/[^"\'\s,}]+\.(?:jpg|png|webp|jpeg)', body)
            for f in found:
                full_url = f"https://www.daisomall.co.kr{f}"
                all_image_urls.add(full_url)

        # DOM 체크 (혹시 렌더링된 경우)
        dom_imgs = page.evaluate("""() => {
            const all = [];
            document.querySelectorAll('img').forEach(img => {
                const s = img.src || img.dataset?.src || '';
                if (s) all.push(s);
            });
            // background-image 체크
            document.querySelectorAll('[style*="background"]').forEach(el => {
                const m = el.style.backgroundImage.match(/url\\(['"]?(.+?)['"]?\\)/);
                if (m) all.push(m[1]);
            });
            return all;
        }""")
        for src in dom_imgs:
            if "/file/DS/" in src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://www.daisomall.co.kr" + src
                all_image_urls.add(src)

        print(f"  DOM 이미지: {len(dom_imgs)}개")
        print(f"  총 고유 이미지: {len(all_image_urls)}개")

        if all_image_urls:
            for url in list(all_image_urls)[:5]:
                print(f"    - {url[:100]}")

        # 다운로드
        downloaded = []
        for i, src in enumerate(sorted(all_image_urls)[:max_results]):
            safe_kw = re.sub(r'[^\w가-힣]', '_', keyword)
            filename = f"{safe_kw}_{i+1}.jpg"
            filepath = os.path.join(output_dir, filename)
            try:
                resp = requests.get(src, timeout=10, headers={
                    "Referer": "https://www.daisomall.co.kr/",
                    "User-Agent": "Mozilla/5.0"
                })
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"  다운로드: {filename} ({len(resp.content)//1024}KB)")
                downloaded.append(filepath)
            except Exception as e:
                print(f"  실패: {e}")

        if not all_image_urls:
            print("\n  [디버그] 페이지 HTML 일부:")
            html = page.content()
            # 검색 결과 영역 찾기
            if "검색 결과" in html or "search" in html.lower():
                print("  검색 결과 페이지 로드됨")
            print(f"  HTML 길이: {len(html)}")
            # file/DS 패턴 재검색
            all_file = re.findall(r'/file/DS/[^\s"\'<>]+', html)
            print(f"  HTML 내 /file/DS/ 패턴: {len(all_file)}개")
            for u in all_file[:5]:
                print(f"    - {u[:100]}")

        browser.close()
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python daiso_image.py '키워드' ['출력폴더']")
        sys.exit(1)

    keyword = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "."
    search_and_download(keyword, output)
