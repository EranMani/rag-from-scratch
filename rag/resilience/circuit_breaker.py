import time
from enum import IntEnum
from dataclasses import dataclass, field
from src.app.core.config import settings
from src.app.core.logging_config import logger
from src.app.core.metrics import CIRCUIT_BREAKER_STATE


class CircuitState(IntEnum):
    CLOSED = 0 # normal - requests flow through
    OPEN = 1 # failing - reject requests immediately
    HALF_OPEN = 2 # probing - allow one request to test recovery


@dataclass
class CircuitBreaker:
    """
    State machine protecting a single service

    States:
        Closed -> OPEN: failure count >= given threshold
        OPEN -> HALF_OPEN: recovery timeout seconds have passed
        HALF_OPEN -> CLOSED: probe request succeeded
        HALF_OPEN -> OPEN: probe request failed
    """
    service_name: str
    failure_threshold: int = field(default_factory=lambda: settings.cb_failure_threshold)
    recovery_timeout: int = field(default_factory=lambda: settings.cb_recovery_timeout)

    # Private variables for recording state, failure count and when last failure happend
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    def _update_metric(self):
        CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(self._state.value)

    @property
    def state(self) -> CircuitState:
        """In OPEN mode, check when recovery timeout passed with real time and switch to HALF_OPEN"""
        if (
            self._state == CircuitState.OPEN
            and time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._update_metric()
            logger.info(
                "Circuit breaker → HALF_OPEN (probing recovery)",
                extra={"service": self.service_name}
            )
        
        return self._state

    def is_available(self) -> bool:
        """Check if current state can be found in one of the following"""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            logger.info(
                "Circuit breaker → CLOSED (recovery confirmed)",
                extra={"service": self.service_name}
            )

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._update_metric()

    def record_failure(self) -> None:
        """Update failure count and time when circuit becomes OPEN"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        # Log the service name that failed byeond current failure threshold
        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.warning(
                    "Circuit breaker → OPEN (too many failures)",
                    extra={
                        "service": self.service_name,
                        "failure_count": self._failure_count,
                    }
                )
            self._state = CircuitState.OPEN
        self._update_metric()

    def status(self) -> dict:
        """Returns the current service status, including name, current state and how many times it failed so far"""
        return {
            "service": self.service_name,
            "state": self.state.name,
            "failure_count": self._failure_count
        }

# One circuit breaker per protected service
chroma_cb = CircuitBreaker("chroma")
openai_cb = CircuitBreaker("openai")
redis_cb = CircuitBreaker("redis")
