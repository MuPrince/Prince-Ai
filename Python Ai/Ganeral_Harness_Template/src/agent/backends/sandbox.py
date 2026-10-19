import threading
import time
import logging
from typing import Optional, Dict, List, Tuple

from opensandbox import SandboxSync
from deepagents_opensandbox import OpensandboxBackend

from agent.config.config import SANDBOX_IDLE_TIMEOUT, SANDBOX_CLEANUP_INTERVAL

logger = logging.getLogger(__name__)

class _SandboxEntry:
    def __init__(self, sandbox: SandboxSync, backend: OpensandboxBackend):
        self.lock = threading.Lock()
        self.sandbox = sandbox
        self.backend = backend
        self.last_use_at = time.time()
        self.provisioned = False
        self.provisioned_error: Optional[str] = None

    def touch(self):
        self.last_use_at = time.time()

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_use_at

    def close(self):
        try:
            self.sandbox.kill()
        except Exception:
            pass

        try:
            self.sandbox.close()
        except Exception:
            pass


class SandboxManager:
    def __init__(self, image: str, idle_timeout: int = SANDBOX_IDLE_TIMEOUT, cleanup_interval_seconds: int = SANDBOX_CLEANUP_INTERVAL):
        self._image = image
        self._idle_timeout = idle_timeout
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._entries: Dict[str, _SandboxEntry] = {}
        self._global_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._available = False

    def start(self):
        try:
            logger.info("SandboxManager: probing sandbox availability...")
            probe = SandboxSync.create(self._image)
            probe.kill()
            probe.close()
            self._available = True
            logger.info("SandboxManager: sandbox available and cleanup thread started.")
        except Exception as e:
            logger.error(f"SandboxManager: sandbox unavailable. - {e}")
            self._available = False
            return

        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, name="sandbox-cleanup", daemon=True
        )
        self._cleanup_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)

        with self._global_lock:
            entries = list(self._entries.values())
            self._entries.clear()

        for entry in entries:
            with entry.lock:
                entry.close()
        logger.info(f"SandboxManager: sandbox stopped, cleaned up {len(entries)} sandbox(es).")

    @property
    def available(self) -> bool:
        return self._available

    def _cleanup_loop(self):
        logger.info(
            f"SandboxManager: cleanup thread started "
            f"(idle_timeout={self._idle_timeout}s, check_interval={self._cleanup_interval_seconds}s)."
        )
        while not self._stop_event.is_set():
            try:
                self._reap_expired()
            except Exception as e:
                logger.error(f"SandboxManager: cleanup error: {e}", exc_info=True)

            self._stop_event.wait(self._cleanup_interval_seconds)

        logger.info(f"SandboxManager: cleanup thread stopped.")

    def _reap_expired(self):
        to_remove: List[Tuple[str, _SandboxEntry]] = []
        with self._global_lock:
            items = list(self._entries.items())

        if not items:
            logger.debug("SandboxManager: cleanup scan - no active sandboxes")
            return

        for org_id, entry in items:
            with entry.lock:
                idle = entry.idle_seconds
            remaining = self._idle_timeout - idle
            if remaining <= 0:
                logger.info(
                    f"SandboxManager: [SCAN] org={org_id} idle={idle:.0f}s "
                    f"(>= threshold {self._idle_timeout}s) -> WILL RECLAIM"
                )
                to_remove.append((org_id, entry))
            else:
                logger.debug(
                    f"SandboxManager: [SCAN] org={org_id} idle={idle:.0f}s "
                    f"(recycle in {remaining: .0f}s)"
                )

        if not to_remove:
            logger.debug(f"SandboxManager: cleanup scan complete - {len(items)} sandbox(ex) active, 0 reclaimed")
            return

        reclaimed = 0
        for org_id, entry in to_remove:
            with self._global_lock:
                cur = self._entries.get(org_id)
                if cur is entry:
                    del self._entries[org_id]
                else:
                    logger.warning(
                        f"SandboxManager: org={org_id} entry changed before reclamation, skipping."
                    )
                    continue
            with entry.lock:
                idle_val = entry.idle_seconds
                entry.close()
            reclaimed += 1
            logger.info(
                f"SandboxManager: [RECLAIMED] org={org_id} sandbox destroyed (was idle={idle_val:.0f}s)."
            )

        still_active = len(items) - reclaimed
        logger.info(
            f"SandboxManager: cleanup scan complete - "
            f"scanned={len(items)}, reclaimed={reclaimed}, still_active={still_active}."
        )

    def get_backend(self, org_id: str) -> Optional[OpensandboxBackend]:
        if not self._available:
            return None

        with self._global_lock:
            entry = self._entries.get(org_id)
            if entry is None:
                logger.info(f"SandboxManager: creating new sandbox for org={org_id}")
                sandbox = SandboxSync.create(self._image)
                backend = OpensandboxBackend(sandbox=sandbox)
                entry = _SandboxEntry(sandbox=sandbox, backend=backend)
                self._entries[org_id] = entry
                need_provision = True
            else:
                logger.info(f"SandboxManager: reusing existing sandbox for org={org_id}")
                need_provision = False

            with entry.lock:
                entry.touch()
                backend = entry.backend

            # if need_provision:
            #     t = threading.Thread(
            #         target=self._provision_entry,
            #         args=(org_id, entry),
            #         name=f"ppt-provision-{org_id}",
            #         daemon=True,
            #     )
            #     t.start()
            return backend

    # def _provision_entry(self, org_id: str, entry: "_SandboxEntry"):
    #     try:
    #         ok, msg = provision_sandbox_with_ppt_skill(entry.backend)
    #         with entry.lock:
    #             entry.provisioned = ok
    #             entry.provisioned_error = None if ok else msg
    #         logger.info(f"SandboxManager: PPT provisioning for org={org_id} -> {msg}")
    #
    #     except Exception as e:
    #         with entry.lock:
    #             entry.provisioned_error = str(e)
    #             entry.provisioned = False
    #         logger.warning(f"SandboxManager: PPT provisioning failed for org={org_id} : {e}")


    def get_sandbox_count(self) -> int:
        with self._global_lock:
            return len(self._entries)












