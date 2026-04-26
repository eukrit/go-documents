"""Single source of truth for the submission "Acceptance & Response Period" clause.

The clause must appear verbatim in (a) every rendered submission PDF/HTML
document and (b) every submission email body. Both EN and TH render together.

If no written response is received within RESPONSE_DAYS working days of the
email send date, the submission is deemed accepted in full and the contractor
proceeds. Protects GO Corp's schedule when consultants/clients sit on approvals.

Public API:
    RESPONSE_DAYS                          (int, env-configurable)
    acceptance_clause_text(submission)     -> bilingual plain-text block
    acceptance_clause_html(submission)     -> bilingual styled HTML block
"""
from __future__ import annotations

import html
import os

RESPONSE_DAYS = int(os.environ.get("SUBMISSION_RESPONSE_DAYS", "7"))


_EN = (
    "Please review and return this submission with written comments within "
    "{n} working days of the date above. If no written comments or rejection "
    "are received within that period, this submission shall be deemed accepted "
    "in full and the contractor will proceed accordingly."
)

_TH = (
    "กรุณาตรวจสอบและส่งคืนเอกสารฉบับนี้พร้อมความคิดเห็นเป็นลายลักษณ์อักษร"
    "ภายใน {n} วันทำการนับจากวันที่ระบุข้างต้น "
    "หากไม่ได้รับความคิดเห็นหรือการปฏิเสธเป็นลายลักษณ์อักษรภายในระยะเวลาดังกล่าว "
    "ให้ถือว่าเอกสารนี้ได้รับการอนุมัติโดยสมบูรณ์ "
    "และผู้รับเหมาจะดำเนินการตามที่เสนอต่อไป"
)


def _days(submission: dict | None) -> int:
    if submission and isinstance(submission.get("responseDays"), int):
        return submission["responseDays"]
    return RESPONSE_DAYS


def acceptance_clause_text(submission: dict | None = None) -> str:
    """Bilingual plain-text clause for email bodies."""
    n = _days(submission)
    return (
        "Acceptance & Response Period:\n"
        f"{_EN.format(n=n)}\n\n"
        "การยอมรับและระยะเวลาตอบกลับ:\n"
        f"{_TH.format(n=n)}"
    )


def acceptance_clause_html(submission: dict | None = None) -> str:
    """Bilingual HTML block matching the .limitations styling in the templates."""
    n = _days(submission)
    return (
        '<div class="limitations acceptance">\n'
        '  <div class="lim-title">Acceptance &amp; Response Period / '
        'การยอมรับและระยะเวลาตอบกลับ</div>\n'
        f'  <p>{html.escape(_EN.format(n=n))}</p>\n'
        f'  <p lang="th">{html.escape(_TH.format(n=n))}</p>\n'
        '</div>'
    )
