"""
SQLAlchemy metadata utility module for declaratively constructing and managing
database tables, including support for programmatic foreign key relations.

This module provides an abstraction over SQLAlchemy's metadata management to
simplify table creation with consistent primary key handling and relationship
declarations.

Exports:
    - Relation: A structured representation of a foreign key relationship.
    - MetadataUtility: A utility for constructing tables using SQLAlchemy metadata,
      with helpers for primary keys and relation tables.
"""

from collections.abc import Callable, Collection, Sequence
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.schema import SchemaConst

from escudeiro.data import data, field


def _default_pk_factory():
    return sa.Column("id", sa.Integer, primary_key=True)


@data
class Relation:
    """
    Represents a relation to another table, encapsulating foreign key definition details.

    Attributes:
        table_name (str): Name of the related table.
        column_name (str): Name of the column in the current table referring to the target.
        target_column (str): Fully qualified target column reference (e.g., "user.id").
        column_type (sa.SchemaItem): SQLAlchemy column type used for the relation (e.g., Integer).
    """

    table_name: str
    column_name: str
    target_column: str
    column_type: sa.SchemaItem


@data
class MetadataUtility:
    """
    Encapsulates a SQLAlchemy `MetaData` instance and provides convenience methods
    to declaratively create tables and relation tables with default configuration.

    Attributes:
        metadata (sa.MetaData): The SQLAlchemy metadata container for this utility.
        pk_factory (Callable[[], sa.ColumnElement]): A factory that returns a default
            primary key column (defaults to `id` as Integer).
    """

    metadata: sa.MetaData = field(default_factory=sa.MetaData)
    pk_factory: Callable[[], sa.ColumnElement] = _default_pk_factory

    def make_table(
        self,
        name: str,
        *args: sa.SchemaItem,
        schema: str | Literal[SchemaConst.BLANK_SCHEMA] | None = None,
        quote: bool | None = None,
        quote_schema: bool | None = None,
        autoload_with: sa.Engine | sa.Connection | None = None,
        autoload_replace: bool = True,
        keep_existing: bool = False,
        extend_existing: bool = False,
        resolve_fks: bool = True,
        include_columns: Collection[str] | None = None,
        implicit_returning: bool = True,
        comment: str | None = None,
        info: dict[Any, Any] | None = None,
        listeners: Sequence[tuple[str, Callable[..., Any]]] | None = None,
        prefixes: Sequence[str] | None = None,
        _extend_on: set[sa.Table] | None = None,
        _no_init: bool = True,
        **kw: Any,
    ) -> sa.Table:
        """Create a new SQLAlchemy Table objects registered to the .metadata attribute."""
        return sa.Table(
            name,
            self.metadata,
            *args,
            schema=schema,
            quote=quote,
            quote_schema=quote_schema,
            autoload_with=autoload_with,
            autoload_replace=autoload_replace,
            keep_existing=keep_existing,
            extend_existing=extend_existing,
            resolve_fks=resolve_fks,
            include_columns=include_columns,
            implicit_returning=implicit_returning,
            comment=comment,
            info=info,
            listeners=listeners,
            prefixes=prefixes,
            _extend_on=_extend_on,
            _no_init=_no_init,
            **kw,
        )

    def create_relation_table(
        self, table_name: str, *relations: Relation | str
    ) -> sa.Table:
        """
        Create and register a SQLAlchemy `Table` with this instance's metadata.

        This method mirrors the full constructor signature of `sqlalchemy.Table`
        to provide a drop-in declarative API, with the `metadata` argument implicitly
        bound to this instance.

        Args:
            name (str): The table name.
            *args (sa.SchemaItem): Column and constraint definitions.
            **kwargs: All remaining parameters match 1:1 with `sqlalchemy.Table`.

        Returns:
            sa.Table: The constructed and registered Table object.
        """
        rels: Sequence[Relation] = [
            item
            if isinstance(item, Relation)
            else Relation(
                item,
                f"{item}_id",
                f"{item}.id",
                sa.Integer,
            )
            for item in relations
        ]
        return self.make_table(
            table_name,
            self.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            *(
                sa.Column(
                    rel.column_name,
                    rel.column_type,
                    sa.ForeignKey(rel.target_column),
                )
                for rel in rels
            ),
        )
