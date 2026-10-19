import pytest
from apps.ingestion.pipeline.curated_validation import source_chrome_hits


@pytest.mark.parametrize(
    "text",
    [
        "ফেইসবুকে লগইন করলাম। একটা নতুন মেসেজ এসেছে ওনার কাছ থেকে।",
        "স্টক মার্কেটে একবার ঢুকে সব ঠিক ঠাক করে আমার ইমেইল অ্যাড্রেস এ লগইন করলাম।",
        "লগইন করলাম। তারপর আমার বন্ধুকে লিখলাম।",
        "She logged in and found a message from her friend.",
        "Login was the last thing on his mind.",
    ],
)
def test_login_mentions_inside_a_book_are_preserved(text):
    assert (
        source_chrome_hits(
            [
                {
                    "section_type": "body",
                    "section_id": "chapter",
                    "html": f"<p>{text}</p>",
                }
            ]
        )
        == []
    )


@pytest.mark.parametrize(
    "text",
    [
        "লগইন",
        "লগইন করুন",
        "বইটি পড়তে লগইন করুন।",
        "Login",
        "Please login to continue",
        "You must be logged in to post a comment.",
    ],
)
def test_actual_login_prompts_still_block_publication(text):
    assert source_chrome_hits(
        [{"section_type": "body", "section_id": "chapter", "html": f"<p>{text}</p>"}]
    )
