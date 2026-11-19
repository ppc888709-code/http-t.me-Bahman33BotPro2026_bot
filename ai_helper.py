from .config import OPENAI_API_KEY, OPENAI_MODEL

async def answer_question(question: str) -> str:
    if not OPENAI_API_KEY:
        return 'پیام شما دریافت شد. برای راهنمایی دقیق‌تر، لطفاً درخواست خود را ثبت کنید تا مدیر پاسخ دهد.'
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        result = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {'role':'system','content':'You are a concise, polite Persian customer-support assistant. Never invent prices, stock, delivery dates, or guarantees. If uncertain, ask the user to submit a request.'},
                {'role':'user','content':question}
            ], temperature=0.3, max_tokens=350)
        return result.choices[0].message.content or 'لطفاً درخواست خود را ثبت کنید.'
    except Exception:
        return 'در حال حاضر پاسخ هوشمند در دسترس نیست. لطفاً درخواست خود را ثبت کنید.'
