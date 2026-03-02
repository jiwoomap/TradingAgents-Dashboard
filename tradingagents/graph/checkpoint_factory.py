"""
Checkpoint factory for TradingAgents graph state persistence.

Provides flexible checkpoint storage backends:
- InMemorySaver: For development/testing (non-persistent)
- SqliteSaver: For production single-instance deployments (persistent)

Usage:
    checkpointer = CheckpointerFactory.create(
        backend='sqlite',
        db_path='./checkpoints.sqlite'
    )
    
    # Feature flag pattern
    workflow.compile(checkpointer=checkpointer if enable_checkpoints else None)
"""

import os
from typing import Optional, Literal
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


class CheckpointerFactory:
    """Factory for creating LangGraph checkpoint savers with different backends."""
    
    @staticmethod
    def create(
        backend: Literal['memory', 'sqlite'] = 'memory',
        db_path: Optional[str] = None,
        auto_create_dir: bool = True
    ):
        """
        Create a checkpoint saver instance.
        
        Args:
            backend: Storage backend type ('memory' or 'sqlite')
            db_path: Path to SQLite database file (required for 'sqlite' backend)
            auto_create_dir: Automatically create directory for db_path if missing
            
        Returns:
            Checkpoint saver instance (MemorySaver or SqliteSaver)
            
        Raises:
            ValueError: If backend is 'sqlite' but db_path is not provided
            OSError: If directory creation fails
            
        Examples:
            # Development: In-memory checkpointing
            >>> checkpointer = CheckpointerFactory.create('memory')
            
            # Production: Persistent SQLite storage
            >>> checkpointer = CheckpointerFactory.create(
            ...     'sqlite',
            ...     db_path='./data/checkpoints.sqlite'
            ... )
        """
        if backend == 'memory':
            return MemorySaver()
        
        elif backend == 'sqlite':
            if not db_path:
                raise ValueError(
                    "db_path is required for 'sqlite' backend. "
                    "Example: db_path='./checkpoints.sqlite'"
                )
            
            # Ensure parent directory exists
            if auto_create_dir:
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                    except OSError as e:
                        raise OSError(
                            f"Failed to create directory for checkpoint database: {db_dir}"
                        ) from e
            
            # SqliteSaver uses connection string format
            conn_string = f"sqlite:///{db_path}"
            return SqliteSaver.from_conn_string(conn_string)
        
        else:
            raise ValueError(
                f"Unsupported backend: {backend}. "
                "Supported backends: 'memory', 'sqlite'"
            )
    
    @staticmethod
    def cleanup_old_checkpoints(
        db_path: str,
        retention_days: int = 30,
        keep_successful: bool = True
    ):
        """
        Clean up old checkpoints from SQLite database.
        
        Args:
            db_path: Path to SQLite database
            retention_days: Delete checkpoints older than this many days
            keep_successful: If True, keep successful runs longer (configurable)
            
        Note:
            This is a placeholder for future implementation.
            In practice, you would:
            1. Connect to the SQLite DB
            2. Query checkpoints older than retention_days
            3. Optionally filter by success/failure metadata
            4. Delete matching records
            
        Example:
            >>> CheckpointerFactory.cleanup_old_checkpoints(
            ...     db_path='./checkpoints.sqlite',
            ...     retention_days=30
            ... )
        """
        # TODO: Implement cleanup logic
        # This will be added in Phase 1.5 when we integrate with scheduler
        raise NotImplementedError(
            "Checkpoint cleanup will be implemented in Phase 1.5. "
            "For now, manage checkpoint database manually."
        )
