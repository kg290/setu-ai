"""Eligibility matching engine - compares user profile against scheme requirements."""
import json
from datetime import datetime
from app.models import UserProfile, SchemeInfo, EligibilityResult
from app.database import get_db_connection


def get_all_schemes() -> list[SchemeInfo]:
    """Fetch all schemes from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes")
    rows = cursor.fetchall()
    conn.close()

    schemes = []
    for row in rows:
        schemes.append(SchemeInfo(
            id=row["id"],
            name=row["name"],
            name_hi=row["name_hi"],
            description=row["description"],
            description_hi=row["description_hi"],
            ministry=row["ministry"],
            category=row["category"],
            min_age=row["min_age"],
            max_age=row["max_age"],
            max_income=row["max_income"],
            eligible_categories=row["eligible_categories"],
            eligible_genders=row["eligible_genders"],
            eligible_states=row["eligible_states"],
            required_documents=row["required_documents"],
            benefits=row["benefits"],
            form_fields=row["form_fields"],
        ))
    return schemes


def get_scheme_by_id(scheme_id: int) -> SchemeInfo | None:
    """Fetch a single scheme by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return SchemeInfo(
        id=row["id"],
        name=row["name"],
        name_hi=row["name_hi"],
        description=row["description"],
        description_hi=row["description_hi"],
        ministry=row["ministry"],
        category=row["category"],
        min_age=row["min_age"],
        max_age=row["max_age"],
        max_income=row["max_income"],
        eligible_categories=row["eligible_categories"],
        eligible_genders=row["eligible_genders"],
        eligible_states=row["eligible_states"],
        required_documents=row["required_documents"],
        benefits=row["benefits"],
        form_fields=row["form_fields"],
    )


def calculate_age(dob_str: str) -> int | None:
    """Calculate age from DOB string (DD/MM/YYYY or DD-MM-YYYY)."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            dob = datetime.strptime(dob_str, fmt)
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except ValueError:
            continue
    return None


def check_eligibility(profile: UserProfile, scheme: SchemeInfo) -> EligibilityResult:
    """Check if a user profile is eligible for a given scheme."""
    reasons = []
    missing_info = []
    checks_passed = 0
    total_checks = 0

    # Age check
    if scheme.min_age is not None or scheme.max_age is not None:
        total_checks += 1
        age = profile.age
        if age is None and profile.date_of_birth:
            age = calculate_age(profile.date_of_birth)

        if age is not None:
            if scheme.min_age and age < scheme.min_age:
                reasons.append(f"Age {age} is below minimum {scheme.min_age}")
            elif scheme.max_age and age > scheme.max_age:
                reasons.append(f"Age {age} exceeds maximum {scheme.max_age}")
            else:
                checks_passed += 1
                reasons.append(f"Age {age} is within range")
        else:
            missing_info.append("age or date_of_birth")

    # Income check
    if scheme.max_income is not None:
        total_checks += 1
        if profile.income is not None:
            if profile.income <= scheme.max_income:
                checks_passed += 1
                reasons.append(f"Income ₹{profile.income:,.0f} is within limit ₹{scheme.max_income:,.0f}")
            else:
                reasons.append(f"Income ₹{profile.income:,.0f} exceeds limit ₹{scheme.max_income:,.0f}")
        else:
            missing_info.append("income")

    # Category check
    if scheme.eligible_categories:
        total_checks += 1
        eligible_cats = [c.strip() for c in scheme.eligible_categories.split(",")]
        if profile.category:
            if profile.category in eligible_cats:
                checks_passed += 1
                reasons.append(f"Category {profile.category} is eligible")
            else:
                reasons.append(f"Category {profile.category} is not in eligible list: {scheme.eligible_categories}")
        else:
            # If all categories are eligible, pass by default
            if set(eligible_cats) == {"SC", "ST", "OBC", "General"}:
                checks_passed += 1
                reasons.append("All categories are eligible")
            else:
                missing_info.append("category")

    # Gender check
    if scheme.eligible_genders:
        total_checks += 1
        eligible_genders = [g.strip() for g in scheme.eligible_genders.split(",")]
        if profile.gender:
            if profile.gender in eligible_genders:
                checks_passed += 1
                reasons.append(f"Gender {profile.gender} is eligible")
            else:
                reasons.append(f"Gender {profile.gender} is not eligible for this scheme")
        else:
            if set(eligible_genders) == {"Male", "Female"}:
                checks_passed += 1
                reasons.append("Both genders are eligible")
            else:
                missing_info.append("gender")

    # State check
    if scheme.eligible_states:
        total_checks += 1
        eligible_states = [s.strip() for s in scheme.eligible_states.split(",")]
        if profile.state:
            if profile.state in eligible_states:
                checks_passed += 1
                reasons.append(f"State {profile.state} is eligible")
            else:
                reasons.append(f"State {profile.state} is not in eligible states")
        else:
            missing_info.append("state")

    # Calculate score
    if total_checks > 0:
        score = checks_passed / total_checks
    else:
        score = 1.0  # No restrictions = eligible

    is_eligible = score >= 0.5 and len(missing_info) <= 2

    return EligibilityResult(
        scheme=scheme,
        is_eligible=is_eligible,
        match_score=round(score, 2),
        reasons=reasons,
        missing_info=missing_info,
    )


def find_eligible_schemes(
    profile: UserProfile, category_filter: str = None
) -> list[EligibilityResult]:
    """Find all eligible schemes for a user profile."""
    schemes = get_all_schemes()

    if category_filter:
        schemes = [s for s in schemes if s.category == category_filter]

    results = []
    for scheme in schemes:
        result = check_eligibility(profile, scheme)
        results.append(result)

    # Sort by match score descending
    results.sort(key=lambda r: r.match_score, reverse=True)
    return results
