"""Verification-code email — branded HTML + i18n subject/body."""

from __future__ import annotations

import logging
from html import escape

from opencmo.tools.email_send import send_mail

logger = logging.getLogger(__name__)


_SUPPORTED_LOCALES = {"en", "zh", "ja", "ko", "es"}


def _normalize_locale(locale: str) -> str:
    candidate = (locale or "").strip().lower().split("-", 1)[0]
    return candidate if candidate in _SUPPORTED_LOCALES else "en"


# Each entry is (subject, intro paragraph, code label, expiry note, disclaimer).
_COPY: dict[str, dict[str, str]] = {
    "en": {
        "subject": "Your OpenCMO verification code",
        "intro": "Welcome to OpenCMO. Enter the 6-digit code below to verify your email address and finish creating your account.",
        "code_label": "Verification code",
        "expires_in": "This code expires in 10 minutes.",
        "disclaimer": "If you did not request this, you can safely ignore this email.",
        "footer": "OpenCMO - Open-source AI Chief Marketing Officer",
    },
    "zh": {
        "subject": "您的 OpenCMO 验证码",
        "intro": "欢迎使用 OpenCMO。请输入下方 6 位验证码以验证您的邮箱并完成账号注册。",
        "code_label": "验证码",
        "expires_in": "验证码 10 分钟内有效。",
        "disclaimer": "如非本人操作，请忽略此邮件。",
        "footer": "OpenCMO - 开源 AI 首席营销官",
    },
    "ja": {
        "subject": "OpenCMO 認証コード",
        "intro": "OpenCMO へようこそ。アカウント作成を完了するため、下記の 6 桁認証コードを入力してください。",
        "code_label": "認証コード",
        "expires_in": "このコードは 10 分間有効です。",
        "disclaimer": "心当たりがない場合は、このメールを無視してください。",
        "footer": "OpenCMO - オープンソース AI 最高マーケティング責任者",
    },
    "ko": {
        "subject": "OpenCMO 인증 코드",
        "intro": "OpenCMO에 오신 것을 환영합니다. 계정 생성을 완료하려면 아래 6자리 인증 코드를 입력하세요.",
        "code_label": "인증 코드",
        "expires_in": "이 코드는 10분 동안 유효합니다.",
        "disclaimer": "본인이 요청하지 않은 경우 이 이메일을 무시해 주세요.",
        "footer": "OpenCMO - 오픈소스 AI 최고 마케팅 책임자",
    },
    "es": {
        "subject": "Tu codigo de verificacion de OpenCMO",
        "intro": "Bienvenido a OpenCMO. Introduce el codigo de 6 digitos para verificar tu correo y completar el registro.",
        "code_label": "Codigo de verificacion",
        "expires_in": "Este codigo caduca en 10 minutos.",
        "disclaimer": "Si no fuiste tu, puedes ignorar este correo.",
        "footer": "OpenCMO - Director de Marketing con IA de codigo abierto",
    },
}


def _build_html(code: str, copy: dict[str, str]) -> str:
    safe_code = escape(code)
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f7f9;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;padding:32px;">
          <tr>
            <td style="font-size:14px;font-weight:600;color:#64748b;letter-spacing:0.04em;text-transform:uppercase;">OpenCMO</td>
          </tr>
          <tr>
            <td style="padding-top:16px;font-size:22px;font-weight:600;line-height:1.3;">{escape(copy['code_label'])}</td>
          </tr>
          <tr>
            <td style="padding-top:12px;font-size:15px;line-height:1.6;color:#334155;">{escape(copy['intro'])}</td>
          </tr>
          <tr>
            <td align="center" style="padding:28px 0;">
              <div style="display:inline-block;padding:18px 28px;background:#0f172a;color:#ffffff;border-radius:10px;font-family:'SFMono-Regular',Menlo,Consolas,monospace;font-size:32px;letter-spacing:0.4em;font-weight:600;">{safe_code}</div>
            </td>
          </tr>
          <tr>
            <td style="font-size:13px;color:#64748b;">{escape(copy['expires_in'])}</td>
          </tr>
          <tr>
            <td style="padding-top:18px;font-size:12px;color:#94a3b8;line-height:1.6;">{escape(copy['disclaimer'])}</td>
          </tr>
          <tr>
            <td style="padding-top:24px;border-top:1px solid #e2e8f0;margin-top:24px;font-size:11px;color:#94a3b8;">{escape(copy['footer'])}</td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_text(code: str, copy: dict[str, str]) -> str:
    return (
        f"{copy['intro']}\n\n"
        f"{copy['code_label']}: {code}\n\n"
        f"{copy['expires_in']}\n\n"
        f"{copy['disclaimer']}\n"
    )


async def send_verification_code(email: str, code: str, locale: str = "en") -> dict:
    """Email a 6-digit verification code with localized subject and body."""
    copy = _COPY[_normalize_locale(locale)]
    html = _build_html(code, copy)
    text = _build_text(code, copy)
    return await send_mail(email, copy["subject"], html, text)
