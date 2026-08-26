from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .spec import SpecError, digest

AUDIT_STATUSES = frozenset({"benchmark-eligible", "review-required", "rejected"})


class HubAuditDependencyError(RuntimeError):
    pass


def _hub_imports() -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi
        from huggingface_hub.errors import HfHubHTTPError
    except ImportError as exc:
        raise HubAuditDependencyError(
            "Hugging Face Hub audit requires: pip install -e '.[hub]'"
        ) from exc
    return {"HfApi": HfApi, "HfHubHTTPError": HfHubHTTPError}


def _nonempty(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise SpecError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class ModelAuditCriteria:
    pipeline_tag: str
    min_parameters: int
    max_parameters: int
    limit: int = 20
    search: str | None = None
    require_library: str = "transformers"
    allow_gated: bool = False
    allowed_licenses: tuple[str, ...] = ()
    sort: str = "likes"

    def __post_init__(self) -> None:
        _nonempty(self.pipeline_tag, "pipeline_tag")
        _nonempty(self.require_library, "require_library")
        _nonempty(self.sort, "sort")
        if isinstance(self.min_parameters, bool) or type(self.min_parameters) is not int:
            raise SpecError("min_parameters must be an integer")
        if isinstance(self.max_parameters, bool) or type(self.max_parameters) is not int:
            raise SpecError("max_parameters must be an integer")
        if not 1 <= self.min_parameters <= self.max_parameters:
            raise SpecError("parameter bounds are invalid")
        if (
            isinstance(self.limit, bool)
            or type(self.limit) is not int
            or not 1 <= self.limit <= 100
        ):
            raise SpecError("model audit limit must be between 1 and 100")
        if self.search is not None and (type(self.search) is not str or not self.search.strip()):
            raise SpecError("search must be null or a non-empty string")
        if any(type(item) is not str or not item.strip() for item in self.allowed_licenses):
            raise SpecError("allowed_licenses must contain non-empty strings")
        if len(self.allowed_licenses) != len(set(self.allowed_licenses)):
            raise SpecError("allowed_licenses must be unique")

    @property
    def parameter_filter(self) -> str:
        return f"min:{self.min_parameters},max:{self.max_parameters}"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "agoge.base-model-audit-criteria.v1",
            "pipeline_tag": self.pipeline_tag,
            "min_parameters": self.min_parameters,
            "max_parameters": self.max_parameters,
            "limit": self.limit,
            "search": self.search,
            "require_library": self.require_library,
            "allow_gated": self.allow_gated,
            "allowed_licenses": list(self.allowed_licenses),
            "sort": self.sort,
        }

    @property
    def criteria_id(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AuditedModel:
    repo_id: str
    revision: str | None
    status: str
    reasons: tuple[str, ...]
    pipeline_tag: str | None
    library_name: str | None
    license: str | None
    gated: bool | str | None
    private: bool
    parameters: int | None
    safetensors_bytes: int | None
    architectures: tuple[str, ...]
    model_type: str | None
    downloads: int | None
    likes: int | None
    tags: tuple[str, ...]
    base_models: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty(self.repo_id, "repo_id")
        if self.status not in AUDIT_STATUSES:
            raise SpecError("model audit status is unsupported")
        if not self.reasons:
            raise SpecError("model audit reasons cannot be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "agoge.base-model-candidate.v1",
            "repo_id": self.repo_id,
            "revision": self.revision,
            "status": self.status,
            "reasons": list(self.reasons),
            "pipeline_tag": self.pipeline_tag,
            "library_name": self.library_name,
            "license": self.license,
            "gated": self.gated,
            "private": self.private,
            "parameters": self.parameters,
            "safetensors_bytes": self.safetensors_bytes,
            "architectures": list(self.architectures),
            "model_type": self.model_type,
            "downloads": self.downloads,
            "likes": self.likes,
            "tags": list(self.tags),
            "base_models": list(self.base_models),
        }


def _card_dict(info: Any) -> dict[str, Any]:
    card = getattr(info, "card_data", None)
    if card is None:
        return {}
    if type(card) is dict:
        return card
    to_dict = getattr(card, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        return value if type(value) is dict else {}
    return {}


def _base_models(card: dict[str, Any]) -> tuple[str, ...]:
    value = card.get("base_model")
    if type(value) is str and value.strip():
        return (value,)
    if type(value) is list:
        return tuple(sorted(item for item in value if type(item) is str and item.strip()))
    return ()


def _safetensors_parameters(info: Any) -> int | None:
    data = getattr(info, "safetensors", None)
    total = getattr(data, "total", None) if data is not None else None
    if isinstance(total, bool) or type(total) is not int or total <= 0:
        return None
    return total


def _safetensors_bytes(info: Any) -> int | None:
    siblings = getattr(info, "siblings", None)
    if type(siblings) is not list:
        return None
    total = 0
    found = False
    for sibling in siblings:
        name = getattr(sibling, "rfilename", None)
        size = getattr(sibling, "size", None)
        if type(name) is str and name.endswith(".safetensors") and type(size) is int and size > 0:
            total += size
            found = True
    return total if found else None


def _config_architecture(info: Any) -> tuple[tuple[str, ...], str | None]:
    config = getattr(info, "config", None)
    if type(config) is not dict:
        return (), None
    architectures = config.get("architectures")
    normalized = (
        tuple(item for item in architectures if type(item) is str and item.strip())
        if type(architectures) is list
        else ()
    )
    model_type = config.get("model_type")
    return normalized, model_type if type(model_type) is str and model_type.strip() else None


def audit_model_info(info: Any, criteria: ModelAuditCriteria) -> AuditedModel:
    repo_id = getattr(info, "id", None) or getattr(info, "modelId", None)
    repo_id = _nonempty(repo_id, "Hub model id")
    card = _card_dict(info)
    license_name = card.get("license")
    if type(license_name) is not str or not license_name.strip():
        license_name = None
    pipeline_tag = getattr(info, "pipeline_tag", None)
    library_name = getattr(info, "library_name", None)
    gated = getattr(info, "gated", None)
    private = bool(getattr(info, "private", False))
    revision = getattr(info, "sha", None)
    parameters = _safetensors_parameters(info)
    tensor_bytes = _safetensors_bytes(info)
    architectures, model_type = _config_architecture(info)
    tags_value = getattr(info, "tags", None)
    tags = (
        tuple(sorted(item for item in tags_value if type(item) is str))
        if type(tags_value) is list
        else ()
    )

    rejection: list[str] = []
    review: list[str] = []
    if private:
        rejection.append("private-repository")
    if pipeline_tag != criteria.pipeline_tag:
        rejection.append("pipeline-tag-mismatch")
    if library_name != criteria.require_library:
        rejection.append("library-mismatch")
    if gated and not criteria.allow_gated:
        rejection.append("gated-model-not-allowed")
    if parameters is None:
        review.append("parameter-count-unknown")
    elif not criteria.min_parameters <= parameters <= criteria.max_parameters:
        rejection.append("parameter-count-out-of-range")
    if revision is None:
        review.append("revision-unknown")
    if not architectures or model_type is None:
        review.append("architecture-metadata-incomplete")
    if tensor_bytes is None:
        review.append("safetensors-size-unknown")
    if license_name is None:
        review.append("license-unknown")
    elif criteria.allowed_licenses and license_name not in criteria.allowed_licenses:
        rejection.append("license-not-allowed-by-audit-policy")
    elif not criteria.allowed_licenses:
        review.append("license-policy-not-specified")

    if rejection:
        status = "rejected"
        reasons = tuple(sorted(set(rejection + review)))
    elif review:
        status = "review-required"
        reasons = tuple(sorted(set(review)))
    else:
        status = "benchmark-eligible"
        reasons = ("metadata-policy-passed",)

    return AuditedModel(
        repo_id=repo_id,
        revision=revision if type(revision) is str and revision else None,
        status=status,
        reasons=reasons,
        pipeline_tag=pipeline_tag if type(pipeline_tag) is str else None,
        library_name=library_name if type(library_name) is str else None,
        license=license_name,
        gated=gated,
        private=private,
        parameters=parameters,
        safetensors_bytes=tensor_bytes,
        architectures=architectures,
        model_type=model_type,
        downloads=getattr(info, "downloads", None),
        likes=getattr(info, "likes", None),
        tags=tags,
        base_models=_base_models(card),
    )


def audit_huggingface(criteria: ModelAuditCriteria) -> dict[str, object]:
    lib = _hub_imports()
    api = lib["HfApi"]()
    hub_error = lib["HfHubHTTPError"]
    discovered = api.list_models(
        pipeline_tag=criteria.pipeline_tag,
        num_parameters=criteria.parameter_filter,
        search=criteria.search,
        sort=criteria.sort,
        limit=criteria.limit,
        full=True,
        cardData=True,
        fetch_config=True,
    )
    candidates: list[AuditedModel] = []
    for summary in discovered:
        repo_id = getattr(summary, "id", None) or getattr(summary, "modelId", None)
        if type(repo_id) is not str or not repo_id:
            continue
        try:
            detailed = api.model_info(repo_id, files_metadata=True)
        except (hub_error, OSError) as exc:
            candidates.append(
                AuditedModel(
                    repo_id=repo_id,
                    revision=None,
                    status="review-required",
                    reasons=(f"model-info-fetch-failed:{type(exc).__name__}",),
                    pipeline_tag=getattr(summary, "pipeline_tag", None),
                    library_name=getattr(summary, "library_name", None),
                    license=None,
                    gated=getattr(summary, "gated", None),
                    private=bool(getattr(summary, "private", False)),
                    parameters=_safetensors_parameters(summary),
                    safetensors_bytes=None,
                    architectures=(),
                    model_type=None,
                    downloads=getattr(summary, "downloads", None),
                    likes=getattr(summary, "likes", None),
                    tags=tuple(sorted(getattr(summary, "tags", None) or ())),
                    base_models=(),
                )
            )
            continue
        candidates.append(audit_model_info(detailed, criteria))

    status_counts = {status: 0 for status in sorted(AUDIT_STATUSES)}
    for candidate in candidates:
        status_counts[candidate.status] += 1
    document = {
        "schema": "agoge.base-model-audit-result.v1",
        "source": "huggingface-hub",
        "criteria": criteria.to_dict(),
        "criteria_id": criteria.criteria_id,
        "selection_rule": "Hub audit produces a shortlist only; Student-local baseline benchmarks choose the base model.",
        "status_counts": status_counts,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    return {**document, "audit_id": digest(document)}
