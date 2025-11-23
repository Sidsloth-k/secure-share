"""Network utilities with retry logic, resumable uploads, and graceful error handling."""

import json
import logging
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("SecureShare")

# Default retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_TIMEOUT = 300  # 5 minutes for large files


class NetworkError(Exception):
    """Base exception for network-related errors."""

    pass


class RetryableError(NetworkError):
    """Error that can be retried."""

    pass


class NonRetryableError(NetworkError):
    """Error that should not be retried."""

    pass


class UploadProgress:
    """Tracks upload progress for resumable uploads."""

    def __init__(self, file_id: str, file_path: str, total_size: int):
        self.file_id = file_id
        self.file_path = file_path
        self.total_size = total_size
        self.uploaded_size = 0
        self.progress_file = Path("temp") / f"{file_id}.progress"
        self._load_progress()

    def _load_progress(self):
        """Load progress from disk if it exists."""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, "r") as f:
                    data = json.load(f)
                    self.uploaded_size = data.get("uploaded_size", 0)
                    logger.info(
                        f"Resuming upload: {self.uploaded_size}/{self.total_size} bytes already uploaded"
                    )
        except Exception as e:
            logger.warning(f"Failed to load upload progress: {e}")
            self.uploaded_size = 0

    def save_progress(self, uploaded_size: int):
        """Save current progress to disk."""
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, "w") as f:
                json.dump(
                    {
                        "file_id": self.file_id,
                        "file_path": self.file_path,
                        "total_size": self.total_size,
                        "uploaded_size": uploaded_size,
                    },
                    f,
                )
            self.uploaded_size = uploaded_size
        except Exception as e:
            logger.warning(f"Failed to save upload progress: {e}")

    def clear_progress(self):
        """Clear progress file after successful upload."""
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to clear progress file: {e}")

    def get_progress_percent(self) -> float:
        """Get upload progress as percentage."""
        if self.total_size == 0:
            return 0.0
        return (self.uploaded_size / self.total_size) * 100.0


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable."""
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Network-related errors that are retryable
    retryable_keywords = [
        "timeout",
        "timed out",
        "connection",
        "network",
        "temporary",
        "retry",
        "503",
        "502",
        "504",
        "429",  # Too many requests
        "read operation timed out",
        "connection reset",
        "broken pipe",
    ]

    # Non-retryable errors
    non_retryable_keywords = [
        "authentication",
        "authorization",
        "forbidden",
        "401",
        "403",
        "404",
        "not found",
        "invalid",
        "malformed",
        "row-level security",
        "rls",
    ]

    # Check for non-retryable first
    for keyword in non_retryable_keywords:
        if keyword in error_str:
            return False

    # Check for retryable
    for keyword in retryable_keywords:
        if keyword in error_str:
            return True

    # Default: retry network errors, don't retry others
    if "http" in error_type.lower() or "network" in error_type.lower():
        return True

    return False


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_RETRY_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    max_delay: float = 60.0,
    retryable_check: Optional[Callable[[Exception], bool]] = None,
):
    """Decorator for retrying operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay: Maximum delay between retries in seconds
        retryable_check: Optional function to check if error is retryable
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retryable_check_func = retryable_check or is_retryable_error
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)

                    # Check if error is retryable
                    if not retryable_check_func(e):
                        logger.error(f"Non-retryable error in {func.__name__}: {error_msg}")
                        raise NonRetryableError(f"Non-retryable error: {error_msg}") from e

                    # If this was the last attempt, raise the error
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {error_msg}"
                        )
                        raise RetryableError(
                            f"Operation failed after {max_retries} retries: {error_msg}"
                        ) from e

                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {error_msg}"
                    )
                    logger.info(f"Retrying in {delay:.2f} seconds...")

                    # Wait before retrying
                    time.sleep(delay)

                    # Increase delay for next retry (exponential backoff)
                    delay = min(delay * backoff_multiplier, max_delay)

            # Should never reach here, but just in case
            if last_exception:
                raise RetryableError(f"Operation failed: {str(last_exception)}") from last_exception

        return wrapper

    return decorator


def safe_execute(
    operation: Callable,
    operation_name: str,
    error_message: str = None,
    default_return: Any = None,
    raise_on_error: bool = False,
    *args,
    **kwargs,
) -> Tuple[Any, Optional[Exception]]:
    """Safely execute an operation with graceful error handling.

    Args:
        operation: Function to execute
        operation_name: Name of the operation for logging
        error_message: Custom error message
        default_return: Value to return on error (if not raising)
        raise_on_error: Whether to raise exception on error
        *args, **kwargs: Arguments to pass to operation

    Returns:
        Tuple of (result, error). If successful, error is None.
    """
    try:
        result = operation(*args, **kwargs)
        return result, None
    except Exception as e:
        error_msg = error_message or f"{operation_name} failed"
        logger.error(f"{error_msg}: {e}")

        if raise_on_error:
            raise
        return default_return, e


def resumable_upload(
    upload_func: Callable,
    file_path: Path,
    file_id: str,
    progress: Optional[UploadProgress] = None,
    chunk_size: int = 1024 * 1024,  # 1MB chunks
    *args,
    **kwargs,
) -> bool:
    """Perform a resumable upload with progress tracking.

    Args:
        upload_func: Function that performs the upload (should accept file-like object)
        file_path: Path to file to upload
        file_id: Unique identifier for the file
        progress: Optional UploadProgress object
        chunk_size: Size of chunks for chunked uploads
        *args, **kwargs: Additional arguments for upload_func

    Returns:
        True if upload successful, False otherwise
    """
    try:
        file_size = file_path.stat().st_size

        if progress is None:
            progress = UploadProgress(file_id, str(file_path), file_size)

        # If we have partial progress, we need to handle resuming
        # For now, we'll use the retry mechanism which will restart
        # In a full implementation, we'd seek to the right position
        if progress.uploaded_size > 0 and progress.uploaded_size < file_size:
            logger.info(
                f"Resuming upload from {progress.uploaded_size}/{file_size} bytes "
                f"({progress.get_progress_percent():.1f}%)"
            )

        # Perform upload with retry
        @retry_with_backoff(max_retries=DEFAULT_MAX_RETRIES)
        def _upload():
            with open(file_path, "rb") as f:
                # If resuming, seek to the right position
                if progress.uploaded_size > 0:
                    f.seek(progress.uploaded_size)

                result = upload_func(f, *args, **kwargs)
                progress.save_progress(file_size)  # Mark as complete
                return result

        _upload()
        progress.clear_progress()
        logger.info(f"Successfully uploaded {file_path.name} ({file_size} bytes)")
        return True

    except Exception as e:
        logger.error(f"Resumable upload failed for {file_path.name}: {e}")
        return False


def batch_operation_with_rollback(
    operations: list[Callable],
    operation_names: list[str],
    rollback_operations: Optional[list[Callable]] = None,
) -> Tuple[bool, Optional[int]]:
    """Execute a batch of operations with rollback on failure.

    Args:
        operations: List of functions to execute
        operation_names: List of names for each operation (for logging)
        rollback_operations: Optional list of rollback functions (in reverse order)

    Returns:
        Tuple of (success, failed_index). If successful, failed_index is None.
    """
    completed_operations = []

    try:
        for i, (operation, name) in enumerate(zip(operations, operation_names)):
            logger.info(f"Executing operation {i + 1}/{len(operations)}: {name}")
            try:
                result = operation()
                completed_operations.append((i, operation, name))
                logger.info(f"Operation {i + 1} completed successfully: {name}")
            except Exception as e:
                logger.error(f"Operation {i + 1} failed: {name} - {e}")
                # Rollback completed operations
                if rollback_operations:
                    logger.warning(f"Rolling back {len(completed_operations)} completed operations...")
                    for j, (op_idx, _, op_name) in enumerate(reversed(completed_operations)):
                        rollback_idx = len(rollback_operations) - 1 - j
                        if rollback_idx >= 0 and rollback_idx < len(rollback_operations):
                            try:
                                rollback_operations[rollback_idx]()
                                logger.info(f"Rolled back operation: {op_name}")
                            except Exception as rollback_error:
                                logger.error(f"Rollback failed for {op_name}: {rollback_error}")
                return False, i

        return True, None

    except Exception as e:
        logger.error(f"Batch operation failed: {e}")
        return False, len(completed_operations)



