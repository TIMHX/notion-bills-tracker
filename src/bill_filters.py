"""Deterministic rules that decide whether an email / extracted bill is recorded.

Card payments (Chase autopay, Citi autopay, "payment received" notices) and
internal transfers are NOT spending: the underlying purchases are already
recorded from per-transaction alerts, so recording the payment double counts.
These checks run without the LLM so they can't be talked out of by a model
that names the merchant "Chase", "Citibank", "CITIBANK, N.A." etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().split())


@dataclass
class SkipRules:
    # Matched (case-insensitive substring) against the email subject — checked
    # BEFORE calling the LLM, so payment notices cost nothing.
    skip_subject_keywords: list[str] = field(default_factory=list)
    # Matched against the extracted merchant name — checked AFTER the LLM.
    exclude_merchants: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: dict) -> "SkipRules":
        return cls(
            skip_subject_keywords=list(cfg.get("skip_subject_keywords") or []),
            exclude_merchants=list(cfg.get("exclude_merchants") or []),
        )

    def subject_skip_reason(self, subject: str | None) -> str | None:
        s = _norm(subject)
        for kw in self.skip_subject_keywords:
            if _norm(kw) in s:
                return f"subject matches '{kw}'"
        return None

    def merchant_skip_reason(self, merchant: str | None) -> str | None:
        m = _norm(merchant)
        for ex in self.exclude_merchants:
            if _norm(ex) in m:
                return f"merchant matches '{ex}'"
        return None


def bill_skip_reason(bill_info, rules: SkipRules) -> str | None:
    """Return a reason string if the extracted bill must not be written."""
    if getattr(bill_info, "is_card_payment_or_transfer", None) is True:
        return "LLM flagged as card payment / internal transfer"
    reason = rules.merchant_skip_reason(bill_info.merchant)
    if reason:
        return reason
    if bill_info.amount is None or abs(bill_info.amount) < 0.005:
        # $0 pre-authorizations / payment reminders without an amount
        return "amount is empty or zero"
    return None


def normalize_sign(bill_info) -> None:
    """Store amounts as positive numbers; direction lives in expense_type.

    Some models return refunds / incoming Zelle as negative 支出. Flip those to
    a positive 收入 so the 支出 views never get negative rows.
    """
    if bill_info.amount is not None and bill_info.amount < 0:
        bill_info.amount = -bill_info.amount
        if bill_info.expense_type in (None, "支出"):
            bill_info.expense_type = "收入"
    if bill_info.expense_type not in ("支出", "收入"):
        bill_info.expense_type = "支出"
