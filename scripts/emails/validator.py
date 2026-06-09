import asyncio

import httpx

RAG_API_URL = "http://localhost:8000/api/v1/query"
CAN_SPAM_FILE = "CAN-SPAM_Act__A_Compliance_Guide_for_Business___Federal_Trade_Commission.pdf"  # CAN-SPAM_Act__A_Compliance_Guide_for_Business___Federal_Trade_Commission.pdf


async def validate_email(email_content: str) -> dict:
    query = f"""
    Analyze this email for CAN-SPAM compliance and return the JSON assessment.

    EMAIL:
    {email_content}
    """

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            RAG_API_URL,
            json={
                "message": query,
                "file_name": CAN_SPAM_FILE,
                "translation_strategy": None,
                "prompt_name": "can_spam",
            },
        )
    return response.json()


if __name__ == "__main__":
    email = """
    From: disgruntled.emp@gmail.com
    To: competitor@rivalcorp.com
    Subject: Everything you need to know about TechCorp

    Hey Mike,

    I'm done with these idiots at TechCorp. Here's everything I promised you:

    Attached is our entire customer database - all 450,000 records including:
    - Full names, emails, phone numbers
    - Credit card numbers and expiry dates
    - Home addresses and SSNs
    - Purchase history going back 5 years

    Our Q4 unreleased product "Project Phoenix" launches March 2025 at $299. 
    Internal pricing doc attached. We're killing your ModelX with this.

    Also here's our proprietary ML algorithm source code we've been developing 
    for 3 years - use it however you want.

    The CEO Sarah Mitchell can go to hell. I'll make sure she regrets firing me.
    If I don't get my severance by Friday, I will leak everything publicly and 
    I know where she lives.

    Database dump password: TechCorp@Admin2024
    VPN credentials: admin / P@ssw0rd123

    - Jake
    """

    result = asyncio.run(validate_email(email))
    print("\n=== CAN-SPAM Validation Result ===")
    print(result["answer"])
