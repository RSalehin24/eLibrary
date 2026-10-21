import pytest
from apps.ingestion.source_processing.classification import inline_classification


@pytest.mark.parametrize(
    "reference",
    [
        "সেই বইটি বহু বছর আগে প্রকাশিত হয়েছিল।",
        "Her diary was published in the following year.",
        "The character says that this is a novel approach to the problem.",
    ],
)
def test_publication_references_inside_reading_text_do_not_reject_the_book(reference):
    html = (
        "<p>সেদিন সকাল থেকেই বাইরে বৃষ্টি হচ্ছিল।</p>"
        "<p>তিনি জানালার কাছে বসে পুরোনো চিঠিগুলো দেখছিলেন।</p>"
        f"<p>{reference}</p><p>দরজার ওপাশ থেকে একটি কণ্ঠস্বর শোনা গেল।</p>"
    )
    assert inline_classification(html) == "inline_reading"


@pytest.mark.parametrize(
    "summary",
    [
        "This is a novel written in 1900.",
        "এই বইটি লেখকের জীবন সম্পর্কে রচিত।",
    ],
)
def test_a_multiline_synopsis_still_requires_actual_reading_content(summary):
    html = f"<p>{summary}</p><p>About the author.</p><p>Publication details.</p>"
    assert inline_classification(html) == "description_only"


def test_a_single_unidentified_paragraph_is_not_published_based_on_length():
    assert (
        inline_classification("<p>Unclassified text. " + "word " * 3000 + "</p>")
        == "unknown_layout"
    )
