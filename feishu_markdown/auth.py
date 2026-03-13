"""飞书应用鉴权模块

通过 app_id 和 app_secret 获取 tenant_access_token，用于后续 API 调用。
"""

import time
from dataclasses import dataclass, field

import requests

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"


@dataclass
class FeishuAuth:
    """管理飞书应用凭证和访问令牌。"""

    app_id: str
    app_secret: str
    _token: str = field(default="", repr=False)
    _token_expire: float = field(default=0.0, repr=False)

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        """返回当前有效的 tenant_access_token，过期时自动刷新。"""
        if not self._token or time.time() >= self._token_expire:
            self._refresh_token()
        return self._token

    @property
    def headers(self) -> dict[str, str]:
        """返回带 Authorization 的请求头。"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _refresh_token(self) -> None:
        """向飞书开放平台申请 tenant_access_token。"""
        resp = requests.post(
            FEISHU_TOKEN_URL,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data.get('msg', 'unknown error')}")
        self._token = data["tenant_access_token"]
        # 提前 60 秒刷新，避免边界过期
        self._token_expire = time.time() + data.get("expire", 7200) - 60
