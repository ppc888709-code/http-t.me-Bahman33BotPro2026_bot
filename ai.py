from app.config import settings

async def answer_question(business_name: str, business_description: str, question: str) -> str:
    if not settings.OPENAI_API_KEY:
        return "برای پاسخ دقیق‌تر، درخواست شما برای مدیر ثبت می‌شود. لطفاً از بخش «ثبت درخواست قیمت» استفاده کنید."
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        result = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": (
                    f"شما دستیار رسمی کسب‌وکار «{business_name}» هستید. "
                    f"اطلاعات مجاز: {business_description or 'اطلاعات تکمیلی ثبت نشده است.'}. "
                    "فقط بر اساس اطلاعات داده‌شده پاسخ بده. قیمت، موجودی، زمان تحویل، مجوز یا ضمانت را جعل نکن. "
                    "اگر پاسخ قطعی نداری، بگو مدیر باید بررسی کند. فارسی روان و کوتاه پاسخ بده."
                )},
                {"role": "user", "content": question[:2000]}
            ],
            temperature=0.3,
            max_tokens=450
        )
        return result.choices[0].message.content or "پاسخ آماده نیست؛ مدیر پیگیری می‌کند."
    except Exception:
        return "دستیار هوشمند فعلاً در دسترس نیست. لطفاً درخواستتان را ثبت کنید تا مدیر پیگیری کند."
