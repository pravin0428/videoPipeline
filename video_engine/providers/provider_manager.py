from __future__ import annotations

import os
import time
from typing import Optional

from video_engine.providers.base_provider import BaseProvider, VideoAsset
from video_engine.providers.provider_factory import ProviderFactory
from video_engine.utils.logging import LOG
from video_engine.config import (
    PROVIDER,
    PROVIDER_FALLBACK_ORDER,
    PROVIDER_CACHE_DIR,
    RETRY_COUNT,
    RETRY_DELAY_BASE,
    RETRY_DELAY_MAX,
    RETRY_QUERY_REFINEMENTS,
)


class ProviderManager:
    def __init__(
        self,
        primary: Optional[str] = None,
        fallback_order: Optional[list[str]] = None,
        config: Optional[dict] = None,
    ) -> None:
        self._primary_name = primary or PROVIDER
        self._fallback_order = fallback_order or list(PROVIDER_FALLBACK_ORDER)
        self._config = config or {}
        self._providers: dict[str, BaseProvider] = {}
        self._primary: Optional[BaseProvider] = None
        self._metrics: dict[str, dict] = {}

    def initialize(self) -> None:
        LOG.info(f"Initializing provider manager (primary={self._primary_name})...")

        order = [self._primary_name]
        for name in self._fallback_order:
            if name not in order and name != self._primary_name:
                order.append(name)

        for name in order:
            provider = ProviderFactory.create(name, config=self._config)
            if provider is None:
                continue
            try:
                provider.initialize()
            except NotImplementedError:
                LOG.info(f"  Provider '{name}': not yet available (placeholder)")
                self._metrics[name] = {"status": "placeholder"}
                continue
            except Exception as e:
                LOG.warn(f"  Provider '{name}' init failed: {e}")
                self._metrics[name] = {"status": "init_failed", "error": str(e)}
                continue

            self._providers[name] = provider
            self._metrics[name] = {"status": "ready"}
            if name == self._primary_name:
                self._primary = provider
                LOG.info(f"  Primary provider '{name}': ready")

        if self._primary is None:
            LOG.warn(f"  Primary '{self._primary_name}' unavailable, "
                     f"falling back to first available")

            for name in order:
                if name in self._providers:
                    self._primary = self._providers[name]
                    self._primary_name = name
                    LOG.info(f"  Using '{name}' as primary (fallback)")
                    break

        if self._primary is None:
            LOG.warn("  No provider initialized — all are placeholders or unavailable")

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    @property
    def primary(self) -> Optional[BaseProvider]:
        return self._primary

    @property
    def primary_name(self) -> str:
        return self._primary_name if self._primary else "none"

    def generate_clip(
        self,
        prompt: str,
        options: Optional[dict] = None,
    ) -> VideoAsset:
        opts = options or {}
        shot_id = opts.get("shot_id", "?")

        if self._primary is None:
            LOG.fail(f"[{shot_id}] No provider available — creating fallback text scene")
            return self._create_fallback_asset(opts)

        fallback_order = [self._primary_name]
        for name in self._fallback_order:
            if name not in fallback_order:
                fallback_order.append(name)

        last_error = ""
        for name in fallback_order:
            provider = self._providers.get(name)
            if provider is None:
                continue

            for attempt in range(RETRY_COUNT):
                q = self._refine_query(prompt, attempt)
                try:
                    shot_start = time.time()
                    LOG.info(f"    [{shot_id}] provider={name}, attempt={attempt + 1}/{RETRY_COUNT}")
                    asset = provider.generate(q, {**(opts or {}), "query_hint": q})
                    elapsed = time.time() - shot_start
                    self._record(name, asset, elapsed)
                    LOG.info(f"    [{shot_id}] {name} done ({elapsed:.1f}s) "
                             f"→ {os.path.basename(asset.local_path)}")
                    return asset
                except NotImplementedError:
                    LOG.info(f"    [{shot_id}] {name} not implemented, skipping")
                    break
                except Exception as e:
                    last_error = str(e)
                    LOG.warn(f"    [{shot_id}] {name} attempt {attempt + 1} failed: {e}")
                    if attempt < RETRY_COUNT - 1:
                        delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
                        time.sleep(delay)
                    continue

            if last_error:
                LOG.info(f"    [{shot_id}] {name} exhausted, trying next provider")

        LOG.fail(f"[{shot_id}] All providers failed — last error: {last_error}")
        return self._create_fallback_asset(opts)

    def get_metrics(self) -> dict[str, dict]:
        result = dict(self._metrics)
        for name, provider in self._providers.items():
            try:
                result[name]["generation_metrics"] = provider.get_metrics()
            except Exception:
                pass
        return result

    def _record(self, provider_name: str, asset: VideoAsset, elapsed: float) -> None:
        self._metrics.setdefault(provider_name, {}).setdefault("generations", 0)
        self._metrics[provider_name]["generations"] += 1
        self._metrics[provider_name].setdefault("total_time", 0.0)
        self._metrics[provider_name]["total_time"] += elapsed

    def _refine_query(self, base_query: str, attempt: int) -> str:
        if attempt == 0:
            return base_query
        if not base_query.strip():
            return base_query
        words = base_query.split()
        if attempt > 1 and len(words) > 3:
            return " ".join(words[:2])
        idx = min(attempt - 1, len(RETRY_QUERY_REFINEMENTS) - 1)
        refinement = RETRY_QUERY_REFINEMENTS[idx]
        if refinement in base_query:
            return base_query
        return f"{refinement} {base_query}"

    def _create_fallback_asset(self, options: dict) -> VideoAsset:
        return VideoAsset(
            local_path=options.get("output_path", ""),
            provider_name="fallback",
            duration=options.get("duration", 5.0),
            width=int(options.get("resolution", "1080x1920").split("x")[0]),
            height=int(options.get("resolution", "1080x1920").split("x")[1]),
            fps=options.get("fps", 30),
            quality_score=0.0,
        )
