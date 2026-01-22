"""Inbox storage for Lloyd."""

import json
from pathlib import Path

from .models import InboxItem


class InboxStore:
    """Persistent storage for inbox items."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the inbox store.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.inbox_file = self.lloyd_dir / "inbox" / "items.json"

    def _ensure_dir(self) -> None:
        """Ensure the inbox directory exists."""
        self.inbox_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[InboxItem]:
        """Load all inbox items from storage."""
        if not self.inbox_file.exists():
            return []
        with open(self.inbox_file, "r") as f:
            data = json.load(f)
        return [InboxItem.from_dict(d) for d in data]

    def _save(self, items: list[InboxItem]) -> None:
        """Save all inbox items to storage."""
        self._ensure_dir()
        with open(self.inbox_file, "w") as f:
            json.dump([item.to_dict() for item in items], f, indent=2)

    def add(self, item: InboxItem) -> InboxItem:
        """Add an item to the inbox.

        Args:
            item: The inbox item to add.

        Returns:
            The added item.
        """
        items = self._load()
        items.append(item)
        self._save(items)
        return item

    def get(self, item_id: str) -> InboxItem | None:
        """Get an inbox item by ID.

        Args:
            item_id: The item ID.

        Returns:
            The inbox item or None if not found.
        """
        for item in self._load():
            if item.id == item_id:
                return item
        return None

    def list_unresolved(self) -> list[InboxItem]:
        """Get all unresolved inbox items.

        Returns:
            List of unresolved items.
        """
        return [item for item in self._load() if not item.resolved]

    def list_all(self) -> list[InboxItem]:
        """Get all inbox items.

        Returns:
            List of all items.
        """
        return self._load()

    def resolve(self, item_id: str, action: str) -> InboxItem | None:
        """Resolve an inbox item with an action.

        Args:
            item_id: The item ID.
            action: The resolution action.

        Returns:
            The resolved item or None if not found.
        """
        items = self._load()
        for item in items:
            if item.id == item_id:
                item.resolve(action)
                self._save(items)
                return item
        return None

    def delete(self, item_id: str) -> bool:
        """Delete an inbox item.

        Args:
            item_id: The item ID.

        Returns:
            True if deleted, False if not found.
        """
        items = self._load()
        original_len = len(items)
        items = [item for item in items if item.id != item_id]
        if len(items) < original_len:
            self._save(items)
            return True
        return False
