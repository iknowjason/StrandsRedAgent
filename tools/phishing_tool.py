import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mitre.attack_graph import ATTACK_GRAPH
from memory.campaign_memory import update, get


CAMPAIGN_TEMPLATES = {
    "phishing": [
        {
            "id": "phish_security_update",
            "name": "IT Security Update (Phishing)",
            "mitre_technique": "T1566.001 - Spearphishing Attachment",
            "target_roles": ["IT Director", "System Administrator", "DevOps Engineer"],
            "subject": "Action Required: Critical Security Update for Your Account",
            "html_body": """<html>
<body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #0066cc; color: white; padding: 15px; text-align: center;">
        <h2 style="margin:0;">IT Security Notice</h2>
    </div>
    <div style="padding: 20px; border: 1px solid #ddd;">
        <p>Dear Employee,</p>
        <p>Our security team has detected unusual activity on your account. As part of our ongoing security compliance, we require all employees to verify their credentials within <strong>24 hours</strong>.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{{PHISHING_URL}}" style="background: #0066cc; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px;">Verify Your Account</a>
        </p>
        <p style="font-size: 12px; color: #666;">If you did not request this, please contact the IT Help Desk immediately.</p>
    </div>
    <div style="text-align: center; font-size: 11px; color: #999; padding-top: 10px;">
        {{COMPANY}} Information Security Team
    </div>
</div>
</body>
</html>""",
            "text_body": "Dear Employee,\n\nOur security team has detected unusual activity on your account. Please verify your credentials within 24 hours by visiting: {{PHISHING_URL}}\n\nIf you did not request this, contact IT Help Desk.\n\n{{COMPANY}} Information Security Team",
        },
        {
            "id": "phish_mfa_enrollment",
            "name": "MFA Enrollment Required (Phishing)",
            "mitre_technique": "T1566.002 - Spearphishing Link",
            "target_roles": ["All Employees", "HR Manager", "Finance Manager"],
            "subject": "Mandatory: Complete Multi-Factor Authentication Setup by Friday",
            "html_body": """<html>
<body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #8e44ad; color: white; padding: 15px; text-align: center;">
        <h2 style="margin:0;">MFA Enrollment Required</h2>
    </div>
    <div style="padding: 20px; border: 1px solid #ddd;">
        <p>Hi,</p>
        <p>As part of our new security policy, all employees must enable Multi-Factor Authentication (MFA) on their accounts by <strong>end of day Friday</strong>.</p>
        <ol>
            <li>Click the link below to access the enrollment portal</li>
            <li>Sign in with your corporate credentials</li>
            <li>Follow the on-screen instructions to register your device</li>
        </ol>
        <p style="text-align: center; margin: 25px 0;">
            <a href="{{PHISHING_URL}}" style="background: #8e44ad; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px;">Enroll in MFA Now</a>
        </p>
        <p style="font-size: 12px; color: #999;">Accounts without MFA after the deadline will be temporarily suspended.</p>
    </div>
</div>
</body>
</html>""",
            "text_body": "Hi,\n\nAll employees must enable MFA by end of day Friday.\n\nEnroll here: {{PHISHING_URL}}\n\nAccounts without MFA will be suspended.\n\nIT Security",
        },
    ],
    "credential stuffing": [
        {
            "id": "cred_password_expiry",
            "name": "Password Expiry Warning (Credential Harvesting)",
            "mitre_technique": "T1078 - Valid Accounts via Credential Stuffing",
            "target_roles": ["All Employees"],
            "subject": "Your Password Expires Tomorrow - Update Now",
            "html_body": """<html>
<body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #e74c3c; color: white; padding: 15px; text-align: center;">
        <h2 style="margin:0;">Password Expiration Notice</h2>
    </div>
    <div style="padding: 20px; border: 1px solid #ddd;">
        <p>Hello,</p>
        <p>Your network password is set to expire in <strong>24 hours</strong>. To avoid being locked out, please update your password now through our secure portal.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{{PHISHING_URL}}" style="background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px;">Reset Password</a>
        </p>
        <p>Failure to update may result in loss of access to email, VPN, and internal systems.</p>
        <p style="font-size: 12px; color: #666;">This is an automated message from IT Services.</p>
    </div>
</div>
</body>
</html>""",
            "text_body": "Hello,\n\nYour network password expires in 24 hours. Update it now at: {{PHISHING_URL}}\n\nFailure to update may lock you out of email, VPN, and internal systems.\n\nIT Services",
        },
        {
            "id": "cred_shared_document",
            "name": "Shared Document Lure (Credential Harvesting)",
            "mitre_technique": "T1078 - Valid Accounts via Credential Stuffing",
            "target_roles": ["Finance Manager", "HR Manager", "Executive Assistant"],
            "subject": "Document Shared With You: Q4 Compensation Review",
            "html_body": """<html>
<body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <p><strong>{{SENDER_NAME}}</strong> has shared a document with you:</p>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <strong>Q4 Compensation Review - Confidential</strong><br>
            <span style="font-size: 12px; color: #666;">Spreadsheet - Last modified today</span>
        </div>
        <p style="text-align: center; margin: 25px 0;">
            <a href="{{PHISHING_URL}}" style="background: #1a73e8; color: white; padding: 10px 24px; text-decoration: none; border-radius: 4px;">Open in Drive</a>
        </p>
    </div>
</div>
</body>
</html>""",
            "text_body": "{{SENDER_NAME}} has shared a document with you:\n\nQ4 Compensation Review - Confidential\n\nOpen it here: {{PHISHING_URL}}",
        },
    ],
    "public web exploit": [
        {
            "id": "exploit_invoice",
            "name": "Invoice Payment Request (Watering Hole / Web Exploit)",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "target_roles": ["Accounts Payable", "Finance Manager", "CFO"],
            "subject": "Invoice #INV-2026-4471 - Payment Overdue",
            "html_body": """<html>
<body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #2c3e50; color: white; padding: 15px;">
        <h2 style="margin:0;">Payment Reminder</h2>
    </div>
    <div style="padding: 20px; border: 1px solid #ddd;">
        <p>Dear Accounts Payable,</p>
        <p>This is a reminder that Invoice <strong>#INV-2026-4471</strong> for <strong>$14,750.00</strong> is now overdue.</p>
        <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
            <tr style="background: #f8f8f8;"><td style="padding:8px; border:1px solid #ddd;"><strong>Invoice</strong></td><td style="padding:8px; border:1px solid #ddd;">#INV-2026-4471</td></tr>
            <tr><td style="padding:8px; border:1px solid #ddd;"><strong>Amount</strong></td><td style="padding:8px; border:1px solid #ddd;">$14,750.00</td></tr>
            <tr style="background: #f8f8f8;"><td style="padding:8px; border:1px solid #ddd;"><strong>Due Date</strong></td><td style="padding:8px; border:1px solid #ddd;">March 15, 2026</td></tr>
        </table>
        <p style="text-align: center;">
            <a href="{{PHISHING_URL}}" style="background: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px;">View Invoice & Pay</a>
        </p>
    </div>
</div>
</body>
</html>""",
            "text_body": "Dear Accounts Payable,\n\nInvoice #INV-2026-4471 for $14,750.00 is overdue.\n\nView and pay here: {{PHISHING_URL}}\n\nPlease process promptly.",
        },
    ],
}


def register(mcp):

    @mcp.tool()
    def generate_phishing_campaign(company: str):
        """Generate a phishing campaign plan using MITRE ATT&CK initial access techniques. Produces 5 campaign templates mapped to phishing, credential stuffing, and public web exploit vectors. Stores campaigns in memory for use by ses_send_phishing."""

        print(f"\n[TOOL] generate_phishing_campaign -> {company}\n")

        initial_access_techniques = ATTACK_GRAPH.get("initial_access", [])

        campaigns = []
        for technique in initial_access_techniques:
            templates = CAMPAIGN_TEMPLATES.get(technique, [])
            for t in templates:
                campaigns.append({
                    "id": t["id"],
                    "name": t["name"],
                    "mitre_technique": t["mitre_technique"],
                    "mitre_initial_access": technique,
                    "target_roles": t["target_roles"],
                    "subject": t["subject"],
                })

        # Store in campaign memory so SES tool can retrieve them
        update("social_engineering", "campaigns", campaigns)
        update("social_engineering", "company", company)
        update("social_engineering", "campaign_count", len(campaigns))

        return {
            "company": company,
            "mitre_initial_access_vectors": initial_access_techniques,
            "campaigns": campaigns,
            "total": len(campaigns),
            "next_step": "Ask user for target email, then call ses_send_phishing with the chosen campaign id.",
        }


def get_campaign_template(campaign_id):
    """Look up a full campaign template by ID. Used by ses_phishing."""
    for technique_templates in CAMPAIGN_TEMPLATES.values():
        for t in technique_templates:
            if t["id"] == campaign_id:
                return t
    return None


def get_all_campaign_ids():
    """Return all valid campaign IDs."""
    ids = []
    for technique_templates in CAMPAIGN_TEMPLATES.values():
        for t in technique_templates:
            ids.append(t["id"])
    return ids
