from __future__ import annotations

import json
from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings


class AdClassification(BaseModel):
    creative_format: str
    message_theme: str
    funnel_stage: str
    emotional_tone: str


ALLOWED_CREATIVE_FORMATS = {"UGC", "Studio", "Doctor-backed", "Influencer", "Meme-style", "Product demo"}
ALLOWED_MESSAGE_THEMES = {
    "Authority",
    "Social proof",
    "Problem agitation",
    "Discount push",
    "Subscription",
    "Ingredient science",
    "Transformation",
    "Community storytelling",
}
ALLOWED_FUNNEL_STAGES = {"Awareness", "Consideration", "Conversion"}
ALLOWED_EMOTIONAL_TONES = {"Fear", "Aspiration", "Urgency", "Trust", "Empowerment"}


class AIClassifier:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def classify_ad(self, ad_text: str, headline: str, cta: str, media_type: str) -> AdClassification:
        if not self.client:
            return self._fallback(ad_text, headline, cta, media_type)

        prompt = f"""
        Classify the following ad and return ONLY valid JSON with keys:
        creative_format, message_theme, funnel_stage, emotional_tone.

        Allowed creative_format: {sorted(ALLOWED_CREATIVE_FORMATS)}
        Allowed message_theme: {sorted(ALLOWED_MESSAGE_THEMES)}
        Allowed funnel_stage: {sorted(ALLOWED_FUNNEL_STAGES)}
        Allowed emotional_tone: {sorted(ALLOWED_EMOTIONAL_TONES)}

        ad_text: {ad_text}
        headline: {headline}
        cta: {cta}
        media_type: {media_type}
        """.strip()

        completion = self.client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a strict ad taxonomy classifier."},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content or "{}"

        try:
            parsed = json.loads(content)
            result = AdClassification.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError("Invalid classification JSON") from exc

        self._validate_enum(result)
        return result

    @staticmethod
    def _validate_enum(result: AdClassification) -> None:
        if result.creative_format not in ALLOWED_CREATIVE_FORMATS:
            raise ValueError("Invalid creative_format")
        if result.message_theme not in ALLOWED_MESSAGE_THEMES:
            raise ValueError("Invalid message_theme")
        if result.funnel_stage not in ALLOWED_FUNNEL_STAGES:
            raise ValueError("Invalid funnel_stage")
        if result.emotional_tone not in ALLOWED_EMOTIONAL_TONES:
            raise ValueError("Invalid emotional_tone")

    @staticmethod
    def _fallback(ad_text: str, headline: str, cta: str, media_type: str) -> AdClassification:
        combined = f"{ad_text} {headline} {cta}".lower()
        if "doctor" in combined or "dermat" in combined:
            creative_format = "Doctor-backed"
        elif "creator" in combined or "influenc" in combined:
            creative_format = "Influencer"
        elif "meme" in combined:
            creative_format = "Meme-style"
        elif media_type == "video":
            creative_format = "UGC"
        elif "demo" in combined:
            creative_format = "Product demo"
        else:
            creative_format = "Studio"

        if "discount" in combined or "offer" in combined or "off" in combined:
            message_theme = "Discount push"
        elif "ingredient" in combined or "science" in combined:
            message_theme = "Ingredient science"
        elif "review" in combined or "testimonial" in combined:
            message_theme = "Social proof"
        elif "community" in combined:
            message_theme = "Community storytelling"
        elif "before" in combined and "after" in combined:
            message_theme = "Transformation"
        elif "subscribe" in combined:
            message_theme = "Subscription"
        elif "problem" in combined or "struggle" in combined:
            message_theme = "Problem agitation"
        else:
            message_theme = "Authority"

        if "buy" in combined or "shop" in combined or "order" in combined:
            funnel_stage = "Conversion"
        elif "learn" in combined or "discover" in combined:
            funnel_stage = "Consideration"
        else:
            funnel_stage = "Awareness"

        if "urgent" in combined or "today" in combined:
            emotional_tone = "Urgency"
        elif "trust" in combined or "safe" in combined:
            emotional_tone = "Trust"
        elif "fear" in combined or "damage" in combined:
            emotional_tone = "Fear"
        elif "empower" in combined or "control" in combined:
            emotional_tone = "Empowerment"
        else:
            emotional_tone = "Aspiration"

        return AdClassification(
            creative_format=creative_format,
            message_theme=message_theme,
            funnel_stage=funnel_stage,
            emotional_tone=emotional_tone,
        )


def now_utc() -> datetime:
    return datetime.utcnow()
