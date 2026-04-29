import io
import json
import os
import sys

import requests

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x0f\x9b\xe1"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def parse_map(raw):
    text = str(raw or "").strip()
    if not text:
        return {}
    data = json.loads(text)
    result = {}
    for key, value in (data or {}).items():
        try:
            campus_id = int(key)
        except Exception:
            continue
        if isinstance(value, str):
            upload_url = value.strip()
            write_url = ""
            public_url = ""
        else:
            upload_url = str((value or {}).get("upload_url") or "").strip()
            write_url = str((value or {}).get("write_url") or "").strip()
            public_url = str((value or {}).get("public_url") or "").strip()
        if upload_url:
            result[campus_id] = {
                "upload_url": upload_url.rstrip("/"),
                "write_url": write_url.rstrip("/"),
                "public_url": public_url.rstrip("/"),
            }
    return result


def check_one(campus_id, upload_url, write_url, public_url):
    if upload_url.endswith("/submit"):
        resp = requests.post(
            upload_url,
            files={"file": ("health.png", io.BytesIO(PNG_1X1), "image/png")},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        file_id = str(data.get("fid") or data.get("file_id") or data.get("name") or "").strip()
        if not file_id:
            raise RuntimeError("上传成功但未返回 fid/file_id/name")
        access_url = f"{public_url}/{file_id}" if public_url else ""
        return {"file_id": file_id, "access_url": access_url}

    assign_resp = requests.get(f"{upload_url}/dir/assign", timeout=8)
    assign_resp.raise_for_status()
    assign_data = assign_resp.json() if assign_resp.content else {}
    fid = str(assign_data.get("fid") or "").strip()
    if not fid:
        raise RuntimeError("分配 fid 失败")

    write_candidates = []
    if write_url:
        write_candidates.append(f"{write_url}/{fid}")
    raw_url = str(assign_data.get("url") or "").strip()
    if raw_url:
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            write_candidates.append(f"{raw_url.rstrip('/')}/{fid}")
        else:
            write_candidates.append(f"http://{raw_url.rstrip('/')}/{fid}")
    if public_url:
        write_candidates.append(f"{public_url}/{fid}")

    last_error = None
    for target in write_candidates:
        try:
            write_resp = requests.post(
                target,
                files={"file": ("health.png", io.BytesIO(PNG_1X1), "image/png")},
                timeout=8,
            )
            write_resp.raise_for_status()
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise RuntimeError(f"写入失败: {last_error}")

    access_url = ""
    if public_url:
        access_url = f"{public_url}/{fid}"
    else:
        raw_public = str(assign_data.get("publicUrl") or "").strip()
        if raw_public:
            if raw_public.startswith("http://") or raw_public.startswith("https://"):
                access_url = f"{raw_public.rstrip('/')}/{fid}"
            else:
                access_url = f"http://{raw_public.rstrip('/')}/{fid}"
    return {"file_id": fid, "access_url": access_url}


def main():
    app = create_app()
    with app.app_context():
        campus_map = parse_map(app.config.get("SEAWEEDFS_CAMPUS_CONFIG_MAP"))
        if not campus_map:
            print("[WARN] 未配置 SEAWEEDFS_CAMPUS_CONFIG_MAP")
            return

        all_ok = True
        for campus_id in sorted(campus_map.keys()):
            row = campus_map[campus_id]
            upload_url = row["upload_url"]
            write_url = row.get("write_url", "")
            public_url = row["public_url"]
            try:
                result = check_one(campus_id, upload_url, write_url, public_url)
                print(
                    f"[OK] campus={campus_id} upload_url={upload_url} "
                    f"file_id={result['file_id']} access_url={result['access_url'] or '-'}"
                )
            except Exception as exc:
                all_ok = False
                print(f"[FAIL] campus={campus_id} upload_url={upload_url} error={exc}")

        if not all_ok:
            raise RuntimeError("SeaweedFS 路由检测失败")
        print("[DONE] SeaweedFS 路由检测通过")


if __name__ == "__main__":
    main()
