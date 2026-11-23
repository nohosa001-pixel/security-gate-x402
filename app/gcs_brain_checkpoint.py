"""
Lightweight Zero-Dependency GCS Brain Checkpoint Helper for A.GRID Sister Systems.
Syncs Brain JSON state to gs://{GCS_BRAIN_BUCKET}/{prefix}/{filename} using Cloud Run's
native GCE metadata OAuth2 token, with graceful local-only fallback outside Cloud Run.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


class GCSBrainCheckpoint:
    def __init__(self, prefix: str, bucket: Optional[str] = None) -> None:
        self.bucket = (bucket if bucket is not None else os.getenv("GCS_BRAIN_BUCKET", "")).strip()
        self.prefix = prefix.strip().strip("/")

    @property
    def persistence_mode(self) -> str:
        return f"GCS_SYNCED (gs://{self.bucket}/{self.prefix})" if self.bucket else "LOCAL_DISK_ONLY"

    def _get_token(self) -> Optional[str]:
        if not self.bucket:
            return None
        try:
            req = urllib.request.Request(_METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8")).get("access_token")
        except Exception:
            pass
        return None

    def save(self, filename: str, data: Dict[str, Any], local_path: Optional[Path] = None) -> bool:
        payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        if local_path is not None:
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(payload)
            except Exception:
                pass

        token = self._get_token()
        if not token:
            return False

        obj_name = f"{self.prefix}/{filename}" if self.prefix else filename
        url = (
            f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o"
            f"?uploadType=media&name={quote(obj_name, safe='')}"
        )
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status in (200, 201)
        except Exception:
            return False

    def load(self, filename: str, local_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        token = self._get_token()
        if token:
            obj_name = f"{self.prefix}/{filename}" if self.prefix else filename
            url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{quote(obj_name, safe='')}?alt=media"
            try:
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if local_path is not None:
                            try:
                                local_path.parent.mkdir(parents=True, exist_ok=True)
                                local_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                            except Exception:
                                pass
                        return data
            except Exception:
                pass

        if local_path is not None and local_path.exists():
            try:
                return json.loads(local_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
