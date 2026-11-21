"""Entrada de dinero capturado a mano. Decimales exactos, sin redondeo silencioso."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Kind = Literal["compra", "venta", "gasto", "precio_mercado"]
Category = Literal["alimento", "sanidad", "mano_obra", "instalaciones", "transporte", "otros"]
Scope = Literal["animales", "corral", "hato"]
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Price = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Weight = Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)]


class MovementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    movement_id: UUID
    kind: Kind
    category: Category | None = None
    amount_mxn: Amount | None = None
    precio_kg_mxn: Price | None = None
    weight_kg: Weight | None = None
    occurred_on: date
    period_start: date | None = None
    period_end: date | None = None
    scope: Scope
    corral: str | None = Field(default=None, min_length=1, max_length=120)
    source_entry_id: UUID | None = None
    animals: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("animals")
    @classmethod
    def tags(cls, values: list[str]) -> list[str]:
        tags = sorted(set(value.strip() for value in values))
        if any(not tag or len(tag) > 64 for tag in tags):
            raise ValueError("Cada arete requiere entre 1 y 64 caracteres")
        return tags

    @field_validator("corral", mode="before")
    @classmethod
    def trim_corral(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def combinations(self) -> Self:
        if self.kind in ("compra", "venta") and (self.scope != "animales"
                                                 or len(self.animals) != 1):
            raise ValueError("Compra y venta requieren exactamente un animal")
        if self.kind == "precio_mercado":
            if self.scope != "hato" or self.animals or self.precio_kg_mxn is None \
                    or self.amount_mxn is not None:
                raise ValueError("Precio de mercado requiere precio/kg y alcance hato sin animales")
        elif self.amount_mxn is None or self.precio_kg_mxn is not None:
            raise ValueError("Compra, venta y gasto requieren monto, sin precio de mercado")
        if (self.kind == "gasto") != (self.category is not None):
            raise ValueError("Solo los gastos requieren categoría")
        if self.weight_kg is not None and self.kind not in ("compra", "venta"):
            raise ValueError("El peso solo corresponde a compra o venta")
        if (self.scope == "animales") != bool(self.animals):
            raise ValueError("El alcance animales requiere aretes; corral y hato no los admiten")
        if (self.scope == "corral") != (self.corral is not None):
            raise ValueError("Solo el alcance corral requiere una etiqueta de corral")
        if self.period_start is not None or self.period_end is not None:
            if self.kind != "gasto" or self.period_start is None or self.period_end is None \
                    or self.period_end < self.period_start:
                raise ValueError("El periodo de gasto requiere inicio y fin en orden")
        return self


class VoidIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    movement_id: UUID
    occurred_on: date


class MovementOut(BaseModel):
    movement_id: UUID
    kind: Kind
    category: Category | None
    amount_mxn: Decimal | None
    precio_kg_mxn: Decimal | None
    weight_kg: Decimal | None
    occurred_on: date
    period_start: date | None
    period_end: date | None
    scope: Scope
    corral: str | None
    source_entry_id: UUID | None
    animals: list[str]
    status: Literal["propuesto", "confirmado", "anulado"]
    estado: Literal["propuesto", "confirmado", "anulado", "anulacion"]
    voids_movement_id: UUID | None
    author_id: int
    author: str
    created_at: datetime


class MovementList(BaseModel):
    movements: list[MovementOut]


class PriceHistory(BaseModel):
    current: MovementOut | None
    history: list[MovementOut]
