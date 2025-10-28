"""
Provides representations of OSV advisories and triaged records for scanning and querying.
"""

from enum import Enum
from datetime import datetime
import logging
import os
from typing import Optional
from typing_extensions import Self

from pynamodb.attributes import BooleanAttribute, ListAttribute, MapAttribute, NumberAttribute, UnicodeAttribute
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


class OsvAdvisoriesModel(Model):
    """
    A minimal representation of OSV advisories for manifest syncing purposes.
    """
    class Meta:
        table_name = os.environ.get("OSV_TABLE_NAME")

    package = UnicodeAttribute(hash_key=True)
    attack_id = NumberAttribute(range_key=True)
    affected: ListAttribute[MapAttribute] = ListAttribute()
    timestamp = NumberAttribute()

    def get_ecosystem_package(self) -> tuple[ECOSYSTEM, str]:
        """
        Extract the advisory record's ecosystem and package name.

        Returns:
            A tuple of the `ECOSYSTEM` and package name `str` for the package
            that the OSV advisory concerns.

        Raises:
            ValueError: Malformed OSV advisory package key.
        """
        try:
            package, _, ecosystem = self.package.rpartition('|')
            return ECOSYSTEM.from_str(ecosystem), package

        except Exception:
            raise ValueError(f"Malformed OSV advisory package key: '{self.package}'")

    def get_affected_versions(self) -> list[str]:
        """
        Extract the list of affected versions for the concerned package.

        Returns:
            A `list[str]` of affected versions mentioned in the advisory
            for the concerned package.

        Raises:
            ValueError: Malformed OSV advisory: no affected record for concerned package.
        """
        ecosystem, package = self.get_ecosystem_package()

        for affected in self.affected:
            affected_package = affected.get("package", {})
            affected_package_ecosystem = affected_package.get("ecosystem", "")
            affected_package_name = affected_package.get("name", "")

            if affected_package_ecosystem != str(ecosystem) or affected_package_name != package:
                continue

            return affected.get("versions", [])

        raise ValueError(
            f"Malformed OSV advisory: no affected record for concerned package {ecosystem}|{package}"
        )

    @classmethod
    def scan_latest_advisories(cls, ecosystem: ECOSYSTEM, since: datetime) -> list[Self]:
        """
        Scan for the latest OSV advisories in a given ecosystem.

        Args:
            ecosystem: The `ECOSYSTEM` of advisories of interest.
            since: The `datetime` lookback cutoff to use when scanning for advisories.

        Returns:
            A `list[OsvAdvisoriesModel]` containing OSV advisories in the given `ecosystem`
            that were modified at or after the given `since` datetime.
        """
        ecosystem_suffix = f"|{str(ecosystem).lower()}"

        filter_condition = (
            cls.package.contains(ecosystem_suffix) & (cls.timestamp >= since.timestamp())
        )

        scan_results = list(cls.scan(filter_condition=filter_condition))
        validated_results = [
            advisory for advisory in scan_results if advisory.package.endswith(ecosystem_suffix)
        ]

        if len(validated_results) != len(scan_results):
            anomalies = set(scan_results) - set(validated_results)
            anomaly_packages = sorted(advisory.package for advisory in anomalies)
            log.warning(f"Detected advisories with dubious package keys: {anomaly_packages}")

        return validated_results


class TriagedResultsModel(Model):
    """
    A minimal representation of package triage records for manifest syncing purposes.
    """
    class Meta:
        table_name = os.environ.get("TRIAGE_TABLE_NAME")

    package = UnicodeAttribute(hash_key=True)
    attack_id = NumberAttribute(range_key=True)
    compromised_lib = BooleanAttribute(null=True)

    @classmethod
    def query_triaged_result(cls, ecosystem: ECOSYSTEM, package: str, attack_id: int) -> Optional[Self]:
        """
        Query triage records for the given package and attack ID.

        Args:
            ecosystem: The `ECOSYSTEM` of the package to query.
            package: The package name `str` of the package to query.
            attack_id: The unique attack ID `int` of the desired triage record.

        Returns:
            A `TriagedResultsModel` responding to the input query or `None` if
            the query returned no results.
        """
        def hash_key() -> str:
            return f"{package}|{str(ecosystem).lower()}"

        range_key_condition = cls.attack_id == attack_id

        query_results = list(cls.query(hash_key=hash_key(), range_key_condition=range_key_condition))

        if not query_results:
            return None

        if len(query_results) != 1:
            log.warning(
                f"Package {ecosystem}|{package} has multiple triage records with attack ID {attack_id}"
            )

        return query_results[0]
