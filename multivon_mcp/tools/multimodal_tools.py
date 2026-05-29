"""Multimodal MCP tools — VQA faithfulness and document grounding.

Wraps multivon-eval's experimental vision evaluators. These require a
vision-capable judge model (Claude 3.5+, GPT-4o+, or Gemini 1.5+).

Image input is accepted as one of:

- A local filesystem path (``"/path/to/image.png"``).
- An HTTP(S) URL (``"https://example.com/scan.jpg"``).
- A data URI (``"data:image/png;base64,iVBOR..."``).
- A raw base64 string with an explicit ``mime_type`` argument (the
  wrapper assembles the data URI for you).

The multivon-eval evaluators themselves read images from
``case.metadata``; this wrapper handles the marshalling.
"""
from __future__ import annotations

from typing import Any


def register(mcp) -> None:
    """Register multimodal MCP tools on the FastMCP server."""

    @mcp.tool()
    def eval_vqa_faithfulness(
        input: str,
        output: str,
        image: str | None = None,
        image_base64: str | None = None,
        mime_type: str = "image/png",
        judge_model: str = "google:gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Check whether an LLM answer about an image is grounded in what's visible.

        Image-grounded faithfulness. The vision judge extracts up to 3
        factual claims from the answer, then verifies each one against
        the image. Score = fraction of claims that are accurate.

        Use this for visual QA, image captioning, chart/diagram reading,
        and any LLM output that purports to describe an image.

        Image input — exactly one of:
        - ``image``: a local path, http(s) URL, or full data URI.
        - ``image_base64``: raw base64 (no ``data:`` prefix); pair with
          ``mime_type`` (default ``"image/png"``).

        Args:
            input: The question or prompt the LLM was answering.
            output: The LLM-generated answer to verify against the image.
            image: Path / URL / data URI for the image.
            image_base64: Alternative — raw base64 image bytes.
            mime_type: Mime type when using ``image_base64``. Default
                ``"image/png"``. Other common values: ``"image/jpeg"``,
                ``"image/webp"``.
            judge_model: Provider:model for the vision judge. Must be
                vision-capable. Default ``"google:gemini-2.5-flash"``
                (cheap). Other vision-capable options: ``"openai:gpt-4o-mini"``
                or ``"anthropic:claude-sonnet-4-6"`` (not haiku — Haiku 4-5
                is not vision-capable).

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "vqa_faithfulness"}``.
        """
        from multivon_eval import EvalCase, VQAFaithfulness

        img_src = _resolve_image_arg(image, image_base64, mime_type)
        if img_src is None:
            return {
                "error": "must provide either `image` (path/URL/data URI) "
                "or `image_base64` (raw base64 + mime_type).",
            }
        judge = _parse_judge(judge_model)
        evaluator = VQAFaithfulness(judge=judge)
        case = EvalCase(input=input, metadata={"image_url": img_src})
        result = evaluator.evaluate(case, output)
        return _result_dict(result)

    @mcp.tool()
    def eval_document_grounding(
        input: str,
        output: str,
        images: list[str] | None = None,
        images_base64: list[str] | None = None,
        mime_type: str = "image/png",
        judge_model: str = "google:gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Check whether an answer about a multi-page document is grounded.

        Document-page-grounded faithfulness for multi-page document
        agents (contracts, invoices, scientific PDFs, medical records).
        The vision judge answers three yes/no questions per document:
        is every claim supported, no inventions, exceptions handled.

        Provide one image per page. Use exactly one of:
        - ``images``: list of paths, http(s) URLs, or data URIs.
        - ``images_base64``: list of raw base64 strings; pair with ``mime_type``.

        Args:
            input: The question or prompt the LLM was answering about
                the document.
            output: The LLM-generated answer to verify against the pages.
            images: List of page image sources (paths/URLs/data URIs).
            images_base64: Alternative — list of raw base64 strings.
            mime_type: Mime type when using ``images_base64``. Default
                ``"image/png"``.
            judge_model: Provider:model for the vision judge. Must be
                vision-capable. Default ``"google:gemini-2.5-flash"``.

        Returns:
            ``{"score": 0.0-1.0, "passed": bool, "reason": str,
            "threshold": float, "evaluator": "document_grounding"}``.
        """
        from multivon_eval import DocumentGrounding, EvalCase

        sources = _resolve_images_list_arg(images, images_base64, mime_type)
        if not sources:
            return {
                "error": "must provide either `images` (list of paths/URLs/"
                "data URIs) or `images_base64` (list of raw base64 + mime_type).",
            }
        judge = _parse_judge(judge_model)
        evaluator = DocumentGrounding(judge=judge)
        case = EvalCase(input=input, metadata={"images": sources})
        result = evaluator.evaluate(case, output)
        return _result_dict(result)


def _resolve_image_arg(
    image: str | None, image_base64: str | None, mime_type: str
) -> str | None:
    """Return a single image source string suitable for VQA evaluators."""
    if image:
        return image
    if image_base64:
        return f"data:{mime_type};base64,{image_base64}"
    return None


def _resolve_images_list_arg(
    images: list[str] | None,
    images_base64: list[str] | None,
    mime_type: str,
) -> list[str]:
    """Return a list of image source strings for DocumentGrounding."""
    if images:
        return list(images)
    if images_base64:
        return [f"data:{mime_type};base64,{b}" for b in images_base64]
    return []


def _parse_judge(spec: str):
    from multivon_eval import JudgeConfig

    if ":" not in spec:
        raise ValueError(
            f"judge_model must be 'provider:model', got {spec!r}. "
            "Example: google:gemini-2.5-flash"
        )
    provider, model = spec.split(":", 1)
    return JudgeConfig(
        provider=provider.strip().lower(),
        model=model.strip(),
        temperature=0.0,
    )


def _result_dict(result) -> dict[str, Any]:
    return {
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
        "threshold": getattr(result, "threshold", None),
        "evaluator": result.evaluator,
    }
