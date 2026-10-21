import pytest
from apps.processing.job_models import JobDispatch
from apps.processing.jobs.dispatches import claim_dispatches
from config.background_limits import processing_queue_name
from django.core.exceptions import ImproperlyConfigured


@pytest.mark.parametrize(
    "name", ["processing", "processing-v2", "processing.20261020", "p" * 255]
)
def test_named_processing_queues_accept_bounded_amqp_safe_names(name):
    assert processing_queue_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "delivery",
        "amq.private",
        "processing,delivery",
        "queue name",
        "queue\n",
        "p" * 256,
        "processing;exit",
    ],
)
def test_queue_configuration_rejects_reserved_or_unsafe_consumer_names(name):
    with pytest.raises(ImproperlyConfigured, match="BACKGROUND_PROCESSING_QUEUE"):
        processing_queue_name(name)


@pytest.mark.django_db
def test_a_fresh_processing_queue_preserves_the_separate_delivery_route(
    kindle_job, settings
):
    settings.BACKGROUND_PROCESSING_QUEUE = "processing-v2"
    leases = claim_dispatches()
    routes = {
        JobDispatch.objects.get(pk=lease.identifier).job.kind: lease.queue
        for lease in leases
    }
    assert routes["prepare_epub"] == "processing-v2"
    assert routes["deliver_kindle"] == "delivery"
