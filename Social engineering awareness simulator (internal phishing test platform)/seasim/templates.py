"""Built-in awareness email templates for SeaSim.

These are the simulated phishing emails used in campaigns. Every one is
explicitly educational: no credential capture, no real brands' login
pages, no malware. Each template lists the psychological technique it
demonstrates and the indicators a trained eye should spot - that list is
reused by the JIT training moment after a click.
"""

from __future__ import annotations

from typing import Dict, List

from seasim.engine.models import EmailTemplate, now_iso
from seasim.engine.models import (
    CATEGORY_AI, CATEGORY_CLASSIC, DIFFICULTY_LEVELS, TECHNIQUES,
)


def _tpl(tid: str, name: str, category: str, difficulty: str,
         techniques: List[str], subject: str, body: str,
         indicators: List[str]) -> EmailTemplate:
    return EmailTemplate(
        id=tid, name=name, category=category, difficulty=difficulty,
        techniques=techniques, subject=subject, body=body,
        link_label="Open", phishing_indicators=indicators, builtin=True,
        created=now_iso(), updated=now_iso(),
    )


def builtin_templates() -> List[EmailTemplate]:
    return [
        _tpl(
            "tpl_payroll_update", "Payroll / HR policy update", CATEGORY_CLASSIC,
            "Medium", ["Authority", "Urgency", "Account security"],
            "[Action required] Payroll portal policy update - 48h",
            "Hello {first_name},\n\n"
            "As part of our annual security refresh at {org}, all staff must "
            "re-validate their payroll portal preferences before Friday.\n\n"
            "Open the internal simulation page to continue:\n{link}\n\n"
            "If you take no action, your next payslip may be delayed.\n\n"
            "IT Service Desk",
            [
                "Urgency plus a mild threat ('payslip may be delayed')",
                "Generic greeting instead of your full name",
                "Link points to a simulation page, not the real portal",
            ],
        ),
        _tpl(
            "tpl_ceo_giftcard", "CEO gift-card request", CATEGORY_CLASSIC,
            "High", ["Authority", "Urgency", "Rewards / gift card"],
            "Quick favor - confidential",
            "Hi {first_name},\n\n"
            "I'm boarding a flight and can't talk. Could you help me with a "
            "quick confidential task? I need {org} to send 5 x $100 gift "
            "cards for a client appreciation event today.\n\n"
            "Reply and I'll explain - keep this between us for now.\n\n"
            "Sent from my phone",
            [
                "Executive impersonation via a familiar display name",
                "Secrecy request ('keep this between us')",
                "Pressure to act today, refuses a phone call",
            ],
        ),
        _tpl(
            "tpl_package", "Missed package delivery", CATEGORY_CLASSIC,
            "Low", ["Curiosity", "Fear of loss"],
            "Your package could not be delivered",
            "Hello {first_name},\n\n"
            "A parcel addressed to you at {org} could not be delivered "
            "because no one was available. It will be returned tomorrow "
            "unless you reschedule here:\n{link}\n\n"
            "Delivery reference: SIM-88213\n",
            [
                "Urgency based on loss ('returned tomorrow')",
                "Reference number looks official but is meaningless",
                "Brand-style layout copied from a real carrier",
            ],
        ),
        _tpl(
            "tpl_doc_share", "Shared document notification", CATEGORY_CLASSIC,
            "Medium", ["Curiosity", "Authority", "Account security"],
            "HR: Your review document was shared with you",
            "Hi {first_name},\n\n"
            "A document titled '2026 Performance Review - DRAFT.docx' was "
            "shared with you via the {org} documentation portal.\n\n"
            "Open the internal simulation page to view it:\n{link}\n\n"
            "The link expires in 72 hours.\n\n"
            "HR Document Service (simulated)",
            [
                "Expires-in-72-hours pressure",
                "Fake 'shared with you' workflow imitating a real product",
                "Asks to open an unexpected document",
            ],
        ),
        _tpl(
            "tpl_ai_voicemail", "AI voicemail transcription", CATEGORY_AI,
            "High", ["Curiosity", "AI-themed"],
            "Voicemail transcript (auto) - 'You need to hear this'",
            "Hello {first_name},\n\n"
            "An AI transcription service processed a 23-second voicemail for "
            "your extension at {org}. Transcript excerpt: \"...need you to "
            "confirm the account details today...\"\n\n"
            "Open the internal simulation page to replay it:\n{link}\n\n"
            "You are receiving this because you were mentioned by name.\n",
            [
                "AI-generated lure: transcript mentions you by name",
                "Curiosity gap: 'You need to hear this'",
                "Fake urgency about account details",
                "AI-themed content - verified as required by the consent flow",
            ],
        ),
        _tpl(
            "tpl_ai_recruiting", "AI recruiter outreach", CATEGORY_AI,
            "Medium", ["Curiosity", "Rewards / gift card", "AI-themed"],
            "Exclusive role - AI screening invite",
            "Hi {first_name},\n\n"
            "Our AI recruiter matched your profile to a confidential senior "
            "role. Salary band: $190k-$220k. Only 3 interview slots left "
            "this week.\n\n"
            "Confirm your interest on the internal simulation page:\n{link}\n\n"
            "This invitation is generated by our AI talent system.\n",
            [
                "AI-personalized lure with salary bait",
                "Scarcity ('only 3 slots left')",
                "Refers to a role you never applied for",
            ],
        ),
        _tpl(
            "tpl_invoice", "Overdue invoice", CATEGORY_CLASSIC,
            "Medium", ["Payment / invoice", "Urgency", "Authority"],
            "Invoice #INV-2091 is overdue - final notice",
            "Hello {first_name},\n\n"
            "Our records show invoice INV-2091 for {org} is 30 days "
            "overdue. Late fees apply from tomorrow.\n\n"
            "Open the internal simulation page to review the invoice:\n{link}\n\n"
            "Accounts Receivable",
            [
                "Payment-fraud pattern: fake invoice with late fees",
                "Bank-details change is the classic next step",
                "False authority ('Accounts Receivable')",
            ],
        ),
        _tpl(
            "tpl_it_password", "Password expiring soon", CATEGORY_CLASSIC,
            "Low", ["Account security", "Urgency", "Authority"],
            "Your password expires in 24 hours",
            "Hello {first_name},\n\n"
            "Your {org} account password expires in 24 hours. Use the "
            "internal simulation page to keep your current password:\n{link}\n\n"
            "Security Desk (simulated)\n",
            [
                "Classic credential-phishing pretext - here it only opens "
                "an educational page, nothing is captured",
                "Threat of lockout creates urgency",
                "Sender domain does not match the real IT domain",
            ],
        ),
    ]


def jit_tip(template: EmailTemplate) -> str:
    """One-line coaching tip keyed to the template difficulty."""
    return {
        "Low": "Slow down: no legitimate service punishes you for verifying "
               "a request first.",
        "Medium": "Check the sender's actual address and hover links before "
                  "clicking anything.",
        "High": "Verify unexpected requests via a second channel you choose "
                "yourself - never the one in the email.",
    }.get(template.difficulty, "When in doubt, report the message.")
