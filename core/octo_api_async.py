"""
Asynchronous Octo API Manager using QThread.
Prevents UI freezing by executing API calls in background thread.
"""
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
from queue import Queue
import threading

from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QObject

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of API tasks."""
    TEST_CONNECTION = "test_connection"
    STOP_PROFILE = "stop_profile"
    STOP_PROFILES_BATCH = "stop_profiles_batch"
    FORCE_STOP_PROFILE = "force_stop_profile"
    GET_PROFILE_INFO = "get_profile_info"
    GET_PROFILES_INFO_BATCH = "get_profiles_info_batch"
    CHECK_PROXY = "check_proxy"
    CHECK_PROXIES_BATCH = "check_proxies_batch"


@dataclass
class ApiTask:
    """Represents a single API task."""
    task_id: str
    task_type: TaskType
    params: Dict[str, Any]
    callback_success: Optional[Callable] = None
    callback_error: Optional[Callable] = None


class OctoApiWorker(QThread):
    """
    Worker thread that executes Octo API calls.
    Communicates with main thread only via signals.
    """
    # Signals for communication with main thread
    task_finished = pyqtSignal(str, object)  # task_id, result
    task_error = pyqtSignal(str, str)  # task_id, error_message
    task_progress = pyqtSignal(str, int, int)  # task_id, current, total
    batch_item_done = pyqtSignal(str, str, bool)  # task_id, uuid, success
    
    def __init__(self, octo_api):
        super().__init__()
        self.octo_api = octo_api
        self.task_queue = Queue()
        self.should_stop = False
        self.current_task_cancelled = False
        self._cancel_lock = QMutex()
    
    def run(self):
        """Main worker loop - processes tasks from queue."""
        logger.info("[OctoApiWorker] Worker thread started")
        
        while not self.should_stop:
            try:
                # Wait for task with timeout (allows checking should_stop)
                task = self.task_queue.get(timeout=0.5)
            except Exception:
                continue
            
            if task is None:  # Poison pill
                break
            
            self._process_task(task)
        
        logger.info("[OctoApiWorker] Worker thread stopped")
    
    def _process_task(self, task: ApiTask):
        """Process a single task."""
        try:
            logger.info(f"[OctoApiWorker] Processing task: {task.task_type.value} ({task.task_id})")
            
            # Reset cancel flag for new task
            with QMutexLocker(self._cancel_lock):
                self.current_task_cancelled = False
            
            if task.task_type == TaskType.TEST_CONNECTION:
                result = self.octo_api.test_connection()
                self.task_finished.emit(task.task_id, result)
            
            elif task.task_type == TaskType.STOP_PROFILE:
                uuid = task.params.get("uuid")
                result = self.octo_api.stop_profile(uuid)
                self.task_finished.emit(task.task_id, {"uuid": uuid, "success": result})
            
            elif task.task_type == TaskType.FORCE_STOP_PROFILE:
                uuid = task.params.get("uuid")
                result = self.octo_api.force_stop_profile(uuid)
                self.task_finished.emit(task.task_id, {"uuid": uuid, "success": result})
            
            elif task.task_type == TaskType.STOP_PROFILES_BATCH:
                self._process_batch_stop(task)
            
            elif task.task_type == TaskType.GET_PROFILE_INFO:
                uuid = task.params.get("uuid")
                result = self.octo_api.get_profile_info(uuid)
                self.task_finished.emit(task.task_id, {"uuid": uuid, "info": result})
            
            elif task.task_type == TaskType.GET_PROFILES_INFO_BATCH:
                self._process_batch_get_info(task)
            
            elif task.task_type == TaskType.CHECK_PROXY:
                uuid = task.params.get("uuid")
                result = self.octo_api.check_proxy(uuid)
                self.task_finished.emit(task.task_id, {"uuid": uuid, "result": result})
            
            elif task.task_type == TaskType.CHECK_PROXIES_BATCH:
                self._process_batch_check_proxies(task)
            
        except Exception as e:
            logger.error(f"[OctoApiWorker] Task error: {e}")
            self.task_error.emit(task.task_id, str(e))
    
    def _process_batch_stop(self, task: ApiTask):
        """Process batch stop profiles task."""
        uuids = task.params.get("uuids", [])
        force = task.params.get("force", False)
        total = len(uuids)
        results = []
        
        for i, uuid in enumerate(uuids):
            # Check if cancelled
            with QMutexLocker(self._cancel_lock):
                if self.current_task_cancelled:
                    logger.info(f"[OctoApiWorker] Batch stop cancelled at {i}/{total}")
                    break
            
            try:
                if force:
                    success = self.octo_api.force_stop_profile(uuid)
                else:
                    success = self.octo_api.stop_profile(uuid)
                results.append({"uuid": uuid, "success": success})
                self.batch_item_done.emit(task.task_id, uuid, success)
            except Exception as e:
                results.append({"uuid": uuid, "success": False, "error": str(e)})
                self.batch_item_done.emit(task.task_id, uuid, False)
            
            # Emit progress
            self.task_progress.emit(task.task_id, i + 1, total)
        
        self.task_finished.emit(task.task_id, {"results": results, "cancelled": self.current_task_cancelled})
    
    def _process_batch_get_info(self, task: ApiTask):
        """Process batch get profile info task."""
        uuids = task.params.get("uuids", [])
        total = len(uuids)
        results = {}
        
        for i, uuid in enumerate(uuids):
            # Check if cancelled
            with QMutexLocker(self._cancel_lock):
                if self.current_task_cancelled:
                    logger.info(f"[OctoApiWorker] Batch get info cancelled at {i}/{total}")
                    break
            
            try:
                info = self.octo_api.get_profile_info(uuid)
                results[uuid] = info
            except Exception as e:
                results[uuid] = None
                logger.error(f"[OctoApiWorker] Get info error for {uuid}: {e}")
            
            # Emit progress
            self.task_progress.emit(task.task_id, i + 1, total)
        
        self.task_finished.emit(task.task_id, {"results": results, "cancelled": self.current_task_cancelled})
    
    def _process_batch_check_proxies(self, task: ApiTask):
        """Process batch proxy check task."""
        uuids = task.params.get("uuids", [])
        total = len(uuids)
        results = {}
        
        for i, uuid in enumerate(uuids):
            # Check if cancelled
            with QMutexLocker(self._cancel_lock):
                if self.current_task_cancelled:
                    logger.info(f"[OctoApiWorker] Batch proxy check cancelled at {i}/{total}")
                    break
            
            try:
                result = self.octo_api.check_proxy(uuid)
                results[uuid] = result
                # Don't emit batch_item_done here - it's connected to stop handler
            except Exception as e:
                results[uuid] = {"success": False, "message": str(e), "ip": ""}
                logger.error(f"[OctoApiWorker] Check proxy error for {uuid}: {e}")
            
            # Emit progress
            self.task_progress.emit(task.task_id, i + 1, total)
        
        self.task_finished.emit(task.task_id, {"results": results, "cancelled": self.current_task_cancelled})
    
    def add_task(self, task: ApiTask):
        """Add task to queue."""
        self.task_queue.put(task)
    
    def cancel_current_task(self):
        """Request cancellation of current batch task."""
        with QMutexLocker(self._cancel_lock):
            self.current_task_cancelled = True
        logger.info("[OctoApiWorker] Cancellation requested")
    
    def shutdown(self):
        """Gracefully shutdown the worker."""
        logger.info("[OctoApiWorker] Shutdown requested")
        self.should_stop = True
        self.task_queue.put(None)  # Poison pill
        self.wait(5000)  # Wait up to 5 seconds


class OctoApiManager(QObject):
    """
    Manager class that provides async API interface.
    Use this from MainWindow instead of calling OctoAPI directly.
    """
    # High-level signals for UI updates
    operation_started = pyqtSignal(str, str)  # task_id, description
    operation_progress = pyqtSignal(str, int, int, str)  # task_id, current, total, message
    operation_finished = pyqtSignal(str, object)  # task_id, result
    operation_error = pyqtSignal(str, str)  # task_id, error
    operation_cancelled = pyqtSignal(str)  # task_id
    
    # Specific signals for batch operations
    profile_stopped = pyqtSignal(str, bool)  # uuid, success
    profile_info_received = pyqtSignal(str, object)  # uuid, info
    proxy_checked = pyqtSignal(str, bool, str)  # uuid, success, message
    
    def __init__(self, octo_api):
        super().__init__()
        self.octo_api = octo_api
        self.worker = None
        self._task_counter = 0
        self._task_lock = QMutex()
        self._pending_callbacks = {}  # task_id -> (success_cb, error_cb)
        
        self._start_worker()
    
    def set_api_token(self, token: str):
        """Set Octo API token for remote API access."""
        self.octo_api.set_api_token(token)
    
    def _start_worker(self):
        """Start the background worker thread."""
        if self.worker is not None:
            self.shutdown()
        
        self.worker = OctoApiWorker(self.octo_api)
        self.worker.task_finished.connect(self._on_task_finished)
        self.worker.task_error.connect(self._on_task_error)
        self.worker.task_progress.connect(self._on_task_progress)
        self.worker.batch_item_done.connect(self._on_batch_item_done)
        self.worker.start()
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        with QMutexLocker(self._task_lock):
            self._task_counter += 1
            return f"task_{self._task_counter}"
    
    def _on_task_finished(self, task_id: str, result: object):
        """Handle task completion."""
        logger.info(f"[OctoApiManager] Task finished: {task_id}")
        
        # Check if cancelled
        if isinstance(result, dict) and result.get("cancelled"):
            self.operation_cancelled.emit(task_id)
        else:
            self.operation_finished.emit(task_id, result)
        
        # Call registered callback
        if task_id in self._pending_callbacks:
            success_cb, _ = self._pending_callbacks.pop(task_id)
            if success_cb:
                success_cb(result)
    
    def _on_task_error(self, task_id: str, error: str):
        """Handle task error."""
        logger.error(f"[OctoApiManager] Task error: {task_id} - {error}")
        self.operation_error.emit(task_id, error)
        
        # Call registered error callback
        if task_id in self._pending_callbacks:
            _, error_cb = self._pending_callbacks.pop(task_id)
            if error_cb:
                error_cb(error)
    
    def _on_task_progress(self, task_id: str, current: int, total: int):
        """Handle task progress update."""
        self.operation_progress.emit(task_id, current, total, f"{current}/{total}")
    
    def _on_batch_item_done(self, task_id: str, uuid: str, success: bool):
        """Handle individual item in batch operation."""
        self.profile_stopped.emit(uuid, success)
    
    # === PUBLIC API METHODS ===
    
    def test_connection_async(self, callback: Callable = None, error_callback: Callable = None) -> str:
        """Test connection to Octo Browser asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.TEST_CONNECTION,
            params={}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, "Testing connection...")
        self.worker.add_task(task)
        return task_id
    
    def stop_profile_async(self, uuid: str, force: bool = False,
                           callback: Callable = None, error_callback: Callable = None) -> str:
        """Stop a single profile asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.FORCE_STOP_PROFILE if force else TaskType.STOP_PROFILE,
            params={"uuid": uuid}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Stopping profile {uuid[:8]}...")
        self.worker.add_task(task)
        return task_id
    
    def stop_profiles_batch_async(self, uuids: List[str], force: bool = False,
                                   callback: Callable = None, error_callback: Callable = None) -> str:
        """Stop multiple profiles asynchronously with progress tracking."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.STOP_PROFILES_BATCH,
            params={"uuids": uuids, "force": force}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Stopping {len(uuids)} profiles...")
        self.worker.add_task(task)
        return task_id
    
    def get_profile_info_async(self, uuid: str,
                                callback: Callable = None, error_callback: Callable = None) -> str:
        """Get profile info asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.GET_PROFILE_INFO,
            params={"uuid": uuid}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Getting info for {uuid[:8]}...")
        self.worker.add_task(task)
        return task_id
    
    def get_profiles_info_batch_async(self, uuids: List[str],
                                       callback: Callable = None, error_callback: Callable = None) -> str:
        """Get info for multiple profiles asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.GET_PROFILES_INFO_BATCH,
            params={"uuids": uuids}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Getting info for {len(uuids)} profiles...")
        self.worker.add_task(task)
        return task_id
    
    def check_proxy_async(self, uuid: str,
                          callback: Callable = None, error_callback: Callable = None) -> str:
        """Check proxy for a single profile asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.CHECK_PROXY,
            params={"uuid": uuid}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Checking proxy for {uuid[:8]}...")
        self.worker.add_task(task)
        return task_id
    
    def check_proxies_batch_async(self, uuids: List[str],
                                   callback: Callable = None, error_callback: Callable = None) -> str:
        """Check proxies for multiple profiles asynchronously."""
        task_id = self._generate_task_id()
        task = ApiTask(
            task_id=task_id,
            task_type=TaskType.CHECK_PROXIES_BATCH,
            params={"uuids": uuids}
        )
        
        if callback or error_callback:
            self._pending_callbacks[task_id] = (callback, error_callback)
        
        self.operation_started.emit(task_id, f"Checking proxies for {len(uuids)} profiles...")
        self.worker.add_task(task)
        return task_id
    
    def cancel_current_operation(self):
        """Cancel the currently running batch operation."""
        if self.worker:
            self.worker.cancel_current_task()
    
    def shutdown(self):
        """Shutdown the manager and worker thread."""
        if self.worker:
            self.worker.shutdown()
            self.worker = None
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self.worker is not None and self.worker.isRunning()
