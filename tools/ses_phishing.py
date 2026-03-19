import json
import subprocess
from tools.tool_check import check_binary
from tools.phishing_tool import get_campaign_template, get_all_campaign_ids
from memory.campaign_memory import get


def register(mcp):

    if not check_binary("aws"):
        return

    @mcp.tool()
    def ses_verify_sender(email: str, region: str = "us-east-1"):
        """Verify a sender email address with Amazon SES. The address owner will receive a verification email they must click. Required before sending."""

        print(f"\n[TOOL] ses_verify_sender -> {email} (region={region})\n")

        try:
            result = subprocess.run(
                [
                    "aws", "ses", "verify-email-identity",
                    "--email-address", email,
                    "--region", region,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return {
                    "status": "ok",
                    "email": email,
                    "region": region,
                    "message": f"Verification email sent to {email}. The owner must click the link before it can be used as a sender.",
                }
            else:
                return {
                    "status": "error",
                    "email": email,
                    "stderr": result.stderr[:1000],
                }
        except Exception as exc:
            return {"status": "error", "email": email, "error": str(exc)}

    @mcp.tool()
    def ses_check_sender(email: str, region: str = "us-east-1"):
        """Check if a sender email address is verified in Amazon SES."""

        print(f"\n[TOOL] ses_check_sender -> {email}\n")

        try:
            result = subprocess.run(
                [
                    "aws", "ses", "get-identity-verification-attributes",
                    "--identities", email,
                    "--region", region,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                attrs = data.get("VerificationAttributes", {}).get(email, {})
                status = attrs.get("VerificationStatus", "NotFound")
                return {
                    "email": email,
                    "verified": status == "Success",
                    "verification_status": status,
                }
            else:
                return {"status": "error", "stderr": result.stderr[:1000]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    @mcp.tool()
    def ses_send_phishing(
        campaign_id: str,
        target_email: str,
        sender_email: str,
        company: str = "",
        phishing_url: str = "https://example.com/verify",
        sender_name: str = "IT Security Team",
        region: str = "us-east-1",
    ):
        """Send a phishing email via Amazon SES using a campaign planned by generate_phishing_campaign. The campaign_id must match one of the MITRE-mapped campaigns. Call generate_phishing_campaign first to plan campaigns, then ask the user which campaign and target email to use."""

        print(f"\n[TOOL] ses_send_phishing -> campaign={campaign_id} to={target_email} from={sender_email}\n")

        # Look up the full template from the MITRE-mapped campaigns
        template = get_campaign_template(campaign_id)
        if not template:
            return {
                "status": "error",
                "error": f"Unknown campaign_id: {campaign_id}",
                "available": get_all_campaign_ids(),
                "hint": "Run generate_phishing_campaign first to plan campaigns.",
            }

        # Use company from campaign memory if not provided
        if not company:
            se_data = get("social_engineering")
            company = se_data.get("company", "ACME Corp")

        subject = template["subject"]
        html = template["html_body"]
        text = template["text_body"]

        # Apply customizations
        replacements = {
            "{{COMPANY}}": company,
            "{{PHISHING_URL}}": phishing_url,
            "{{SENDER_NAME}}": sender_name,
        }
        for placeholder, value in replacements.items():
            subject = subject.replace(placeholder, value)
            html = html.replace(placeholder, value)
            text = text.replace(placeholder, value)

        message = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Html": {"Data": html, "Charset": "UTF-8"},
                "Text": {"Data": text, "Charset": "UTF-8"},
            },
        }

        try:
            result = subprocess.run(
                [
                    "aws", "ses", "send-email",
                    "--from", f"{sender_name} <{sender_email}>",
                    "--destination", json.dumps({"ToAddresses": [target_email]}),
                    "--message", json.dumps(message),
                    "--region", region,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "status": "sent",
                    "message_id": data.get("MessageId", "unknown"),
                    "campaign": template["name"],
                    "mitre_technique": template["mitre_technique"],
                    "from": sender_email,
                    "to": target_email,
                    "subject": subject,
                }
            else:
                return {
                    "status": "error",
                    "to": target_email,
                    "stderr": result.stderr[:1000],
                    "hint": "Ensure sender is verified (ses_check_sender) and AWS credentials are configured.",
                }
        except Exception as exc:
            return {"status": "error", "to": target_email, "error": str(exc)}
