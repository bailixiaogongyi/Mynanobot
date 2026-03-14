"""Global HTTP client manager with connection pooling."""

from __future__ import annotations

import httpx
from loguru import logger


class HttpClientManager:
    """Global HTTP client manager with connection pooling.
    
    This class provides a singleton-like pattern for managing HTTP clients
    with connection pooling to improve performance and reduce resource usage.
    """
    
    _default_client: httpx.AsyncClient | None = None
    _clients: dict[str, httpx.AsyncClient] = {}
    
    @classmethod
    async def get_client(
        cls,
        name: str = "default",
        timeout: float = 30.0,
        **kwargs: any,
    ) -> httpx.AsyncClient:
        """Get or create an HTTP client.
        
        Args:
            name: Client name for identification.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to httpx.AsyncClient.
            
        Returns:
            An AsyncClient instance.
        """
        if name == "default":
            if cls._default_client is None:
                cls._default_client = httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    **kwargs,
                )
                logger.debug(f"Created default HTTP client with timeout={timeout}s")
            return cls._default_client
        
        if name not in cls._clients:
            cls._clients[name] = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                **kwargs,
            )
            logger.debug(f"Created HTTP client '{name}' with timeout={timeout}s")
        return cls._clients[name]
    
    @classmethod
    async def close_all(cls) -> None:
        """Close all HTTP clients."""
        if cls._default_client:
            await cls._default_client.aclose()
            cls._default_client = None
            logger.debug("Closed default HTTP client")
        
        for name, client in list(cls._clients.items()):
            await client.aclose()
            logger.debug(f"Closed HTTP client '{name}'")
        cls._clients.clear()
    
    @classmethod
    async def close(cls, name: str) -> None:
        """Close a specific HTTP client.
        
        Args:
            name: Client name to close.
        """
        if name == "default":
            if cls._default_client:
                await cls._default_client.aclose()
                cls._default_client = None
                logger.debug("Closed default HTTP client")
        elif name in cls._clients:
            await cls._clients[name].aclose()
            del cls._clients[name]
            logger.debug(f"Closed HTTP client '{name}'")


http_client = HttpClientManager()
