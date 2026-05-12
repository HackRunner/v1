import json
import re

# Common English stop words to filter out during keyword matching
STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "by", "from", "as", "be",
    "are", "was", "were", "has", "have", "had", "not", "this",
    "that", "which", "used", "use", "can", "will", "do", "does",
    "its", "it's", "also", "than", "then", "so", "if", "when"
}

# Threshold fraction for keyword matching — how much of the keywords
# must appear in the explanation to consider it consistent.
# 2 = half (strict); 3 = a third (permissive).
KEYWORD_MATCH_FRACTION = 2  # divisor: len(keywords) // KEYWORD_MATCH_FRACTION


def extract_json(text: str):
    
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            return json.loads(match.group())

    except Exception:
        pass

    return None


def validate_mcq(data: dict) -> tuple[bool, str | None]:

    if data is None:
        return False, "invalid_json"

    required = [
        "type",
        "difficulty",
        "topic",
        "question",
        "options",
        "correct_answer",
        "explanation"
    ]

    for key in required:
        if key not in data:
            return False, f"missing_field_{key}"
    """
    Run all validation checks against a parsed MCQ dict.
    Returns (is_valid, reason_string_or_None).
    Order matters: cheap/structural checks run before semantic ones.
    """
    if data["type"] != "mcq":
        return False, "invalid_type"
    if data["correct_answer"] not in ["A", "B", "C", "D"]:
        return False, "invalid_correct_answer"

    if not is_quality_question(data):
        return False, "low_quality"

    if not is_safe_cyber_question(data):
        return False, "unsafe_content"

    if has_ambiguity(data):
        return False, "ambiguous"

    if has_placeholder(data):
        return False, "placeholder_detected"

    if not is_explanation_consistent(data):
        return False, "explanation_mismatch"

    # Runs last — only meaningful once we know the correct-answer
    # explanation is itself consistent.
    if has_multiple_correct_options(data):
        return False, "multiple_correct_options"

    return True, None


def is_quality_question(data):
    question = data["question"]
    explanation = data["explanation"]
    options = data["options"]

    if len(options) != 4:
        return False

    if len(explanation.split()) < 8:
        return False

    if len(question.split()) < 5:
        return False

    return True


def is_safe_cyber_question(data):
    text = (
        data["question"] +
        " " +
        " ".join(data["options"]) +
        " " +
        data["explanation"]
    ).lower()

    # Patterns that are genuinely destructive and have no educational framing.
    # NOTE: terms like "exploit", "payload", "reverse shell" are intentionally
    # excluded — they are standard cybersecurity vocabulary for a beginner MCQ
    # context and blocking them would reject most valid questions.
    dangerous_patterns = [
        # Destructive DB commands
        "drop table",
        "delete from",
        "truncate table",
        # System destruction
        "rm -rf /",
        "format c:",
        "mkfs.",
        ":(){:|:&};:",          # fork bomb
        # Malware / C2 specifics
        "reverse shell one-liner",
        "meterpreter session",
        "download and execute",
        "wget http",
        "curl http",
        # Credential dumping specifics
        "lsass dump",
        "mimikatz sekurlsa",
        # Lateral movement specifics that go beyond theory
        "psexec \\\\",
        "wmiexec.py",
        # Shutdown / wipe
        "shutdown /s /t 0",
        "del /f /s /q",
    ]

    for pattern in dangerous_patterns:
        if pattern in text:
            return False

    return True


def has_ambiguity(data):
    explanation = data["explanation"].lower()

    ambiguous_terms = [
        "also correct",
        "partially correct",
        "can also be",
        "another correct",
        "might be correct",
        "both a and",
        "both b and",
        "both c and",
        "all of the above",
        "any of the above",
    ]

    for term in ambiguous_terms:
        if term in explanation:
            return True

    return False


def has_placeholder(data):
    text = " ".join(data["options"]).lower()
    bad_patterns = ["...", "option text", "placeholder"]
    return any(p in text for p in bad_patterns)


def _extract_option_keywords(option_text: str) -> list[str]:
    """
    Strip the leading label (e.g. 'A.', 'B)') from an option
    and return meaningful keywords, filtering out stop words
    and short tokens.
    """
    cleaned = re.sub(r"^[a-dA-D][.)]\s*", "", option_text).lower()
    tokens = re.findall(r"[a-z]{3,}", cleaned)
    return [t for t in tokens if t not in STOP_WORDS]


def is_explanation_consistent(data):
    """
    Check that the explanation supports the correct answer option
    by verifying enough of the option's keywords appear in it.
    """
    explanation = data["explanation"].lower()
    correct = data["correct_answer"]
    options = data["options"]

    correct_option_text = options[ord(correct) - ord("A")]
    keywords = _extract_option_keywords(correct_option_text)

    if not keywords:
        return True  # nothing meaningful to check — give benefit of the doubt

    match_count = sum(1 for word in keywords if word in explanation)
    required = max(2, len(keywords) // KEYWORD_MATCH_FRACTION)
    return match_count >= required


def has_multiple_correct_options(data):
    """
    Check whether any incorrect option has suspiciously high keyword overlap
    with the explanation — signals the model may have made multiple options correct.
    """
    explanation = data["explanation"].lower()
    correct = data["correct_answer"]
    options = data["options"]

    for i, opt in enumerate(options):
        label = chr(ord("A") + i)
        if label == correct:
            continue

        keywords = _extract_option_keywords(opt)
        if not keywords:
            continue

        overlap = sum(1 for w in keywords if w in explanation)
        required = max(3, len(keywords) // 2)

        if overlap >= required:
            return True

    return False


def validate_short_answer(data):
    if data is None:
        return False, "invalid_json"
    required = [
        "type",
        "difficulty",
        "topic",
        "question",
        "answer",
        "explanation"
    ]

    for key in required:
        if key not in data:
            return False, f"Missing field: {key}"

    if data["type"] != "short_answer":
        return False, "Invalid type"

    answer_words = len(data["answer"].split())
    if not data["answer"].strip():
        return False, "empty_answer"

    if len(data["question"].split()) < 5:
        return False, "low_quality_question"

    if answer_words > 8:
        return False, "Answer too long"

    if len(data["explanation"].split()) < 5:
        return False, "weak_explanation"

    return True, None