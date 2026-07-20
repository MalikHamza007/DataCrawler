from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.intelligence.normalization import address_similarity, domain, haversine_meters, name_similarity, normalize_address, normalize_name_matching
from app.intelligence.signals import explanation, signal
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.intelligence import DuplicateCandidate
from app.models.project import Project
from app.models.social_profile import SocialProfile


def generate_pairs(db: Session, entity_type: str, settings: Settings | None = None, lahore_zone: str | None = None) -> tuple[list[tuple[int, int]], int]:
    settings = settings or get_settings(); blocks: dict[str, set[int]] = defaultdict(set)
    model = Developer if entity_type == "developer" else Project
    stmt = select(model).where(model.record_status == "active")
    if entity_type == "project" and lahore_zone: stmt = stmt.where(Project.lahore_zone == lahore_zone)
    records = list(db.scalars(stmt).all())
    for record in records:
        name = normalize_name_matching(record.name)
        significant = [token for token in name.split() if len(token) >= 3]
        if significant: blocks[f"name:{significant[0]}"].add(record.id)
        if len(name) >= 8: blocks[f"prefix:{name[:10]}"].add(record.id)
        website = record.website_url if entity_type == "developer" else record.official_website_url
        if website:
            blocks[f"domain:{domain(website)}"].add(record.id)
        address = record.office_address if entity_type == "developer" else record.address
        if address: blocks[f"address:{normalize_address(address)}"].add(record.id)
        if entity_type == "project":
            if record.google_place_id: blocks[f"place:{record.google_place_id}"].add(record.id)
            if record.latitude is not None and record.longitude is not None: blocks[f"geo:{round(record.latitude, 3)}:{round(record.longitude, 3)}"].add(record.id)
            if record.lahore_zone and significant: blocks[f"zone:{record.lahore_zone.casefold()}:{significant[0]}"].add(record.id)
            if record.developer_id: blocks[f"developer:{record.developer_id}:{significant[0] if significant else ''}"].add(record.id)
    owner_column = Contact.developer_id if entity_type == "developer" else Contact.project_id
    for contact in db.execute(select(owner_column, Contact.normalized_value).where(owner_column.is_not(None))).all():
        if contact[1]: blocks[f"contact:{contact[1]}"].add(contact[0])
    social_owner = SocialProfile.developer_id if entity_type == "developer" else SocialProfile.project_id
    for owner, url in db.execute(select(social_owner, SocialProfile.normalized_url).where(social_owner.is_not(None))).all():
        if url: blocks[f"social:{url}"].add(owner)
    pairs: set[tuple[int, int]] = set()
    limit = settings.developer_duplicate_max_pair_comparisons if entity_type == "developer" else settings.project_duplicate_max_pair_comparisons
    for ids in blocks.values():
        ordered = sorted(ids)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                pairs.add((left, right))
                if len(pairs) > limit: raise ValueError("Duplicate pair comparison limit exceeded")
    return sorted(pairs), len(blocks)


def scan_duplicates(db: Session, entity_type: str, settings: Settings | None = None, lahore_zone: str | None = None, minimum_score: int | None = None, cancellation_check: callable | None = None, progress: callable | None = None) -> dict:
    settings = settings or get_settings(); threshold = minimum_score or settings.duplicate_candidate_threshold
    pairs, block_count = generate_pairs(db, entity_type, settings, lahore_zone); created = updated = preserved = below = 0
    for index, pair in enumerate(pairs, 1):
        if cancellation_check: cancellation_check()
        score, signals = score_pair(db, entity_type, *pair, settings=settings)
        if score < threshold: below += 1; continue
        left_filter = DuplicateCandidate.left_developer_id == pair[0] if entity_type == "developer" else DuplicateCandidate.left_project_id == pair[0]
        right_filter = DuplicateCandidate.right_developer_id == pair[1] if entity_type == "developer" else DuplicateCandidate.right_project_id == pair[1]
        candidate = db.scalar(select(DuplicateCandidate).where(DuplicateCandidate.entity_type == entity_type, left_filter, right_filter, DuplicateCandidate.rule_version == settings.intelligence_rule_version))
        confidence = "high" if score >= settings.duplicate_high_confidence_threshold else "medium" if score >= 65 else "low"
        if candidate:
            if candidate.status != "pending": preserved += 1
            candidate.duplicate_score = score; candidate.confidence_level = confidence; candidate.signals_json = signals; candidate.explanation = explanation(signals); updated += 1
        else:
            kwargs = {"left_developer_id": pair[0], "right_developer_id": pair[1]} if entity_type == "developer" else {"left_project_id": pair[0], "right_project_id": pair[1]}
            db.add(DuplicateCandidate(entity_type=entity_type, duplicate_score=score, confidence_level=confidence, signals_json=signals, explanation=explanation(signals), rule_version=settings.intelligence_rule_version, status="pending", **kwargs)); created += 1
        if progress: progress(phase="comparing", message=f"Comparing duplicate pair {index} of {len(pairs)}", processed_delta=1)
        if created >= settings.duplicate_max_candidates_per_scan: break
    db.commit()
    return {"entity_type": entity_type, "records_scanned": len({item for pair in pairs for item in pair}), "blocks_generated": block_count, "candidate_pairs": len(pairs), "pairs_compared": min(len(pairs), created + updated + below), "candidates_created": created, "candidates_updated": updated, "previous_decisions_preserved": preserved, "pairs_below_threshold": below}


def score_pair(db: Session, entity_type: str, left_id: int, right_id: int, settings: Settings | None = None) -> tuple[int, list[dict]]:
    settings = settings or get_settings(); model = Developer if entity_type == "developer" else Project
    left, right = db.get(model, left_id), db.get(model, right_id)
    if not left or not right: raise ValueError("Duplicate pair record was not found")
    signals = []; similarity = name_similarity(left.name, right.name)
    if similarity >= 95: signals.append(signal("NAME_95", "Names are nearly identical", 35 if entity_type == "developer" else 40, [], similarity=similarity))
    elif similarity >= 90: signals.append(signal("NAME_90", "Names are highly similar", 30 if entity_type == "developer" else 35, [], similarity=similarity))
    elif similarity >= 80: signals.append(signal("NAME_80", "Names are similar", 20, [], similarity=similarity))
    elif similarity >= 70: signals.append(signal("NAME_70", "Names are somewhat similar", 10, [], similarity=similarity))
    website_left = left.website_url if entity_type == "developer" else left.official_website_url; website_right = right.website_url if entity_type == "developer" else right.official_website_url
    if website_left and website_right:
        if domain(website_left) == domain(website_right): signals.append(signal("SAME_DOMAIN", "Records share a registered domain", 45 if entity_type == "developer" else 35, [], domain=domain(website_left)))
        else: signals.append(signal("CONFLICTING_DOMAIN", "Records have different registered domains", -30, []))
    left_contacts = {item.normalized_value for item in db.scalars(select(Contact).where((Contact.developer_id if entity_type == "developer" else Contact.project_id) == left_id)).all() if item.normalized_value}
    right_contacts = {item.normalized_value for item in db.scalars(select(Contact).where((Contact.developer_id if entity_type == "developer" else Contact.project_id) == right_id)).all() if item.normalized_value}
    if left_contacts & right_contacts: signals.append(signal("EXACT_CONTACT", "Records share an exact normalized contact", 45, [], values=sorted(left_contacts & right_contacts)))
    left_socials = {item.normalized_url for item in db.scalars(select(SocialProfile).where((SocialProfile.developer_id if entity_type == "developer" else SocialProfile.project_id) == left_id)).all() if item.normalized_url}
    right_socials = {item.normalized_url for item in db.scalars(select(SocialProfile).where((SocialProfile.developer_id if entity_type == "developer" else SocialProfile.project_id) == right_id)).all() if item.normalized_url}
    if left_socials & right_socials: signals.append(signal("EXACT_SOCIAL", "Records share an official social profile", 45, []))
    left_address = left.office_address if entity_type == "developer" else left.address; right_address = right.office_address if entity_type == "developer" else right.address
    if left_address and right_address:
        address_score = address_similarity(left_address, right_address)
        if normalize_address(left_address) == normalize_address(right_address): signals.append(signal("EXACT_ADDRESS", "Addresses match exactly", 25, [], similarity=100))
        elif address_score >= 85: signals.append(signal("SIMILAR_ADDRESS", "Addresses are highly similar", 15, [], similarity=address_score))
    if entity_type == "developer" and left.legal_name and right.legal_name and normalize_name_matching(left.legal_name) == normalize_name_matching(right.legal_name): signals.append(signal("SAME_LEGAL_NAME", "Legal names match", 40, []))
    if entity_type == "project":
        if left.google_place_id and left.google_place_id == right.google_place_id: signals.append(signal("EXACT_PLACE_ID", "Google Place IDs match", 100, []))
        if left.developer_id and left.developer_id == right.developer_id: signals.append(signal("SAME_DEVELOPER", "Projects share the same developer", 20, []))
        if left.developer_id and right.developer_id and left.developer_id != right.developer_id: signals.append(signal("DIFFERENT_DEVELOPERS", "Projects have different assigned developers", -40, []))
        distance = haversine_meters(left.latitude, left.longitude, right.latitude, right.longitude)
        if distance is not None:
            if distance <= settings.project_duplicate_distance_high_meters: points, code = 30, "VERY_NEAR"
            elif distance <= settings.project_duplicate_distance_medium_meters: points, code = 20, "NEAR"
            elif distance <= settings.project_duplicate_distance_max_meters: points, code = 5, "POSSIBLE_DISTANCE"
            else: points, code = -30, "FAR_APART"
            signals.append(signal(code, "Project coordinate distance", points, [], distance_meters=round(distance, 1)))
        if left.lahore_zone and left.lahore_zone == right.lahore_zone: signals.append(signal("SAME_ZONE", "Projects share a Lahore zone", 5, []))
        if _distinct_phase(left.name, right.name): signals.append(signal("DISTINCT_PHASE", "Names identify different towers, phases or blocks", -40, []))
    return max(0, min(100, sum(item["score"] for item in signals))), signals


def _distinct_phase(left: str, right: str) -> bool:
    import re
    pattern = re.compile(r"\b(?:tower|phase|block)\s*([a-z0-9]+)\b", re.I)
    a, b = pattern.search(left), pattern.search(right)
    return bool(a and b and a.group(1).casefold() != b.group(1).casefold())
