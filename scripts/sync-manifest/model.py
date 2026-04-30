"""
Provides a representation of triaged records for scanning and querying.
"""

from enum import Enum
from datetime import datetime
import logging
import os
from typing_extensions import Self

from pynamodb.attributes import BooleanAttribute, ListAttribute, NumberAttribute, UnicodeAttribute
from pynamodb.models import Model

log = logging.getLogger(__name__)


class ECOSYSTEM(Enum):
    """
    The dataset's monitored package ecosystems.
    """
    Npm = "npm"
    PyPI = "PyPI"

    def __str__(self) -> str:
        """
        Format an `ECOSYSTEM` for printing.

        Returns:
            A `str` representing the given `ECOSYSTEM` suitable for printing.
        """
        return self.value

    @classmethod
    def from_str(cls, s: str) -> Self:
        """
        Convert a string into an `ECOSYSTEM`.

        Args:
            s: The `str` to be converted (case-insensitive).

        Returns:
            The `ECOSYSTEM` referred to by the given string.

        Raises:
            ValueError: The given string does not refer to a valid `ECOSYSTEM`.
        """
        try:
            mappings = {f"{ecosystem}".lower(): ecosystem for ecosystem in cls}
            return mappings[s.lower()]
        except Exception:
            raise ValueError(f"Invalid package ecosystem '{s}'")


class TriagedResultsModel(Model):
    """
    A minimal representation of package triage records for manifest syncing purposes.
    """
    class Meta:
        table_name = os.environ.get("TRIAGE_TABLE_NAME")

    package = UnicodeAttribute(hash_key=True)
    attack_id = NumberAttribute(range_key=True)
    compromised_lib = BooleanAttribute(null=True)
    malicious_versions: ListAttribute[UnicodeAttribute] = ListAttribute()
    created_at = NumberAttribute()
    updated_at = NumberAttribute(null=True)

    def get_ecosystem_package(self) -> tuple[ECOSYSTEM, str]:
        """
        Extract the triage record's ecosystem and package name.

        Returns:
            A tuple of the `ECOSYSTEM` and package name `str` that the record concerns.

        Raises:
            ValueError: Malformed triage record package key.
        """
        try:
            package, _, ecosystem = self.package.rpartition('|')
            return ECOSYSTEM.from_str(ecosystem), package

        except Exception:
            raise ValueError(f"Malformed triage record package key: '{self.package}'")

    @classmethod
    def scan_latest_records(cls, ecosystem: ECOSYSTEM, since: datetime) -> list[Self]:
        """
        Scan for the latest triage records in a given ecosystem.

        Args:
            ecosystem: The `ECOSYSTEM` of records of interest.
            since: The `datetime` lookback cutoff to use when scanning for records.

        Returns:
            A `list[TriagedResultsModel]` containing triage records in the given `ecosystem`
            that were modified at or after the given `since` datetime.
        """
        since_timestamp = since.timestamp()
        ecosystem_suffix = f"|{str(ecosystem).lower()}"

        filter_condition = (
            cls.package.contains(ecosystem_suffix)
            & ((cls.updated_at >= since_timestamp) | (cls.created_at >= since_timestamp))
        )

        scan_results = list(cls.scan(filter_condition=filter_condition))
        validated_results = [
            record for record in scan_results if record.package.endswith(ecosystem_suffix)
        ]

        if len(validated_results) != len(scan_results):
            anomalies = set(scan_results) - set(validated_results)
            anomaly_packages = sorted(record.package for record in anomalies)
            log.warning(f"Detected triage records with dubious package keys: {anomaly_packages}")

        return validated_results
