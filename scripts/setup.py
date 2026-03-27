#!/usr/bin/env python3
"""
동행복권 로그인 자격증명 저장
사용법: python3 setup.py
"""
import json, os, getpass
from pathlib import Path

CONFIG_PATH = Path.home() / ".donghae" / "config.json"

def setup():
    print("=== 동행복권 로그인 정보 설정 ===")
    user_id = input("아이디: ").strip()
    user_pw = getpass.getpass("비밀번호: ")

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"id": user_id, "pw": user_pw}, ensure_ascii=False))
    os.chmod(CONFIG_PATH, 0o600)
    print(f"✅ 저장 완료: {CONFIG_PATH}")

if __name__ == "__main__":
    setup()
