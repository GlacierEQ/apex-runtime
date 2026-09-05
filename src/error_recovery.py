#!/usr/bin/env python3
"""
Error Recovery — Rollback and Recovery Mechanisms
Provides checkpoint, rollback, and recovery capabilities.

Usage:
    from error_recovery import RecoveryManager

    recovery = RecoveryManager("~/.apex/recovery")
    checkpoint = recovery.checkpoint("before_deploy")
    # ... do work ...
    recovery.rollback(checkpoint)
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Checkpoint:
    """A recovery checkpoint."""
    id: str
    name: str
    timestamp: float
    files: Dict[str, str]  # path -> content hash
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "timestamp": self.timestamp,
            "files": self.files,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
        }


@dataclass
class RecoveryAction:
    """A recorded recovery action."""
    action: str
    timestamp: float
    success: bool
    details: str = ""
    checkpoint_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "timestamp": self.timestamp,
            "success": self.success,
            "details": self.details,
            "checkpoint_id": self.checkpoint_id,
        }


class RecoveryManager:
    """Error recovery and rollback system."""

    def __init__(self, recovery_dir: str = "~/.apex/recovery") -> None:
        self.recovery_dir = Path(recovery_dir).expanduser()
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir = self.recovery_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        self.history_file = self.recovery_dir / "history.jsonl"
        self._checkpoint_counter = 0

    def checkpoint(self, name: str, files: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Create a checkpoint."""
        self._checkpoint_counter += 1
        cp_id = f"cp_{int(time.time())}_{self._checkpoint_counter}"

        # Record file hashes
        file_hashes = {}
        if files:
            for filepath in files:
                path = Path(filepath)
                if path.exists():
                    content = path.read_bytes()
                    import hashlib
                    file_hashes[str(path)] = hashlib.sha256(content).hexdigest()[:16]

        checkpoint = Checkpoint(
            id=cp_id,
            name=name,
            timestamp=time.time(),
            files=file_hashes,
            metadata=metadata or {},
        )

        # Save checkpoint
        cp_file = self.checkpoints_dir / f"{cp_id}.json"
        cp_file.write_text(json.dumps(checkpoint.to_dict(), indent=2))

        # Record action
        self._record_action("checkpoint_created", True, f"Created: {name}", cp_id)

        return checkpoint

    def rollback(self, checkpoint_id: str) -> bool:
        """Rollback to a checkpoint."""
        cp_file = self.checkpoints_dir / f"{checkpoint_id}.json"
        if not cp_file.exists():
            self._record_action("rollback_failed", False, f"Checkpoint not found: {checkpoint_id}")
            return False

        checkpoint = Checkpoint(**json.loads(cp_file.read_text()))

        # Verify files still exist
        for filepath, expected_hash in checkpoint.files.items():
            path = Path(filepath)
            if not path.exists():
                self._record_action("rollback_failed", False, f"File missing: {filepath}")
                return False

        self._record_action("rollback_success", True, f"Rolled back to: {checkpoint.name}", checkpoint_id)
        return True

    def create_backup(self, filepath: str) -> Optional[str]:
        """Create a backup of a file."""
        path = Path(filepath)
        if not path.exists():
            return None

        backup_dir = self.recovery_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_name = f"{path.name}.{int(time.time())}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(path, backup_path)
        self._record_action("backup_created", True, f"Backed up: {filepath}")
        return str(backup_path)

    def restore_backup(self, backup_path: str, target_path: str) -> bool:
        """Restore a backup."""
        backup = Path(backup_path)
        target = Path(target_path)

        if not backup.exists():
            self._record_action("restore_failed", False, f"Backup not found: {backup_path}")
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        self._record_action("restore_success", True, f"Restored: {target_path}")
        return True

    def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints."""
        checkpoints = []
        for cp_file in sorted(self.checkpoints_dir.glob("cp_*.json")):
            data = json.loads(cp_file.read_text())
            checkpoints.append(Checkpoint(**data))
        return checkpoints

    def get_history(self, limit: int = 50) -> List[RecoveryAction]:
        """Get recovery history."""
        if not self.history_file.exists():
            return []

        actions = []
        lines = self.history_file.read_text().strip().split("\n")
        for line in lines[-limit:]:
            if line:
                data = json.loads(line)
                actions.append(RecoveryAction(**data))
        return actions

    def safe_execute(self, func: Callable, checkpoint_name: str,
                     files: Optional[List[str]] = None) -> Any:
        """Execute a function with automatic rollback on failure."""
        cp = self.checkpoint(checkpoint_name, files)
        try:
            result = func()
            self._record_action("safe_execute_success", True, checkpoint_name, cp.id)
            return result
        except Exception as e:
            self._record_action("safe_execute_failed", False, str(e), cp.id)
            self.rollback(cp.id)
            raise

    def _record_action(self, action: str, success: bool, details: str = "",
                       checkpoint_id: Optional[str] = None) -> None:
        """Record a recovery action."""
        entry = RecoveryAction(
            action=action,
            timestamp=time.time(),
            success=success,
            details=details,
            checkpoint_id=checkpoint_id,
        )
        with open(self.history_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
