from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.competitor import Competitor
from app.schemas.common import MessageResponse
from app.schemas.competitor import CompetitorOut
from app.services.analytics_service import AnalyticsService
from app.services.brief_generator import WeeklyBriefGenerator
from app.services.ingestion_service import IngestionService
from app.services.meta_client import MetaAdLibraryClient

router = APIRouter()


@router.get("/health", response_model=MessageResponse)
def health() -> MessageResponse:
    return MessageResponse(message="ok")


@router.get("/competitors", response_model=list[CompetitorOut])
def list_competitors(
    mosaic_brand: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CompetitorOut]:
    query = select(Competitor)
    if mosaic_brand:
        query = query.where(Competitor.mosaic_brand == mosaic_brand)
    return db.execute(query.order_by(Competitor.name)).scalars().all()


@router.post("/ingest/run")
def ingest_run(
    mosaic_brand: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    svc = IngestionService(db)
    result = svc.ingest_by_brand(mosaic_brand)
    return {"status": "completed", "result": result, "timestamp": datetime.utcnow().isoformat()}


@router.post("/ingest/non-api-demo")
def ingest_non_api_demo(
    mosaic_brand: str | None = Query(default=None),
    weeks: int = Query(default=6, ge=2, le=26),
    ads_per_week: int = Query(default=5, ge=2, le=20),
    db: Session = Depends(get_db),
) -> dict:
    svc = IngestionService(db)
    result = svc.ingest_non_api_demo(mosaic_brand=mosaic_brand, weeks=weeks, ads_per_week=ads_per_week)
    return {"status": "completed", "mode": "non_api_demo", "ingested_counts": result, "timestamp": datetime.utcnow().isoformat()}


@router.get("/meta/status")
def meta_status() -> dict:
    status = MetaAdLibraryClient().connection_status()
    return {"timestamp": datetime.utcnow().isoformat(), "meta": status}


@router.post("/analytics/recompute")
def recompute_metrics(db: Session = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    upserts = svc.recompute_weekly_metrics()
    return {"status": "completed", "weekly_rows_updated": upserts}


@router.get("/dashboard")
def dashboard(
    mosaic_brand: str | None = Query(default=None),
    competitor: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    creative_format: str | None = Query(default=None),
    message_theme: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(active|inactive|all)$"),
    db: Session = Depends(get_db),
) -> dict:
    svc = AnalyticsService(db)
    active_map = {"active": True, "inactive": False, "all": None, None: None}
    return svc.dashboard_payload(
        mosaic_brand=mosaic_brand,
        competitor_name=competitor,
        start_date=start_date,
        end_date=end_date,
        creative_format=creative_format,
        message_theme=message_theme,
        is_active=active_map[status],
    )


@router.get("/insights/live")
def live_insights(
    mosaic_brand: str | None = Query(default=None),
    competitor: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    creative_format: str | None = Query(default=None),
    message_theme: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(active|inactive|all)$"),
    db: Session = Depends(get_db),
) -> dict:
    svc = AnalyticsService(db)
    active_map = {"active": True, "inactive": False, "all": None, None: None}
    insights = svc.live_actionable_insights(
        mosaic_brand=mosaic_brand,
        competitor_name=competitor,
        start_date=start_date,
        end_date=end_date,
        creative_format=creative_format,
        message_theme=message_theme,
        is_active=active_map[status],
    )
    return {"insights": insights, "generated_at": datetime.utcnow().isoformat()}


@router.get("/weekly-brief/{mosaic_brand}")
def weekly_brief(mosaic_brand: str, db: Session = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    facts = svc.summary_facts_for_brief(mosaic_brand)

    if not facts.get("overview"):
        raise HTTPException(status_code=404, detail="No analytics data available for this brand")

    report = WeeklyBriefGenerator().generate_report(mosaic_brand=mosaic_brand, facts_payload=facts)
    return {
        "mosaic_brand": mosaic_brand,
        "generated_at": datetime.utcnow().isoformat(),
        "brief": report.get("narrative", ""),
        "report": report,
        "facts": facts,
    }


@router.get("/weekly-brief/{mosaic_brand}/pdf")
def weekly_brief_pdf(mosaic_brand: str, db: Session = Depends(get_db)) -> StreamingResponse:
    payload = weekly_brief(mosaic_brand, db)
    report = payload.get("report", {})
    overview = report.get("overview", {})
    highlights = report.get("benchmark_highlights", {})
    shift_alerts = report.get("shift_alerts", [])[:5]
    opportunities = report.get("opportunities", [])[:5]
    actions = report.get("priority_actions", [])[:6]
    narrative = report.get("narrative", payload.get("brief", ""))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"Adalyse Weekly Brief - {mosaic_brand}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#08233B"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#0A3D66"), spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#112A3A"))
    small = ParagraphStyle("small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=colors.HexColor("#34566F"))

    elements = []
    elements.append(Paragraph(report.get("title", f"Adalyse Weekly Competitive Brief - {mosaic_brand.title()}"), h1))
    elements.append(Paragraph(f"Generated: {payload.get('generated_at')} | Brand: {mosaic_brand.title()}", small))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Executive Snapshot", h2))
    overview_table = Table(
        [
            ["Competitors tracked", str(overview.get("total_competitors", 0)), "Active ads", str(overview.get("total_active_ads", 0))],
            ["Video share", f"{overview.get('video_percentage', 0)}%", "UGC share", f"{overview.get('ugc_percentage', 0)}%"],
            ["Average ad age", f"{overview.get('avg_ad_age', 0)} days", "Highest longevity brand", str(overview.get("highest_longevity_brand", "N/A"))],
        ],
        colWidths=[1.6 * inch, 1.5 * inch, 1.6 * inch, 2.2 * inch],
    )
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4FF")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FBFF")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFD7EC")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#143149")),
            ]
        )
    )
    elements.append(overview_table)

    elements.append(Paragraph("Competitive Highlights", h2))
    top_l = highlights.get("highest_longevity_competitor", {}) or {}
    top_e = highlights.get("highest_experimentation_competitor", {}) or {}
    top_s = highlights.get("largest_theme_shift", {}) or {}
    highlights_table = Table(
        [
            ["Highest Longevity", top_l.get("competitor", "N/A"), f"{round(float(top_l.get('longevity_ratio', 0)) * 100, 1)}%"],
            ["Highest Experimentation", top_e.get("competitor", "N/A"), f"{round(float(top_e.get('experimentation_rate', 0)) * 100, 1)}%"],
            ["Largest Theme Shift", top_s.get("theme", "N/A"), f"{top_s.get('deviation', 0)} pts"],
        ],
        colWidths=[1.9 * inch, 2.8 * inch, 2.2 * inch],
    )
    highlights_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FBFF")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5DBEE")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#173A58")),
            ]
        )
    )
    elements.append(highlights_table)

    if shift_alerts:
        elements.append(Paragraph("Messaging Shift Alerts", h2))
        shift_rows = [["Theme", "Direction", "Current", "Baseline", "Deviation", "Severity"]]
        for row in shift_alerts:
            shift_rows.append(
                [
                    str(row.get("theme", "")),
                    str(row.get("direction", "")),
                    f"{row.get('current_percentage', 0)}%",
                    f"{row.get('baseline_percentage', 0)}%",
                    f"{row.get('deviation', 0)}",
                    str(row.get("severity", "watch")).title(),
                ]
            )
        shift_table = Table(shift_rows, colWidths=[1.55 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 0.8 * inch, 1.2 * inch])
        shift_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4FF")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C5DBEE")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#173A58")),
                ]
            )
        )
        elements.append(shift_table)

    if opportunities:
        elements.append(Paragraph("Opportunity Priorities", h2))
        for idx, opp in enumerate(opportunities, start=1):
            opp_line = (
                f"<b>{idx}. {opp.get('type', 'Opportunity')} - {opp.get('name', 'N/A')}</b><br/>"
                f"Usage: {opp.get('usage_percentage', 0)}%<br/>"
                f"{opp.get('insight', '')}<br/>"
                f"<b>Action:</b> {opp.get('action', '')}"
            )
            elements.append(Paragraph(opp_line, body))
            elements.append(Spacer(1, 3))

    elements.append(Paragraph("Priority Actions (Next 7 Days)", h2))
    for idx, action in enumerate(actions, start=1):
        elements.append(Paragraph(f"{idx}. {action}", body))

    elements.append(Paragraph("Executive Narrative", h2))
    elements.append(Paragraph(narrative.replace("\n", "<br/>"), body))
    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=weekly-brief-{mosaic_brand}.pdf"},
    )
