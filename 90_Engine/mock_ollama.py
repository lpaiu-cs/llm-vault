#!/usr/bin/env python3
"""
mock_ollama.py — 테스트용 Ollama 호환 임베딩 서버

실제 ollama serve 대신 워크스페이스에서 결정론적 임베딩을 반환하는 미니 서버.
hash 기반으로 텍스트 유사성을 어느 정도 반영 (동일 텍스트 → 동일 벡터, 유사 텍스트는
일부 차원 공유). 실전 의미 검색 품질은 떨어지지만 파이프라인 가동/SQL/MCP 검증에는 충분.

가동:
    python3 mock_ollama.py --port 11434

실제 Ollama 가동 시 이 파일은 폐기 (사용자는 본인 머신에서 'ollama serve' 사용).
"""

import json
import hashlib
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

EMBED_DIM = 1024  # bge-m3와 동일 차원


def deterministic_embedding(text, dim=EMBED_DIM):
    """텍스트를 결정론적 벡터로 변환.

    동작 방식: SHA256으로 시드를 만들고, 텍스트의 단어 단위 해시를 차원에 분산 누적.
    동일 텍스트 → 동일 벡터. 공통 단어가 많은 텍스트는 유사한 벡터.
    """
    # 토큰화 (한/영 단어 단위)
    import re
    tokens = re.findall(r"[가-힣]+|[a-zA-Z0-9]+", text.lower())

    vec = [0.0] * dim
    for token in tokens:
        h = hashlib.sha256(token.encode("utf-8")).digest()
        # 해시 바이트를 차원에 펼쳐 누적
        for i, b in enumerate(h):
            vec[(i * 7) % dim] += (b - 128) / 128.0
            vec[(i * 13 + 3) % dim] += (b - 128) / 256.0

    # 정규화하지 않음 (indexer가 정규화함)
    return vec


class OllamaHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/api/embed":
            # 새 API: input은 문자열 또는 배열
            inp = payload.get("input", "")
            if isinstance(inp, str):
                texts = [inp]
            else:
                texts = inp
            embeddings = [deterministic_embedding(t) for t in texts]
            response = {
                "model": payload.get("model", "bge-m3"),
                "embeddings": embeddings,
            }
        elif self.path == "/api/embeddings":
            # 구 API: prompt는 단일 문자열
            prompt = payload.get("prompt", "")
            response = {
                "model": payload.get("model", "bge-m3"),
                "embedding": deterministic_embedding(prompt),
            }
        else:
            self.send_error(404, "Not Found")
            return

        body_bytes = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_GET(self):
        if self.path == "/api/tags":
            response = {"models": [{"name": "bge-m3", "size": 2300000000}]}
            body_bytes = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # 노이즈 감소
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), OllamaHandler)
    print(f"[Mock Ollama] http://{args.host}:{args.port} (dim={EMBED_DIM})")
    print(f"[Mock Ollama] Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Mock Ollama] stopped")


if __name__ == "__main__":
    main()
