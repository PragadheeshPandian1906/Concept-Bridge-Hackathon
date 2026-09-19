"""Pydantic compatibility layer.

The project is written against the Pydantic v2 API (``BaseModel``,
``Field``, ``ValidationError``, ``model_validate``, ``model_dump``).

If Pydantic is installed we simply re-export it. If it is not installed
(offline machine, minimal container, hackathon laptop with no wheels)
we fall back to a small, strict, dependency-free implementation that
supports the subset of the API this project uses.

Nothing else in the codebase imports pydantic directly, so the whole
agent behaves identically either way.
"""

from __future__ import annotations

try:  # pragma: no cover - depends on the environment
    from pydantic import BaseModel, Field, ValidationError  # type: ignore

    PYDANTIC_AVAILABLE = True

except Exception:  # pragma: no cover - fallback path
    PYDANTIC_AVAILABLE = False

    import json
    import typing
    from typing import Any, Union, get_args, get_origin

    class ValidationError(ValueError):
        """Raised when input data does not satisfy a model definition."""

    class _Missing:
        def __repr__(self) -> str:
            return "<missing>"

    _MISSING = _Missing()

    class _FieldInfo:
        __slots__ = ("default", "default_factory", "description", "ge", "le")

        def __init__(self, default=_MISSING, default_factory=None,
                     description=None, ge=None, le=None):
            self.default = default
            self.default_factory = default_factory
            self.description = description
            self.ge = ge
            self.le = le

        def has_default(self) -> bool:
            return self.default is not _MISSING or self.default_factory is not None

        def get_default(self):
            if self.default_factory is not None:
                return self.default_factory()
            return self.default

    def Field(default=_MISSING, *, default_factory=None, description=None,
              ge=None, le=None, **_ignored):
        return _FieldInfo(default=default, default_factory=default_factory,
                          description=description, ge=ge, le=le)

    def _type_name(tp) -> str:
        return getattr(tp, "__name__", str(tp))

    def _validate(tp, value, path: str, field: "_FieldInfo | None" = None):
        origin = get_origin(tp)

        if tp is Any or tp is None:
            return value

        # Optional[X] / Union[...]
        if origin is Union or str(origin) == "<class 'types.UnionType'>":
            args = get_args(tp)
            if value is None and type(None) in args:
                return None
            errors = []
            for arg in args:
                if arg is type(None):
                    continue
                try:
                    return _validate(arg, value, path, field)
                except ValidationError as exc:
                    errors.append(str(exc))
            raise ValidationError(f"{path}: does not match {tp} ({'; '.join(errors)})")

        if origin in (list, tuple):
            if not isinstance(value, (list, tuple)):
                raise ValidationError(f"{path}: expected a list, got {type(value).__name__}")
            args = get_args(tp)
            item_tp = args[0] if args else Any
            return [_validate(item_tp, v, f"{path}[{i}]") for i, v in enumerate(value)]

        if origin is dict:
            if not isinstance(value, dict):
                raise ValidationError(f"{path}: expected an object, got {type(value).__name__}")
            args = get_args(tp)
            if len(args) == 2:
                return {_validate(args[0], k, path): _validate(args[1], v, f"{path}.{k}")
                        for k, v in value.items()}
            return dict(value)

        if origin is typing.Literal:
            if value not in get_args(tp):
                raise ValidationError(f"{path}: {value!r} is not one of {get_args(tp)}")
            return value

        if isinstance(tp, type) and issubclass(tp, BaseModel):
            if isinstance(value, tp):
                return value
            if isinstance(value, dict):
                return tp(**value)
            raise ValidationError(f"{path}: expected {tp.__name__} object")

        if tp is bool:
            if isinstance(value, bool):
                return value
            raise ValidationError(f"{path}: expected bool, got {type(value).__name__}")

        if tp is int:
            if isinstance(value, bool):
                raise ValidationError(f"{path}: expected int, got bool")
            if isinstance(value, int):
                return value
            if isinstance(value, float) and float(value).is_integer():
                return int(value)
            raise ValidationError(f"{path}: expected int, got {type(value).__name__}")

        if tp is float:
            if isinstance(value, bool):
                raise ValidationError(f"{path}: expected float, got bool")
            if isinstance(value, (int, float)):
                out = float(value)
            elif isinstance(value, str):
                try:
                    out = float(value.strip())
                except ValueError:
                    raise ValidationError(f"{path}: expected a number, got {value!r}")
            else:
                raise ValidationError(f"{path}: expected float, got {type(value).__name__}")
            if field is not None:
                if field.ge is not None and out < field.ge:
                    raise ValidationError(f"{path}: {out} < minimum {field.ge}")
                if field.le is not None and out > field.le:
                    raise ValidationError(f"{path}: {out} > maximum {field.le}")
            return out

        if tp is str:
            if isinstance(value, str):
                return value
            raise ValidationError(f"{path}: expected str, got {type(value).__name__}")

        # Unknown/plain types: accept as-is.
        return value

    class _ModelMeta(type):
        def __new__(mcls, name, bases, namespace, **kwargs):
            cls = super().__new__(mcls, name, bases, dict(namespace))
            fields: dict = {}
            for base in reversed(cls.__mro__[1:]):
                fields.update(getattr(base, "__fields_def__", {}) or {})
            annotations = namespace.get("__annotations__", {}) or {}
            for fname, ftype in annotations.items():
                if fname.startswith("_"):
                    continue
                raw_default = namespace.get(fname, _MISSING)
                if isinstance(raw_default, _FieldInfo):
                    info = raw_default
                else:
                    info = _FieldInfo(default=raw_default)
                fields[fname] = (ftype, info)
            cls.__fields_def__ = fields
            return cls

    class BaseModel(metaclass=_ModelMeta):
        """Minimal stand-in for ``pydantic.BaseModel`` (v2 surface)."""

        __fields_def__: dict = {}

        @classmethod
        def _fields(cls) -> dict:
            """Field map with string annotations resolved (PEP 563 safe)."""
            cached = cls.__dict__.get("__fields_resolved__")
            if cached is not None:
                return cached
            try:
                hints = typing.get_type_hints(cls)
            except Exception:  # pragma: no cover - unresolvable forward ref
                hints = {}
            resolved = {
                name: (hints.get(name, tp), info)
                for name, (tp, info) in cls.__fields_def__.items()
            }
            cls.__fields_resolved__ = resolved
            return resolved

        def __init__(self, **data):
            errors = []
            values = {}
            for fname, (ftype, info) in self._fields().items():
                if fname in data:
                    try:
                        values[fname] = _validate(ftype, data[fname], fname, info)
                    except ValidationError as exc:
                        errors.append(str(exc))
                elif info.has_default():
                    values[fname] = info.get_default()
                else:
                    errors.append(f"{fname}: field required")
            if errors:
                raise ValidationError(
                    f"{type(self).__name__}: " + "; ".join(errors)
                )
            self.__dict__.update(values)

        # -- pydantic v2 API subset ---------------------------------
        @classmethod
        def model_validate(cls, obj):
            if isinstance(obj, cls):
                return obj
            if isinstance(obj, dict):
                return cls(**obj)
            raise ValidationError(f"{cls.__name__}: expected an object")

        @classmethod
        def model_validate_json(cls, raw: str):
            try:
                parsed = json.loads(raw)
            except Exception as exc:
                raise ValidationError(f"{cls.__name__}: invalid JSON ({exc})")
            return cls.model_validate(parsed)

        @classmethod
        def model_fields_set(cls):
            return set(cls._fields())

        def model_dump(self):
            out = {}
            for fname in self._fields():
                out[fname] = _dump_value(getattr(self, fname))
            return out

        def model_dump_json(self, indent=None):
            return json.dumps(self.model_dump(), indent=indent, ensure_ascii=False)

        def model_copy(self, update=None):
            data = self.model_dump()
            data.update(update or {})
            return type(self)(**data)

        def __eq__(self, other):
            return isinstance(other, type(self)) and self.model_dump() == other.model_dump()

        def __repr__(self):
            inner = ", ".join(f"{k}={getattr(self, k)!r}" for k in self._fields())
            return f"{type(self).__name__}({inner})"

    def _dump_value(value):
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, (list, tuple)):
            return [_dump_value(v) for v in value]
        if isinstance(value, dict):
            return {k: _dump_value(v) for k, v in value.items()}
        return value


__all__ = ["BaseModel", "Field", "ValidationError", "PYDANTIC_AVAILABLE"]
