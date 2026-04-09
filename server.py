
import os
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

load_dotenv()

SYSTEM_PROMPT = """You are an AI assistant that writes high-quality vendor outreach emails.

Your task: produce a clear, professional, and concise email from the user's inputs.

Guidelines:
- Write a well-structured email with: Subject line, Greeting, Clear requirement, Deadline mention, Polite closing.
- Tone should be professional by default.
- If an instruction is given (e.g., "make it casual", "shorten it", "make it persuasive"), apply it.
- Keep it concise (100–200 words) unless the instruction asks for a different length.
- Return only the email as plain text. Do not add explanations, preambles, or markdown fences."""

app = FastAPI(title="Email Drafter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class GenerateEmailRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1)
    product_or_service: str = Field(..., min_length=1)
    deadline: str = Field(..., min_length=1)
    instruction: Optional[str] = None
    previous_email: Optional[str] = None


def _build_messages(body: GenerateEmailRequest) -> list[dict[str, str]]:
    prev = (body.previous_email or "").strip()
    instr = (body.instruction or "").strip()

    if prev and instr:
        user_content = (
            f"Refine the following vendor outreach email according to this instruction: {instr}\n\n"
            f"Keep the business context accurate:\n"
            f"- Vendor Name: {body.vendor_name}\n"
            f"- Product/Service: {body.product_or_service}\n"
            f"- Deadline: {body.deadline}\n\n"
            f"Current email:\n{prev}\n\n"
            "Return only the refined plain text email."
        )
    else:
        parts = [
            "Generate a vendor outreach email.\n",
            f"Vendor Name: {body.vendor_name}\n",
            f"Product/Service: {body.product_or_service}\n",
            f"Deadline: {body.deadline}\n",
        ]
        if instr:
            parts.append(f"Instruction: {instr}\n")
        parts.append(
            "\nFollow the system guidelines. Output only the email (subject line + body)."
        )
        user_content = "".join(parts)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


async def _token_stream(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            temperature=0.7,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {e!s}") from e


@app.post("/generate-email")
async def generate_email(body: GenerateEmailRequest):
    messages = _build_messages(body)

    async def stream():
        async for token in _token_stream(messages):
            yield token

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")


@app.get("/health")
async def health():
    return {"ok": True}
