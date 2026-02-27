"""
Unit Tests — Core Exception Hierarchy & Observer/EventBus Pattern
"""
import pytest
from app.core.exceptions import (
    GenXSOPException,
    EntityNotFoundException,
    BusinessRuleViolationException,
    DuplicateEntityException,
    InvalidStateTransitionException,
    InsufficientPermissionsException,
    AuthenticationException,
    ForecastGenerationException,
    InsufficientDataException,
    to_http_exception,
)
from app.utils.events import (
    EventBus,
    EventHandler,
    DomainEvent,
    EntityCreatedEvent,
    EntityUpdatedEvent,
    EntityDeletedEvent,
    PlanStatusChangedEvent,
    ForecastGeneratedEvent,
    LoggingHandler,
    get_event_bus,
)


# ── Exception Hierarchy Tests ─────────────────────────────────────────────────

class TestExceptionHierarchy:

    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(EntityNotFoundException, GenXSOPException)
        assert issubclass(BusinessRuleViolationException, GenXSOPException)
        assert issubclass(DuplicateEntityException, GenXSOPException)
        assert issubclass(InvalidStateTransitionException, GenXSOPException)
        assert issubclass(InsufficientPermissionsException, GenXSOPException)
        assert issubclass(AuthenticationException, GenXSOPException)
        assert issubclass(ForecastGenerationException, GenXSOPException)
        assert issubclass(InsufficientDataException, GenXSOPException)

    def test_entity_not_found_message(self):
        exc = EntityNotFoundException("DemandPlan", 42)
        assert "DemandPlan" in str(exc)
        assert "42" in str(exc)

    def test_business_rule_violation_message(self):
        exc = BusinessRuleViolationException("Cannot modify locked plan")
        assert "Cannot modify locked plan" in str(exc)

    def test_invalid_state_transition_message(self):
        exc = InvalidStateTransitionException("DemandPlan", "draft", "locked")
        assert "draft" in str(exc)
        assert "locked" in str(exc)

    def test_insufficient_data_message(self):
        exc = InsufficientDataException(required=12, available=3, operation="forecast")
        assert "12" in str(exc)
        assert "3" in str(exc)

    def test_duplicate_entity_message(self):
        exc = DuplicateEntityException("Product", "sku", "SKU-001")
        assert "SKU-001" in str(exc)


class TestToHttpException:

    def test_entity_not_found_returns_404(self):
        exc = EntityNotFoundException("DemandPlan", 1)
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 404

    def test_business_rule_returns_400(self):
        exc = BusinessRuleViolationException("Cannot delete approved plan")
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 400

    def test_duplicate_entity_returns_400(self):
        exc = DuplicateEntityException("Product", "sku", "SKU-001")
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 400

    def test_invalid_state_transition_returns_400(self):
        exc = InvalidStateTransitionException("Plan", "draft", "locked")
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 400

    def test_insufficient_permissions_returns_403(self):
        exc = InsufficientPermissionsException("admin")
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 403

    def test_authentication_returns_401(self):
        exc = AuthenticationException("Invalid token")
        http_exc = to_http_exception(exc)
        assert http_exc.status_code == 401

    def test_http_exception_detail_has_code_and_message(self):
        exc = EntityNotFoundException("DemandPlan", 99)
        http_exc = to_http_exception(exc)
        assert "code" in http_exc.detail
        assert "message" in http_exc.detail


# ── Observer / EventBus Tests ─────────────────────────────────────────────────

class TestEventBus:

    def test_subscribe_and_publish(self):
        received = []

        class TestHandler(EventHandler):
            def handle(self, event: DomainEvent):
                received.append(event)

        bus = EventBus()
        bus.subscribe(TestHandler())
        bus.publish(EntityCreatedEvent(entity_type="demand_plan", entity_id=1))
        assert len(received) == 1
        assert isinstance(received[0], EntityCreatedEvent)

    def test_multiple_handlers_all_notified(self):
        counts = [0, 0]

        class Handler1(EventHandler):
            def handle(self, event): counts[0] += 1

        class Handler2(EventHandler):
            def handle(self, event): counts[1] += 1

        bus = EventBus()
        bus.subscribe(Handler1())
        bus.subscribe(Handler2())
        bus.publish(EntityCreatedEvent(entity_type="test", entity_id=1))
        assert counts == [1, 1]

    def test_unsubscribe_removes_handler(self):
        received = []

        class TestHandler(EventHandler):
            def handle(self, event): received.append(event)

        bus = EventBus()
        handler = TestHandler()
        bus.subscribe(handler)
        bus.unsubscribe(handler)
        bus.publish(EntityCreatedEvent(entity_type="test", entity_id=1))
        assert len(received) == 0

    def test_handler_exception_does_not_crash_bus(self):
        class BrokenHandler(EventHandler):
            def handle(self, event): raise RuntimeError("Broken!")

        bus = EventBus()
        bus.subscribe(BrokenHandler())
        # Should not raise
        bus.publish(EntityCreatedEvent(entity_type="test", entity_id=1))

    def test_can_handle_filter(self):
        received = []

        class FilteredHandler(EventHandler):
            def can_handle(self, event): return isinstance(event, EntityCreatedEvent)
            def handle(self, event): received.append(event)

        bus = EventBus()
        bus.subscribe(FilteredHandler())
        bus.publish(EntityUpdatedEvent(entity_type="test", entity_id=1))  # filtered out
        bus.publish(EntityCreatedEvent(entity_type="test", entity_id=2))  # accepted
        assert len(received) == 1
        assert isinstance(received[0], EntityCreatedEvent)

    def test_logging_handler_does_not_raise(self):
        bus = EventBus()
        bus.subscribe(LoggingHandler())
        bus.publish(PlanStatusChangedEvent(
            entity_type="demand_plan", entity_id=1,
            old_status="draft", new_status="submitted",
        ))

    def test_get_event_bus_returns_singleton(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2


class TestDomainEvents:

    def test_entity_created_event_fields(self):
        event = EntityCreatedEvent(
            entity_type="demand_plan", entity_id=5, user_id=1,
            new_values={"product_id": 10},
        )
        assert event.entity_type == "demand_plan"
        assert event.entity_id == 5
        assert event.user_id == 1
        assert event.new_values["product_id"] == 10

    def test_plan_status_changed_event_fields(self):
        event = PlanStatusChangedEvent(
            entity_type="supply_plan", entity_id=3,
            old_status="draft", new_status="approved",
            comment="Looks good",
        )
        assert event.old_status == "draft"
        assert event.new_status == "approved"
        assert event.comment == "Looks good"

    def test_forecast_generated_event_fields(self):
        event = ForecastGeneratedEvent(
            product_id=7, model_type="prophet",
            horizon_months=6, records_created=6,
        )
        assert event.product_id == 7
        assert event.model_type == "prophet"
        assert event.records_created == 6
